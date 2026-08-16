"""Inbound A2A edge tests (M1.8).

Verifies the real Bridge's inbound A2A edge (``bridge.edges.a2a.app:create_app``):
the dynamic Agent Card (M1.3), the ``_status_for`` mapping, and a contract-faithful
collect round-trip driven through **core** (M1.6 disposition → M1.4 ledger over M1.2
tasks) — real disposition, not the mock's canned fixtures.

The HTTP tests drive the edge in-process via ``httpx.ASGITransport`` and the real
``a2a-sdk`` client (``ClientFactory`` + the card), exercising the canonical spec
methods (``message/send`` + ``tasks/get`` polling) without a live socket / uvicorn.

**Scope (M1.8, per plan §8):** the round-trip is verified at the ``wire.py`` contract
shape *inside* ``bridge/tests`` — it replicates the wire encoding locally and does NOT
import ``agents`` (``bridge/`` never imports ``agents/``; the deeper native-consumer
round-trip through the real ``RemoteA2aAgent`` is M1.13's job, when the cross-package
dep is added). The A11 (non-empty progress message) and A12 (``last_chunk=True`` on a
partial pre-park collection) acceptance criteria are asserted at the event level via a
direct-executor test with a capturing queue, and at the wire level in the park test.
"""

import asyncio
from types import SimpleNamespace

import httpx
import pytest
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.helpers.proto_helpers import (
    get_data_parts,
    get_message_text,
    new_data_message,
    new_text_message,
)
from a2a.types import GetTaskRequest, Role, SendMessageRequest, TaskState
from contract import CollectRequest, Disposition, ExchangeTurn

from bridge.edges.a2a.app import create_app
from bridge.edges.a2a.executor import BridgeExecutor, _status_for
from bridge.edges.a2a.plan import GOV_ID_INSTANT, TWO_BILLS_DISTINCT, plan_for_skill
from bridge.edges.a2a.trust import TrustBoundaryError, authorize_leg

PARTY = "jordan-lee"
SKILL = "address-proof"
BASE_URL = "http://testserver"


# --------------------------------------------------------------------------- #
# Wire encoding replicated locally (bridge/ must not import bridge_client/agents)
# --------------------------------------------------------------------------- #


def _request_message(request: CollectRequest, *, context_id: str | None = None):
    """Encode a CollectRequest as the single JSON DataPart message the wire spec uses."""
    return new_data_message(
        request.model_dump(mode="json"),
        media_type="application/json",
        context_id=context_id or request.context_id or None,
        role=Role.ROLE_USER,
    )


def _turn_from_task(task) -> ExchangeTurn:
    """Decode the ExchangeTurn carried in a completed task's last artifact (wire shape)."""
    assert task.artifacts, "task carried no artifacts"
    datas = get_data_parts(task.artifacts[-1].parts)
    assert datas, "artifact carried no data part"
    turn = ExchangeTurn.model_validate(datas[0])
    if not turn.context_id:
        turn = turn.model_copy(update={"context_id": task.context_id})
    return turn


class _FakeQueue:
    """Capturing event queue for event-level (A11/A12) assertions."""

    def __init__(self):
        self.events = []

    async def enqueue_event(self, event):
        self.events.append(event)


async def _poll(client, task, target, *, timeout: float = 10.0):
    """Poll ``tasks/get`` until the task reaches ``target`` (records observed states)."""
    observed = [task.status.state]
    deadline = asyncio.get_running_loop().time() + timeout
    while task.status.state != target:
        assert asyncio.get_running_loop().time() < deadline, f"never reached {target}"
        await asyncio.sleep(0.02)
        task = await client.get_task(GetTaskRequest(id=task.id))
        observed.append(task.status.state)
    return task, observed


# --------------------------------------------------------------------------- #
# 1 — Dynamic Agent Card (M1.3)
# --------------------------------------------------------------------------- #


@pytest.mark.seam("skill_registry")
@pytest.mark.anyio
async def test_dynamic_agent_card():
    """The edge serves a registry-derived card advertising address-proof + streaming."""
    app = create_app(base_url=BASE_URL, hold_seconds=0.0)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL) as hx:
        resp = await hx.get("/.well-known/agent-card.json")
        assert resp.status_code == 200
        data = resp.json()
        skills = data.get("skills", [])
        assert any(s.get("id") == "address-proof" for s in skills)
        assert data["capabilities"]["streaming"] is True


# --------------------------------------------------------------------------- #
# 2 — _status_for mapping (pure, no server)
# --------------------------------------------------------------------------- #


def test_status_for_mapping():
    """PENDING → INPUT_REQUIRED; ACCEPTED/REJECTED → COMPLETED."""
    assert _status_for(Disposition.PENDING) == TaskState.TASK_STATE_INPUT_REQUIRED
    assert _status_for(Disposition.ACCEPTED) == TaskState.TASK_STATE_COMPLETED
    assert _status_for(Disposition.REJECTED) == TaskState.TASK_STATE_COMPLETED


