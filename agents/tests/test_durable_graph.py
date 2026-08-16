"""S1-6 — Durable graph consumer + park/resume across a simulated restart.

Exercises the native, durable Collect-loop graph (``agents.address.graph``) that
retires the in-turn ``BridgeAgentTool`` (ADR-0010). Three layers:

- **5.1 spike gate 1** — the ``RemoteA2aAgent`` collect node runs directly as a
  ``Workflow`` graph node and the deterministic gate reads its collected
  ``ExchangeTurn`` off the shared session; an instant-terminal scenario routes to
  done.
- **5.2 spike gate 2 + loop iteration** — a parked (``input-required``) leg
  *pauses inside the loop* on a ``LongRunningFunctionTool`` call and *resumes*
  via a ``FunctionResponse`` (no HTTP) to the terminal outcome, and the
  collected-so-far ledger is captured before the park.
- **5.3 the headline** — the parked leg survives a *simulated process restart*
  (fresh ``Runner`` + fresh ``DatabaseSessionService`` on the same SQLite file,
  the mock served with a ``DatabaseTaskStore``): the collected ledger + exchange
  context and the peer A2A ``task_id``/``context_id`` (auto-restored from event
  ``custom_metadata``) are intact, and resume continues the deterministic gate to
  the same terminal outcome as an uninterrupted run — terminal-outcome parity.

Construct note: the Collect loop is a native ``google.adk.workflow.Workflow``
conditional cycle (``collect -> gate``, ``gate --[again]--> collect``, ``gate
--[done]--> present``) — *not* the deprecated ``LoopAgent``. A conditional
loop-back edge **does** re-enter and re-run the completed collect node (the graph
validator requires loop-back edges to be routed; the scheduler re-runs a
re-triggered COMPLETED node). The one Workflow-specific wrinkle is that
``RemoteA2aAgent``'s built-in resume detection assumes the resolved
``FunctionResponse`` is the *last* session event, which the graph orchestrator
breaks by appending a workflow event after it; the send-path interceptor
(``bridge_client.remote_consumer``) re-detects the pending resume and stamps the
parked A2A ``task_id``/``context_id`` so gate 2/5.3 resume the *same* task. See
``graph.py`` / ADR-0010 / ADR-0012 and docs/lessons-learned A12.

Seams touched (both local-only via SQLite; the GCP adapters are Sprint 2):
**Sessions** (``InMemorySessionService`` -> ``DatabaseSessionService``) and
**Task store** (``InMemoryTaskStore`` -> ``DatabaseTaskStore``). The swaps are a
no-op for the graph — only the service construction + card URL change.
"""

import asyncio

from a2a.server.tasks import DatabaseTaskStore
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService, InMemorySessionService
from google.adk.workflow import Workflow
from google.genai import types
from sqlalchemy.ext.asyncio import create_async_engine

from agents.address.graph import build_address_app, build_address_graph
from agents.address.satisfaction import (
    COLLECTION_STATUS_STATE_KEY,
    _coerce_status,
    is_satisfied,
)
from bridge_client.wire import extract_exchange_turn
from tests.support.live_server import LiveMockServer

PARTY = "jordan-lee"
APP_NAME = "address"
A2A_TASK_ID_META = "a2a:task_id"
A2A_CONTEXT_ID_META = "a2a:context_id"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _latest_turn(events) -> dict | None:
    """Freshest collected ExchangeTurn from an event stream (reversed scan)."""
    return extract_exchange_turn(list(reversed(list(events))))


def _find_paused_call(events):
    """Return the function_call that paused the runner, or None."""
    for event in events:
        if not event.long_running_tool_ids:
            continue
        for fc in event.get_function_calls():
            if fc.id in event.long_running_tool_ids:
                return fc
    return None


def _peer_ids(events) -> tuple[str | None, str | None]:
    """Latest peer A2A (task_id, context_id) from event custom_metadata."""
    task_id = context_id = None
    for event in events:
        meta = event.custom_metadata or {}
        if meta.get(A2A_TASK_ID_META):
            task_id = meta[A2A_TASK_ID_META]
        if meta.get(A2A_CONTEXT_ID_META):
            context_id = meta[A2A_CONTEXT_ID_META]
    return task_id, context_id


def _accepted_issuers(turn: dict | None) -> set[str]:
    """Terminal-outcome fingerprint: the accepted-issuer set for a turn."""
    return set(is_satisfied(_coerce_status(turn or {})).accepted_issuers)


def _collect_message(text: str = "collect the address proof") -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=text)])


def _resume_message(paused) -> types.Content:
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=paused.id,
                    name=paused.name,
                    response={"status": "provided"},
                )
            )
        ],
    )


# --------------------------------------------------------------------------- #
# 5.1 — spike gate 1: RemoteA2aAgent-as-loop-node runs, gate reads its output
# --------------------------------------------------------------------------- #


