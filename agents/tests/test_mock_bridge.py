"""Tests for the mock Document Bridge (fixtures, executor, card, app).

Network-free tests. The live round-trip (agent -> mock -> agent over real sockets)
is in M0.6.
"""

import asyncio
from types import SimpleNamespace

import httpx
import pytest
from a2a.helpers.proto_helpers import get_data_parts
from a2a.types import TaskState
from a2a.utils.constants import TransportProtocol

from agents.mock_bridge import (
    build_agent_card,
    build_exchange_turn,
    create_app,
    load_gov_id_clean_entry,
)
from contract import Disposition, ExchangeTurn


def test_load_gov_id_clean_entry():
    """Load the gov-id-clean entry from the eval fixture and validate its shape."""
    entry = load_gov_id_clean_entry()

    assert entry.id == "gov-id-clean"
    assert entry.doctype == "gov-id"
    assert entry.issuer is None
    assert entry.disposition == Disposition.ACCEPTED
    assert entry.extraction.overall_confidence == 0.96
    assert entry.extraction.fields.key_fields["name"] == "Jordan Lee"
    assert entry.extraction.fields.key_fields["address"] == "14 Elm Row, Springfield"
    assert entry.extraction.legible is True


def test_build_exchange_turn():
    """Build an ExchangeTurn wrapping one ledger entry."""
    entry = load_gov_id_clean_entry()
    turn = build_exchange_turn("ctx-1", entry)

    assert turn.context_id == "ctx-1"
    assert turn.status.terminal is True
    assert len(turn.status.ledger) == 1
    assert turn.status.ledger[0].id == "gov-id-clean"
    assert turn.status.outstanding == []


def test_executor_emits_working_then_completed():
    """Drive the executor with a fake event queue; assert WORKING precedes COMPLETED.

    This proves the emitted wire shape matches what ``wire.task_to_exchange_turn``
    reads — parity by discipline.
    """
    from agents.mock_bridge import GOV_ID_INSTANT, MockBridgeExecutor

    # Capturing fake event queue (avoids depending on internal RequestContext/Queue)
    class FakeQueue:
        def __init__(self):
            self.events = []

        async def enqueue_event(self, event):
            self.events.append(event)

    executor = MockBridgeExecutor(GOV_ID_INSTANT, hold_seconds=0.0)
    queue = FakeQueue()
    context = SimpleNamespace(task_id="t1", context_id="ctx-1", current_task=None)

    asyncio.run(executor.execute(context, queue))

    # Assert event sequence: Task(SUBMITTED) -> WORKING -> artifact -> COMPLETED
    assert len(queue.events) >= 4
    # First event: Task with SUBMITTED state
    assert hasattr(queue.events[0], "status")
    assert queue.events[0].status.state == TaskState.TASK_STATE_SUBMITTED
    # Second event: WORKING
    assert hasattr(queue.events[1], "status")
    assert queue.events[1].status.state == TaskState.TASK_STATE_WORKING

    # Find the artifact event
    artifact_event = None
    for event in queue.events:
        if hasattr(event, "artifact"):
            artifact_event = event
            break
    assert artifact_event is not None

    # Final event: COMPLETED
    assert hasattr(queue.events[-1], "status")
    assert queue.events[-1].status.state == TaskState.TASK_STATE_COMPLETED

    # Decode the artifact and validate it round-trips to the expected turn
    data_parts = get_data_parts(artifact_event.artifact.parts)
    assert len(data_parts) == 1
    decoded_turn = ExchangeTurn.model_validate(data_parts[0])
    assert decoded_turn.context_id == "ctx-1"
    assert decoded_turn.status.terminal is True
    assert len(decoded_turn.status.ledger) == 1
    assert decoded_turn.status.ledger[0].id == "gov-id-clean"


def test_build_agent_card():
    """Build the Agent Card and validate its structure."""
    card = build_agent_card("http://127.0.0.1:8080")

    assert card.name == "Mock Document Bridge"
    # streaming=True so the native RemoteA2aAgent consumer receives progress
    # TaskStatusUpdateEvents (adr-0009).
    assert card.capabilities.streaming is True
    assert card.capabilities.push_notifications is False

    # Find the JSONRPC interface
    jsonrpc_interface = None
    for iface in card.supported_interfaces:
        if iface.protocol_binding == TransportProtocol.JSONRPC.value:
            jsonrpc_interface = iface
            break
    assert jsonrpc_interface is not None
    assert jsonrpc_interface.url == "http://127.0.0.1:8080/"

    # Find the address-proof skill
    address_skill = None
    for skill in card.skills:
        if skill.id == "address-proof":
            address_skill = skill
            break
    assert address_skill is not None
    assert address_skill.name == "Address proof collection"