def test_plan_for_skill_defaults():
    """address-proof resolves to GOV_ID_INSTANT; unknown skills fall back to it."""
    assert plan_for_skill("address-proof") is GOV_ID_INSTANT
    assert plan_for_skill("unknown-skill") is GOV_ID_INSTANT
    # round_for clamps to the final round.
    assert TWO_BILLS_DISTINCT.round_for(5) is TWO_BILLS_DISTINCT.rounds[-1]


# --------------------------------------------------------------------------- #
# 3 — Wire round-trip, instant accept (real disposition through core)
# --------------------------------------------------------------------------- #


@pytest.mark.seam("extraction")
@pytest.mark.anyio
async def test_wire_round_trip_instant_accept():
    """message/send → poll to COMPLETED → decode ExchangeTurn with an accepted gov-id.

    Exercises the canonical spec methods against the wire contract shape, with the
    ledger computed by core (M1.6 classify_document over the fixture extraction), and
    asserts WORKING was observed before COMPLETED (the async surface — A11).
    """
    app = create_app(base_url=BASE_URL, hold_seconds=0.05, collect_plan=GOV_ID_INSTANT)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL) as hx:
        card = await A2ACardResolver(hx, BASE_URL).get_agent_card()
        client = ClientFactory(ClientConfig(httpx_client=hx, streaming=False, polling=True)).create(
            card
        )

        msg = _request_message(CollectRequest(party=PARTY, skill=SKILL))
        task = None
        async for resp in client.send_message(SendMessageRequest(message=msg)):
            assert resp.HasField("task"), "send_message returned a message, not a task"
            task = resp.task
            break
        assert task is not None

        task, observed = await _poll(client, task, TaskState.TASK_STATE_COMPLETED)

    # Async path exercised: WORKING before COMPLETED (A11).
    assert TaskState.TASK_STATE_WORKING in observed
    assert observed.index(TaskState.TASK_STATE_WORKING) < observed.index(
        TaskState.TASK_STATE_COMPLETED
    )

    turn = _turn_from_task(task)
    assert turn.context_id, "context_id must be populated (backfill parity)"
    assert turn.status.terminal is True
    assert len(turn.status.ledger) == 1
    entry = turn.status.ledger[0]
    assert entry.id == "gov-id-clean"
    assert entry.doctype == "gov-id"
    assert entry.disposition == Disposition.ACCEPTED


# --------------------------------------------------------------------------- #
# 4 — Park path (INPUT_REQUIRED) → resume → COMPLETED (distinct-issuer bills)
# --------------------------------------------------------------------------- #


@pytest.mark.seam("extraction")
@pytest.mark.anyio
async def test_park_then_resume_two_bills():
    """First round parks at INPUT_REQUIRED (non-empty message + partial artifact); a
    resume on the same task_id completes with both distinct-issuer bills accepted.

    Terminal-outcome parity (A2): assert the destination, not the step count.
    """
    app = create_app(base_url=BASE_URL, hold_seconds=0.02, collect_plan=TWO_BILLS_DISTINCT)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL) as hx:
        card = await A2ACardResolver(hx, BASE_URL).get_agent_card()
        client = ClientFactory(ClientConfig(httpx_client=hx, streaming=False, polling=True)).create(
            card
        )

        msg = _request_message(CollectRequest(party=PARTY, skill=SKILL))
        task = None
        async for resp in client.send_message(SendMessageRequest(message=msg)):
            task = resp.task
            break
        task, _ = await _poll(client, task, TaskState.TASK_STATE_INPUT_REQUIRED)

        # A11: the park carries a non-empty status.message.
        assert task.status.message is not None
        assert get_message_text(task.status.message).strip()

        # A12: a partial (pre-park) collection is carried in an artifact (last_chunk=True).
        parked_turn = _turn_from_task(task)
        assert parked_turn.status.terminal is False
        assert [e.id for e in parked_turn.status.ledger] == ["bill-powerco-clean"]

        # Resume on the SAME task_id / context_id.
        resume = new_text_message(
            "Here is a second proof.", context_id=task.context_id, task_id=task.id
        )
        async for resp in client.send_message(SendMessageRequest(message=resume)):
            task = resp.task
            break
        task, _ = await _poll(client, task, TaskState.TASK_STATE_COMPLETED)

    final = _turn_from_task(task)
    assert final.status.terminal is True
    ledger = {e.id: e.disposition for e in final.status.ledger}
    assert ledger == {
        "bill-powerco-clean": Disposition.ACCEPTED,
        "bill-aquautil-clean": Disposition.ACCEPTED,
    }
    # Distinct issuers (the app's sense-B rule is satisfiable).
    issuers = {e.issuer for e in final.status.ledger}
    assert issuers == {"power-co", "aqua-util"}