def _make_runner(card_url: str, session_service) -> Runner:
    """A durable App runner for the graph (collect node owns its own httpx client)."""
    return Runner(
        app=build_address_app(card_url),
        session_service=session_service,
        artifact_service=InMemoryArtifactService(),
    )


async def _run_once_in_memory(card_url: str):
    """Run the graph once under an in-memory App runner; return the final session."""
    session_service = InMemorySessionService()
    runner = _make_runner(card_url, session_service)
    await session_service.create_session(app_name=APP_NAME, user_id=PARTY, session_id="s1")
    async for _ in runner.run_async(user_id=PARTY, session_id="s1", new_message=_collect_message()):
        pass
    session = await session_service.get_session(app_name=APP_NAME, user_id=PARTY, session_id="s1")
    await runner.close()
    return session


def test_gate1_remote_node_runs_and_gate_reads_output():
    """Gate 1: the RemoteA2aAgent node runs in the loop; the gate reads its turn."""
    with LiveMockServer(hold_seconds=0.1, scenario="gov-id-instant") as server:
        session = asyncio.run(_run_once_in_memory(server.card_url))

    # The collected turn landed in shared session state (written by the gate).
    turn = session.state.get(COLLECTION_STATUS_STATE_KEY)
    assert turn is not None, "gate did not record the collected ExchangeTurn to state"
    ledger = turn["status"]["ledger"]
    assert len(ledger) == 1
    assert ledger[0]["id"] == "gov-id-clean"
    assert ledger[0]["disposition"] == "accepted"
    # The deterministic gate judged it done (loop terminated on escalate).
    assert is_satisfied(_coerce_status(turn)).done is True


# --------------------------------------------------------------------------- #
# 5.2 — spike gate 2 + loop iteration: pause/resume INSIDE the loop (no restart)
# --------------------------------------------------------------------------- #


async def _drive_park_resume_in_memory(card_url: str):
    """Park inside the loop, then resume (no restart, no HTTP); return artifacts."""
    session_service = InMemorySessionService()
    runner = _make_runner(card_url, session_service)
    await session_service.create_session(app_name=APP_NAME, user_id=PARTY, session_id="s1")
    first = [
        e
        async for e in runner.run_async(
            user_id=PARTY, session_id="s1", new_message=_collect_message()
        )
    ]
    paused = _find_paused_call(first)
    session_at_park = await session_service.get_session(
        app_name=APP_NAME, user_id=PARTY, session_id="s1"
    )
    collected_at_park = _latest_turn(session_at_park.events)

    if paused is not None:
        async for _ in runner.run_async(
            user_id=PARTY, session_id="s1", new_message=_resume_message(paused)
        ):
            pass
    session = await session_service.get_session(app_name=APP_NAME, user_id=PARTY, session_id="s1")
    await runner.close()
    return paused, collected_at_park, session


def test_gate2_pause_and_resume_inside_loop():
    """Gate 2: input-required pauses the loop; a FunctionResponse resumes it."""
    with LiveMockServer(hold_seconds=0.1, park=True, scenario="two-bills") as server:
        paused, collected_at_park, session = asyncio.run(
            _drive_park_resume_in_memory(server.card_url)
        )

    # The loop paused on the INPUT_REQUIRED long-running call.
    assert paused is not None, "the loop did not pause on the INPUT_REQUIRED park"
    # The collected-so-far ledger (round 1's first bill) was captured before park.
    assert collected_at_park is not None, "no collected turn was persisted before the park"
    assert len(collected_at_park["status"]["ledger"]) == 1

    # After resume the deterministic gate reached the terminal outcome.
    final = session.state.get(COLLECTION_STATUS_STATE_KEY)
    assert final is not None
    assert final["status"]["terminal"] is True
    assert len(final["status"]["ledger"]) == 2
    assert is_satisfied(_coerce_status(final)).done is True


# --------------------------------------------------------------------------- #
# 5.3 — the headline: durable park/resume across a simulated restart (no HTTP)
# --------------------------------------------------------------------------- #


async def _build_task_store(db_path: str) -> DatabaseTaskStore:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    return DatabaseTaskStore(engine=engine, create_table=True)


async def _run_no_restart(card_url: str, db_path: str):
    """Baseline: run park->resume on ONE durable Runner (no restart) for parity."""
    session_service = DatabaseSessionService(db_url=f"sqlite+aiosqlite:///{db_path}")
    runner = _make_runner(card_url, session_service)
    await session_service.create_session(app_name=APP_NAME, user_id=PARTY, session_id="s1")
    first = [
        e
        async for e in runner.run_async(
            user_id=PARTY, session_id="s1", new_message=_collect_message()
        )
    ]
    paused = _find_paused_call(first)
    assert paused is not None
    async for _ in runner.run_async(
        user_id=PARTY, session_id="s1", new_message=_resume_message(paused)
    ):
        pass
    session = await session_service.get_session(app_name=APP_NAME, user_id=PARTY, session_id="s1")
    await runner.close()
    return session.state.get(COLLECTION_STATUS_STATE_KEY)


