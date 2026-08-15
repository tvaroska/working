"""S1-4 — the multi-turn Collect loop (durable exchange context across rounds).

Three properties are locked here (see
``.claude/plans/S1-4-multi-turn-collect-loop.md``):

- **Send-path context threading** (hermetic interceptor unit test): a fresh send
  stamps the exchange ``context_id`` threaded through session state, so the loop
  continues one exchange; resume requests still pass through unchanged.
- **Durable exchange context** (live seam test, real sockets): two ``document_bridge``
  collect rounds against the live mock carry the **same** A2A ``context_id`` — no
  fresh context per round — and ``BridgeAgentTool`` writes both the returned turn and
  the context id to parent session state.
- **Loop iteration** (hermetic): with a fake Bridge tool scripted not-satisfying then
  satisfying, the model routes on the authoritative ``check_completeness`` gate —
  collect → gate(not done) → chase → gate(done) → terminate — and stops.
"""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from a2a.helpers.proto_helpers import get_data_parts, new_text_message
from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import (
    InvocationContext,
    new_invocation_context_id,
)
from google.adk.runners import InMemoryRunner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from agents.address.agent import APP_NAME, PARTY, SKILL
from agents.address.satisfaction import COLLECTION_STATUS_STATE_KEY, check_completeness
from bridge_client import (
    EXCHANGE_CONTEXT_STATE_KEY,
    BridgeAgentTool,
    build_bridge_remote_agent,
    build_collect_request_interceptor,
)
from contract import (
    CollectionStatus,
    CollectRequest,
    Disposition,
    ExchangeTurn,
    Extraction,
    LedgerEntry,
)
from tests.support.adk_stub import ScriptedLoopModel
from tests.support.live_server import LiveMockServer

EXPECTED_DATA = CollectRequest(party=PARTY, skill=SKILL).model_dump(mode="json")


# --------------------------------------------------------------------------- #
# 1. Interceptor context-threading unit tests (hermetic — no sockets, no ADK)
# --------------------------------------------------------------------------- #


def _fake_ctx(state: dict) -> SimpleNamespace:
    """A minimal ctx exposing ``ctx.session.state`` (the only field read)."""
    return SimpleNamespace(session=SimpleNamespace(state=state))


def test_interceptor_threads_context_from_state():
    """A fresh send stamps the exchange context id threaded through state."""
    interceptor = build_collect_request_interceptor(CollectRequest(party=PARTY, skill=SKILL))
    ctx = _fake_ctx({EXCHANGE_CONTEXT_STATE_KEY: "ctx-abc"})
    fresh = new_text_message("whatever the model happened to say")

    msg, _ = asyncio.run(interceptor.before_request(ctx, fresh, None))

    assert msg.context_id == "ctx-abc"
    datas = get_data_parts(msg.parts)
    assert len(datas) == 1
    assert datas[0] == EXPECTED_DATA


def test_interceptor_no_state_leaves_context_empty():
    """No threaded state -> fresh send falls back to an empty context id."""
    interceptor = build_collect_request_interceptor(CollectRequest(party=PARTY, skill=SKILL))
    ctx = _fake_ctx({})
    fresh = new_text_message("kickoff")

    msg, _ = asyncio.run(interceptor.before_request(ctx, fresh, None))

    assert not msg.context_id  # empty / unset -> a fresh exchange
    assert get_data_parts(msg.parts)[0] == EXPECTED_DATA


def test_interceptor_passthrough_on_resume_with_state():
    """A resume request (task_id set) is passed through unchanged even with state."""
    interceptor = build_collect_request_interceptor(CollectRequest(party=PARTY, skill=SKILL))
    ctx = _fake_ctx({EXCHANGE_CONTEXT_STATE_KEY: "ctx-abc"})
    resume = new_text_message(
        "Here is the requested proof.", task_id="task-123", context_id="ctx-1"
    )

    msg, _ = asyncio.run(interceptor.before_request(ctx, resume, None))

    assert msg is resume  # not rewritten
    assert not get_data_parts(msg.parts)  # no CollectRequest injected


# --------------------------------------------------------------------------- #
# 2. Live durable-context seam test (real sockets) — the headline S1-4 property
# --------------------------------------------------------------------------- #


async def _make_tool_context(agent) -> ToolContext:
    """Build a real ToolContext backed by an InMemory session for direct tool runs.

    State writes persist on the session across calls (State.__setitem__ writes the
    backing session.state), so re-running the same tool with this context re-seeds
    the next round's child session — exactly the cross-AgentTool channel S1-4 uses.
    """
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=PARTY)
    invocation_context = InvocationContext(
        session_service=session_service,
        invocation_id=new_invocation_context_id(),
        agent=agent,
        session=session,
    )
    return ToolContext(invocation_context)


async def _run_two_rounds(card_url: str):
    bridge = build_bridge_remote_agent(
        card_url,
        name="document_bridge",
        collect_request=CollectRequest(party=PARTY, skill=SKILL),
    )
    tool = BridgeAgentTool(
        bridge,
        skip_summarization=False,
        result_state_key=COLLECTION_STATUS_STATE_KEY,
    )
    tool_context = await _make_tool_context(bridge)

    round1 = await tool.run_async(args={}, tool_context=tool_context)
    state_after_1 = dict(tool_context.state.to_dict())
    round2 = await tool.run_async(args={}, tool_context=tool_context)
    return round1, round2, state_after_1