# --------------------------------------------------------------------------- #
# 5 — Event-level A11/A12 (capturing queue, direct executor)
# --------------------------------------------------------------------------- #


@pytest.mark.seam("extraction")
@pytest.mark.anyio
async def test_executor_emits_nonempty_progress_and_last_chunk_artifact():
    """Task(SUBMITTED) → WORKING(non-empty msg) → artifact(last_chunk=True) → COMPLETED.

    Event-level proof of A11 (non-empty status.message on progress) and A12
    (last_chunk=True on the emitted artifact) — the acceptance criteria the wire tests
    exercise incidentally, made explicit here.
    """
    from bridge.adapters.local.extraction import FixtureExtractionEngine

    executor = BridgeExecutor(engine=FixtureExtractionEngine(), collect_plan=GOV_ID_INSTANT)
    queue = _FakeQueue()
    message = _request_message(CollectRequest(party=PARTY, skill=SKILL))
    context = SimpleNamespace(
        task_id="t1",
        context_id="ctx-1",
        current_task=None,
        message=message,
        call_context=None,
    )

    await executor.execute(context, queue)

    # First event: Task(SUBMITTED).
    assert queue.events[0].status.state == TaskState.TASK_STATE_SUBMITTED

    # A11: at least one WORKING event carries a non-empty status.message.
    working = [
        e
        for e in queue.events
        if hasattr(e, "status") and e.status.state == TaskState.TASK_STATE_WORKING
    ]
    assert working
    assert any(e.status.message and get_message_text(e.status.message).strip() for e in working)

    # A12: the artifact event is flagged last_chunk=True.
    artifact_events = [e for e in queue.events if hasattr(e, "artifact")]
    assert artifact_events
    assert getattr(artifact_events[-1], "last_chunk", False) is True

    # Terminal: COMPLETED, with an accepted gov-id in the decoded artifact.
    assert queue.events[-1].status.state == TaskState.TASK_STATE_COMPLETED
    datas = get_data_parts(artifact_events[-1].artifact.parts)
    turn = ExchangeTurn.model_validate(datas[0])
    assert turn.status.ledger[0].id == "gov-id-clean"
    assert turn.status.ledger[0].disposition == Disposition.ACCEPTED


# --------------------------------------------------------------------------- #
# 6 — Trust boundary permissive-by-default (A6)
# --------------------------------------------------------------------------- #


def test_authorize_leg_permissive_by_default():
    """None caller is a no-op; mismatch is allowed unless strict; strict mismatch raises."""
    # Unauthenticated caller: no-op regardless of mode.
    authorize_leg(None, PARTY)
    authorize_leg(None, PARTY, strict=True)
    # Permissive default: a mismatched caller is allowed.
    authorize_leg("someone-else", PARTY)
    # Matching caller under strict: allowed.
    authorize_leg(PARTY, PARTY, strict=True)
    # Mismatched caller under strict: rejected.
    with pytest.raises(TrustBoundaryError):
        authorize_leg("someone-else", PARTY, strict=True)


@pytest.mark.anyio
async def test_edge_permissive_no_caller_succeeds():
    """A request with no caller identity succeeds even under strict=True (permissive A6)."""
    app = create_app(base_url=BASE_URL, hold_seconds=0.0, strict=True)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL) as hx:
        card = await A2ACardResolver(hx, BASE_URL).get_agent_card()
        client = ClientFactory(ClientConfig(httpx_client=hx, streaming=False, polling=True)).create(
            card
        )
        msg = _request_message(CollectRequest(party=PARTY, skill=SKILL))
        task = None
        async for resp in client.send_message(SendMessageRequest(message=msg)):
            task = resp.task
            break
        task, _ = await _poll(client, task, TaskState.TASK_STATE_COMPLETED)
    assert _turn_from_task(task).status.ledger[0].id == "gov-id-clean"


@pytest.mark.anyio
async def test_edge_strict_rejects_mismatched_caller():
    """Under strict=True a mismatched authenticated caller is rejected (server-level A6)."""
    from bridge.adapters.local.extraction import FixtureExtractionEngine

    executor = BridgeExecutor(engine=FixtureExtractionEngine(), strict=True)
    queue = _FakeQueue()
    message = _request_message(CollectRequest(party=PARTY, skill=SKILL))
    call_context = SimpleNamespace(user=None, state={"caller": "impersonator"})
    context = SimpleNamespace(
        task_id="t1",
        context_id="ctx-strict",
        current_task=None,
        message=message,
        call_context=call_context,
    )
    with pytest.raises(TrustBoundaryError):
        await executor.execute(context, queue)