@pytest.mark.anyio
async def test_create_app_serves_card():
    """In-process ASGI test: GET the Agent Card via httpx.AsyncClient.

    This proves the card is served at the right path and is JSON-decodable.
    The full message/send -> poll -> COMPLETED flow is in M0.6 (needs real sockets).
    """
    app = create_app(base_url="http://testserver", hold_seconds=0.0)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/.well-known/agent-card.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert data["name"] == "Mock Document Bridge"
        # Verify the address-proof skill is in the JSON
        skills = data.get("skills", [])
        assert any(s.get("id") == "address-proof" for s in skills)


# --------------------------------------------------------------------------- #
# S1-5 — Multi-turn scenario tests
# --------------------------------------------------------------------------- #


def test_load_entry_distinct_issuer_bills():
    """Load distinct-issuer bill fixtures and validate canonical issuers."""
    from agents.mock_bridge import load_entry

    powerco = load_entry("bill-powerco-clean")
    assert powerco.id == "bill-powerco-clean"
    assert powerco.doctype == "utility-bill"
    assert powerco.issuer == "power-co"
    assert powerco.disposition == Disposition.ACCEPTED

    aqua = load_entry("bill-aquautil-clean")
    assert aqua.id == "bill-aquautil-clean"
    assert aqua.doctype == "utility-bill"
    assert aqua.issuer == "aqua-util"
    assert aqua.disposition == Disposition.ACCEPTED


def test_two_bills_scenario_steps():
    """TWO_BILLS scenario steps: round 0 not terminal, round 1 terminal, clamp."""
    from agents.mock_bridge import TWO_BILLS

    # Round 0: not terminal, 1 ledger id, outstanding utility-bill, chase messages.
    step0 = TWO_BILLS.step_for_round(0)
    assert not step0.terminal
    assert step0.ledger_ids == ("bill-powerco-clean",)
    assert step0.outstanding == ("utility-bill",)
    assert len(step0.chase_messages) > 0

    # Round 1: terminal, 2 ledger ids, no outstanding.
    step1 = TWO_BILLS.step_for_round(1)
    assert step1.terminal
    assert step1.ledger_ids == ("bill-powerco-clean", "bill-aquautil-clean")
    assert step1.outstanding == ()

    # Round 2: clamps to the terminal step.
    step2 = TWO_BILLS.step_for_round(2)
    assert step2 is step1


def test_executor_two_bills_multiturn():
    """Executor drives TWO_BILLS scenario: round 1 not terminal, round 2 terminal."""
    from a2a.helpers.proto_helpers import get_message_text

    from agents.mock_bridge import TWO_BILLS, MockBridgeExecutor

    class FakeQueue:
        def __init__(self):
            self.events = []

        async def enqueue_event(self, event):
            self.events.append(event)

    executor = MockBridgeExecutor(TWO_BILLS, hold_seconds=0.0)

    # Round 1
    queue1 = FakeQueue()
    ctx1 = SimpleNamespace(task_id="t1", context_id="ctx-1", current_task=None)
    asyncio.run(executor.execute(ctx1, queue1))

    # At least one WORKING event has a non-empty status.message (faked chase).
    working_events = [
        e
        for e in queue1.events
        if hasattr(e, "status") and e.status.state == TaskState.TASK_STATE_WORKING
    ]
    assert len(working_events) > 0
    chase_found = any(
        get_message_text(e.status.message) for e in working_events if e.status.message
    )
    assert chase_found, "Expected at least one WORKING event with non-empty status.message"

    # Final event: COMPLETED
    assert queue1.events[-1].status.state == TaskState.TASK_STATE_COMPLETED

    # Decode the artifact
    artifact_event = next(e for e in queue1.events if hasattr(e, "artifact"))
    data_parts = get_data_parts(artifact_event.artifact.parts)
    turn1 = ExchangeTurn.model_validate(data_parts[0])
    assert not turn1.status.terminal
    assert len(turn1.status.ledger) == 1
    assert turn1.status.ledger[0].id == "bill-powerco-clean"

    # Round 2 (same context_id)
    queue2 = FakeQueue()
    ctx2 = SimpleNamespace(task_id="t2", context_id="ctx-1", current_task=None)
    asyncio.run(executor.execute(ctx2, queue2))

    assert queue2.events[-1].status.state == TaskState.TASK_STATE_COMPLETED
    artifact_event2 = next(e for e in queue2.events if hasattr(e, "artifact"))
    data_parts2 = get_data_parts(artifact_event2.artifact.parts)
    turn2 = ExchangeTurn.model_validate(data_parts2[0])
    assert turn2.status.terminal
    assert len(turn2.status.ledger) == 2
    ledger_ids = {e.id for e in turn2.status.ledger}
    assert ledger_ids == {"bill-powerco-clean", "bill-aquautil-clean"}