def test_durable_exchange_context_spans_rounds_live():
    """Two collect rounds share one A2A context; the tool threads it via state."""
    with LiveMockServer(hold_seconds=0.2, park=False) as server:
        round1, round2, state_after_1 = asyncio.run(_run_two_rounds(server.card_url))
        context_ids_seen = list(server.executor.context_ids_seen)

    # Round 1 returned an ExchangeTurn with a non-empty context id (X).
    x = round1["context_id"]
    assert x, "round 1 turn carried no context id"
    assert round1["status"]["ledger"][0]["id"] == "gov-id-clean"

    # After round 1 the parent state holds the collection + threaded context id.
    assert state_after_1[COLLECTION_STATUS_STATE_KEY]["context_id"] == x
    assert state_after_1[EXCHANGE_CONTEXT_STATE_KEY] == x

    # Round 2 continued the SAME exchange (no fresh context per round).
    assert round2["context_id"] == x
    assert len(context_ids_seen) == 2
    assert context_ids_seen[0] == context_ids_seen[1] == x


# --------------------------------------------------------------------------- #
# 3. Hermetic loop-orchestration test — iterate + terminate on the gate
# --------------------------------------------------------------------------- #


def _load_evals() -> dict:
    path = Path(__file__).resolve().parents[2] / "wiki/evals/address/expected.json"
    return json.loads(path.read_text())


def _ledger_entry(entry_id: str) -> LedgerEntry:
    data = _load_evals()
    raw = next(e for e in data["documents"] if e["id"] == entry_id)
    return LedgerEntry(
        id=raw["id"],
        doctype=raw["doctype"],
        issuer=raw["issuer"],
        disposition=Disposition(raw["expected_disposition"]),
        extraction=Extraction.model_validate(raw["extraction"]),
    )


def _turn(*entry_ids: str, done: bool) -> dict:
    """Build an ExchangeTurn dict from eval ledger entries."""
    return ExchangeTurn(
        context_id="loop-ctx",
        status=CollectionStatus(
            ledger=[_ledger_entry(i) for i in entry_ids],
            outstanding=[] if done else ["gov-id", "utility-bill"],
            terminal=done,
        ),
    ).model_dump(mode="json")


def _make_fake_bridge_tool(scripted_turns: list[dict]):
    """A fake ``document_bridge`` that pops scripted turns and writes them to state.

    Mimics ``BridgeAgentTool``'s state write (under COLLECTION_STATUS_STATE_KEY) so
    the real ``check_completeness`` gate reads it. Raises past the scripted turns so
    a runaway loop fails the test rather than spinning forever.
    """
    calls = {"n": 0}

    async def document_bridge(tool_context: ToolContext) -> dict:
        i = calls["n"]
        calls["n"] += 1
        if i >= len(scripted_turns):
            raise AssertionError(
                "document_bridge called more than scripted — loop did not terminate"
            )
        turn = scripted_turns[i]
        tool_context.state[COLLECTION_STATUS_STATE_KEY] = turn
        return turn

    return document_bridge, calls


def test_loop_iterates_until_gate_satisfied():
    """Not-done -> chase -> done -> terminate, routed by the authoritative gate."""
    # Round 1: one accepted bill (1 distinct issuer) -> not satisfied.
    # Round 2: add a second distinct-issuer accepted bill -> satisfied.
    scripted = [
        _turn("bill-powerco-clean", done=False),
        _turn("bill-powerco-clean", "bill-aquautil-clean", done=True),
    ]
    fake_bridge, calls = _make_fake_bridge_tool(scripted)

    agent = LlmAgent(
        name="address_agent",
        model=ScriptedLoopModel(),
        instruction="loop",
        tools=[fake_bridge, check_completeness],
        output_key="address_result",
    )

    async def drive():
        runner = InMemoryRunner(agent, app_name=APP_NAME)
        await runner.session_service.create_session(
            app_name=APP_NAME, user_id=PARTY, session_id="loop"
        )
        records = {"bridge": 0, "gate_verdicts": [], "final_text": ""}
        async for event in runner.run_async(
            user_id=PARTY,
            session_id="loop",
            new_message=types.Content(role="user", parts=[types.Part(text="collect")]),
        ):
            for fr in event.get_function_responses():
                if fr.name == "document_bridge":
                    records["bridge"] += 1
                elif fr.name == "check_completeness":
                    resp = dict(fr.response or {})
                    if "done" not in resp and isinstance(resp.get("result"), dict):
                        resp = resp["result"]
                    records["gate_verdicts"].append(resp["done"])
            if event.is_final_response() and event.content and event.content.parts:
                text = "".join(p.text or "" for p in event.content.parts)
                if text:
                    records["final_text"] = text
        return records

    records = asyncio.run(drive())

    # The Bridge (fake) was called twice — chased once after the not-done verdict.
    assert calls["n"] == 2
    assert records["bridge"] == 2
    # The gate ran each round; first verdict not done, final verdict done.
    assert records["gate_verdicts"] == [False, True]
    # The agent terminated with a final text response (no infinite loop).
    assert records["final_text"] == "Address proof collected."