async def _run_with_restart(card_url: str, consumer_db: str):
    """Park on Runner #1, drop it, resume on a fresh Runner + fresh session svc."""
    db_url = f"sqlite+aiosqlite:///{consumer_db}"

    # --- Runner #1: run the first turn until it parks, then tear everything down.
    session_service_1 = DatabaseSessionService(db_url=db_url)
    runner_1 = _make_runner(card_url, session_service_1)
    await session_service_1.create_session(app_name=APP_NAME, user_id=PARTY, session_id="s1")
    first = [
        e
        async for e in runner_1.run_async(
            user_id=PARTY, session_id="s1", new_message=_collect_message()
        )
    ]
    paused = _find_paused_call(first)
    # Flush sqlite handles before the fresh service reopens the file.
    await runner_1.close()
    del runner_1, session_service_1

    assert paused is not None, "Runner #1 did not park the leg"

    # --- Simulated restart: fresh session service on the SAME db file.
    session_service_2 = DatabaseSessionService(db_url=db_url)
    restored = await session_service_2.get_session(
        app_name=APP_NAME, user_id=PARTY, session_id="s1"
    )

    # Assert restore BEFORE resuming: the collected-so-far ledger, the exchange
    # context, and the peer A2A ids all survived the "restart".
    collected_before_resume = _latest_turn(restored.events)
    peer_task_id, peer_context_id = _peer_ids(restored.events)

    # --- Runner #2: resume the parked leg with a FunctionResponse (no HTTP).
    runner_2 = _make_runner(card_url, session_service_2)
    async for _ in runner_2.run_async(
        user_id=PARTY, session_id="s1", new_message=_resume_message(paused)
    ):
        pass
    final = await session_service_2.get_session(app_name=APP_NAME, user_id=PARTY, session_id="s1")
    await runner_2.close()

    return {
        "collected_before_resume": collected_before_resume,
        "peer_task_id": peer_task_id,
        "peer_context_id": peer_context_id,
        "final_turn": final.state.get(COLLECTION_STATUS_STATE_KEY),
    }


def test_headline_durable_park_resume_across_restart(tmp_path):
    """The parked leg survives a restart and resumes to the same terminal outcome."""
    consumer_db = str(tmp_path / "consumer.db")
    task_db = str(tmp_path / "tasks.db")

    task_store = asyncio.run(_build_task_store(task_db))
    # The mock stays up across the consumer "restart"; only the consumer's Runner
    # + DatabaseSessionService are rebuilt. The mock's task store is durable too
    # (the Task-store seam swap), so the swap is faithful end to end.
    with LiveMockServer(
        hold_seconds=0.1, park=True, scenario="two-bills", task_store=task_store
    ) as server:
        result = asyncio.run(_run_with_restart(server.card_url, consumer_db))

        # Restore assertions (state observed on the fresh service, pre-resume).
        collected = result["collected_before_resume"]
        assert collected is not None, "collected ledger did not survive the restart"
        assert len(collected["status"]["ledger"]) == 1, "round-1 ledger not restored"
        assert result["peer_task_id"], "peer A2A task_id not restored from metadata"
        assert result["peer_context_id"], "peer A2A context_id not restored from metadata"

        # Resume outcome after the restart: terminal with both bills.
        final = result["final_turn"]
        assert final is not None
        assert final["status"]["terminal"] is True
        assert len(final["status"]["ledger"]) == 2
        assert is_satisfied(_coerce_status(final)).done is True

        # Terminal-outcome parity: same accepted-issuer set as an uninterrupted run
        # (never a step-by-step ledger match — docs/lessons-learned B/parity rule).
        baseline_db = str(tmp_path / "baseline.db")
        baseline_final = asyncio.run(_run_no_restart(server.card_url, baseline_db))

    assert baseline_final is not None
    assert _accepted_issuers(final) == _accepted_issuers(baseline_final)
    assert _accepted_issuers(final), "expected a non-empty accepted-issuer set"


def test_build_address_graph_shape():
    """The graph is a Workflow conditional cycle, not a LoopAgent.

    Asserts the edge topology that makes it a durable loop: ``collect -> gate``,
    the conditional ``gate --[again]--> collect`` loop-back edge (the thing a
    ``LoopAgent`` cannot express and the misdiagnosis claimed a ``Workflow``
    could not either), and ``gate --[done]--> present``.
    """
    graph = build_address_graph("http://example.invalid/card.json")
    assert isinstance(graph, Workflow)
    assert not hasattr(graph, "sub_agents"), "a Workflow graph has edges, not sub_agents"

    edges = {(edge.from_node.name, edge.to_node.name, edge.route) for edge in graph.edges}
    assert edges == {
        ("__START__", "document_bridge", None),
        ("document_bridge", "satisfaction_gate", None),
        ("satisfaction_gate", "document_bridge", "again"),  # conditional loop-back
        ("satisfaction_gate", "present", "done"),
    }
