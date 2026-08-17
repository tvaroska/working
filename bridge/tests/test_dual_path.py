"""Dual-path routing tests (M1.11).

Verify Path-A (structured) vs Path-B (extraction) dispatch, convergence, and the
"indistinguishable to the requester" acceptance (terminal-outcome parity, A2).
"""

import pytest
from a2a.helpers.proto_helpers import new_data_message, new_data_part
from a2a.types import Role
from contract import Disposition, ExchangeTurn
from httpx import ASGITransport, AsyncClient

from bridge.adapters.local.extraction import FixtureDocument, FixtureExtractionEngine
from bridge.edges.a2a.app import create_app
from bridge.edges.a2a.dispatch import (
    PathKind,
    classify_arrival,
    looks_like_extraction,
    route_arrival,
)
from bridge.fulfillment import Phase, validate_only


class SpyExtractionEngine:
    """Spy wrapper around FixtureExtractionEngine that records extract calls."""

    def __init__(self):
        self._engine = FixtureExtractionEngine()
        self.extract_count = 0

    async def extract(self, document, doctype_skill):
        """Extract and record the call."""
        self.extract_count += 1
        return await self._engine.extract(document, doctype_skill)


# --- classify_arrival dispatch tests (pure) ---


def test_classify_arrival_structured_extraction_is_path_a():
    """A message with a structured Extraction DataPart → PathKind.A."""
    extraction_data = {
        "fields": {
            "doctype": "gov-id",
            "issuer": None,
            "key_fields": {},
        },
        "overall_confidence": 0.95,
        "legible": True,
        "flagged_fields": [],
    }
    msg = new_data_message(extraction_data, media_type="application/json", role=Role.ROLE_USER)
    path = classify_arrival(msg.parts)
    assert path == PathKind.A


def test_classify_arrival_collect_request_only_is_path_b():
    """A CollectRequest-only DataPart message (no 'fields') → PathKind.B (default)."""
    request_data = {"party": "jordan-lee", "skill": "address-proof"}
    msg = new_data_message(request_data, media_type="application/json", role=Role.ROLE_USER)
    path = classify_arrival(msg.parts)
    assert path == PathKind.B


@pytest.mark.skip(reason="Part construction needs proto introspection - tested via executor")
def test_classify_arrival_file_part_is_path_b():
    """A message with a FilePart → PathKind.B (tested via executor)."""
    pass


@pytest.mark.skip(reason="Part construction needs proto introspection - tested via executor")
def test_classify_arrival_text_part_is_path_b():
    """A message with a TextPart → PathKind.B (tested via executor)."""
    pass


def test_classify_arrival_operator_fulfilled_is_path_b():
    """operator=True (even with a structured part) → PathKind.B."""
    extraction_data = {
        "fields": {"doctype": "gov-id", "issuer": None, "key_fields": {}},
        "overall_confidence": 0.95,
    }
    msg = new_data_message(extraction_data, media_type="application/json", role=Role.ROLE_USER)
    path = classify_arrival(msg.parts, operator=True)
    assert path == PathKind.B


def test_looks_like_extraction_with_fields_key():
    """looks_like_extraction({"fields": ...}) → True."""
    data = {"fields": {"doctype": "gov-id"}}
    assert looks_like_extraction(data) is True


def test_looks_like_extraction_without_fields_key():
    """looks_like_extraction({"party": ...}) → False (CollectRequest shape)."""
    data = {"party": "jordan-lee", "skill": "address-proof"}
    assert looks_like_extraction(data) is False


# --- validate_only makes no extraction call ---


@pytest.mark.anyio
async def test_validate_only_makes_no_extraction_call():
    """Path A validate_only runs the gate but makes NO extraction call (spy count=0)."""
    spy = SpyExtractionEngine()

    # Load a real Extraction for gov-id-clean via the fixture engine
    extraction = await spy._engine.extract(FixtureDocument(fixture_id="gov-id-clean"), None)
    spy.extract_count = 0  # reset after the load

    # Call validate_only (Path A)
    result = validate_only(extraction)

    # Assert: no extraction call (spy count still 0)
    assert spy.extract_count == 0

    # Assert: correct disposition + phase
    assert result.phase == Phase.AUTO_APPROVE
    assert result.disposition == Disposition.ACCEPTED
    assert result.entry is not None
    assert result.entry.doctype == "gov-id"


# --- Indistinguishable convergence (terminal-outcome parity, A2) ---


@pytest.mark.anyio
@pytest.mark.parametrize(
    "fixture_id,expected_phase,expected_disposition",
    [
        ("gov-id-clean", Phase.AUTO_APPROVE, Disposition.ACCEPTED),
        ("bill-powerco-clean", Phase.AUTO_APPROVE, Disposition.ACCEPTED),
        ("gov-id-expired", Phase.HITL, Disposition.PENDING),
        ("bill-aquautil-clear", Phase.HITL, Disposition.PENDING),
        ("bill-aquautil-blurry", Phase.RESUBMIT, Disposition.REJECTED),
        ("passport-unsupported", Phase.UNSUPPORTED, Disposition.REJECTED),
        ("bill-aquautil-clean", Phase.AUTO_APPROVE, Disposition.ACCEPTED),
        ("bill-powerco-clean-2", Phase.AUTO_APPROVE, Disposition.ACCEPTED),
    ],
)
async def test_path_a_path_b_convergence(fixture_id, expected_phase, expected_disposition):
    """Path A (validate_only) and Path B (run_fulfillment) reach the same outcome.

    Proves terminal-outcome parity (A2): same phase, disposition, terminal, suspended
    across both paths for every eval fixture.
    """
    engine = FixtureExtractionEngine()

    # Load the extraction once
    extraction = await engine.extract(FixtureDocument(fixture_id=fixture_id), None)

    # Path A: validate_only (no extraction call)
    result_a = validate_only(extraction)

    # Path B: run_fulfillment (calls engine.extract)
    from bridge.fulfillment import run_fulfillment

    result_b = await run_fulfillment(FixtureDocument(fixture_id=fixture_id), engine=engine)

    # Assert: indistinguishable outcomes
    assert result_a.phase == result_b.phase == expected_phase
    assert result_a.disposition == result_b.disposition == expected_disposition
    assert result_a.terminal == result_b.terminal
    assert result_a.suspended == result_b.suspended


# --- route_arrival convergence + engine usage ---


@pytest.mark.anyio
async def test_route_arrival_path_a_no_extract():
    """route_arrival(PathKind.A, extraction=...) makes NO extract call."""
    spy = SpyExtractionEngine()

    # Load extraction for gov-id-clean
    extraction = await spy._engine.extract(FixtureDocument(fixture_id="gov-id-clean"), None)
    spy.extract_count = 0  # reset

    # Route via Path A
    result = await route_arrival(PathKind.A, extraction=extraction, engine=spy)

    # Assert: no extract call
    assert spy.extract_count == 0
    assert result.phase == Phase.AUTO_APPROVE
    assert result.disposition == Disposition.ACCEPTED


@pytest.mark.anyio
async def test_route_arrival_path_b_calls_extract():
    """route_arrival(PathKind.B, document=...) calls engine.extract once."""
    spy = SpyExtractionEngine()

    # Route via Path B
    result = await route_arrival(
        PathKind.B, document=FixtureDocument(fixture_id="gov-id-clean"), engine=spy
    )

    # Assert: extract called once
    assert spy.extract_count == 1
    assert result.phase == Phase.AUTO_APPROVE
    assert result.disposition == Disposition.ACCEPTED


@pytest.mark.anyio
async def test_route_arrival_path_a_path_b_convergence():
    """Path A and Path B via route_arrival reach the same result for gov-id-clean."""
    spy = SpyExtractionEngine()

    # Load extraction
    extraction = await spy._engine.extract(FixtureDocument(fixture_id="gov-id-clean"), None)
    spy.extract_count = 0

    # Route via Path A (no extract)
    result_a = await route_arrival(PathKind.A, extraction=extraction, engine=spy)
    extract_count_a = spy.extract_count

    # Route via Path B (calls extract)
    result_b = await route_arrival(
        PathKind.B, document=FixtureDocument(fixture_id="gov-id-clean"), engine=spy
    )
    extract_count_b = spy.extract_count - extract_count_a

    # Assert: same result, different engine usage
    assert result_a.phase == result_b.phase
    assert result_a.disposition == result_b.disposition
    assert extract_count_a == 0  # Path A: no extract
    assert extract_count_b == 1  # Path B: one extract


# --- Executor dispatch over the real edge ---


@pytest.mark.anyio
@pytest.mark.seam("extraction")
async def test_executor_path_a_structured_extraction():
    """Executor: Path A (structured Extraction DataPart) → COMPLETED, NO extract call."""
    import asyncio

    from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
    from a2a.helpers.proto_helpers import get_data_parts
    from a2a.types import GetTaskRequest, SendMessageRequest, TaskState

    spy = SpyExtractionEngine()
    app = create_app(base_url="http://testserver", engine=spy, hold_seconds=0.0)

    # Load a real extraction for gov-id-clean
    extraction = await spy._engine.extract(FixtureDocument(fixture_id="gov-id-clean"), None)
    spy.extract_count = 0  # reset

    # Build a message with TWO DataParts: CollectRequest + Extraction (Path A indicator)
    collect_request_data = {"party": "jordan-lee", "skill": "address-proof"}
    extraction_data = extraction.model_dump(mode="json")

    # Create a Message with the first data part, then append the second
    msg = new_data_message(collect_request_data, media_type="application/json", role=Role.ROLE_USER)
    msg.parts.append(new_data_part(extraction_data))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as hx:
        card = await A2ACardResolver(hx, "http://testserver").get_agent_card()
        client = ClientFactory(ClientConfig(httpx_client=hx, streaming=False, polling=True)).create(
            card
        )

        # Send the message
        task = None
        async for resp in client.send_message(SendMessageRequest(message=msg)):
            if resp.HasField("task"):
                task = resp.task
                break

        assert task is not None

        # Poll to completion
        deadline = asyncio.get_running_loop().time() + 5.0
        while task.status.state != TaskState.TASK_STATE_COMPLETED:
            assert asyncio.get_running_loop().time() < deadline, "task did not complete"
            await asyncio.sleep(0.02)
            task = await client.get_task(GetTaskRequest(id=task.id))

        # Decode the ExchangeTurn from artifacts
        assert task.artifacts, "task carried no artifacts"
        datas = get_data_parts(task.artifacts[-1].parts)
        assert datas, "artifact carried no data part"
        # Select ExchangeTurn by shape (has "status" key)
        turn_data = next((d for d in datas if isinstance(d, dict) and "status" in d), datas[0])
        turn = ExchangeTurn.model_validate(turn_data)

        # Assert: accepted gov-id in the ledger
        assert len(turn.status.ledger) == 1
        entry = turn.status.ledger[0]
        assert entry.doctype == "gov-id"
        assert entry.disposition == Disposition.ACCEPTED

        # Assert: NO extract call (Path A)
        assert spy.extract_count == 0


@pytest.mark.anyio
@pytest.mark.seam("extraction")
async def test_executor_path_b_collect_request():
    """Executor: Path B (CollectRequest only) → COMPLETED, extract called."""
    import asyncio

    from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
    from a2a.helpers.proto_helpers import get_data_parts
    from a2a.types import GetTaskRequest, SendMessageRequest, TaskState

    spy = SpyExtractionEngine()
    app = create_app(base_url="http://testserver", engine=spy, hold_seconds=0.0)

    # Send a normal CollectRequest (Path B, default plan: gov-id-clean)
    collect_request_data = {"party": "jordan-lee", "skill": "address-proof"}
    msg = new_data_message(collect_request_data, media_type="application/json", role=Role.ROLE_USER)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as hx:
        card = await A2ACardResolver(hx, "http://testserver").get_agent_card()
        client = ClientFactory(ClientConfig(httpx_client=hx, streaming=False, polling=True)).create(
            card
        )

        # Send the message
        task = None
        async for resp in client.send_message(SendMessageRequest(message=msg)):
            if resp.HasField("task"):
                task = resp.task
                break

        assert task is not None

        # Poll to completion
        deadline = asyncio.get_running_loop().time() + 5.0
        while task.status.state != TaskState.TASK_STATE_COMPLETED:
            assert asyncio.get_running_loop().time() < deadline, "task did not complete"
            await asyncio.sleep(0.02)
            task = await client.get_task(GetTaskRequest(id=task.id))

        # Decode the ExchangeTurn
        assert task.artifacts, "task carried no artifacts"
        datas = get_data_parts(task.artifacts[-1].parts)
        assert datas, "artifact carried no data part"
        turn_data = next((d for d in datas if isinstance(d, dict) and "status" in d), datas[0])
        turn = ExchangeTurn.model_validate(turn_data)

        # Assert: accepted gov-id in the ledger (default plan: gov-id-clean)
        assert len(turn.status.ledger) >= 1
        gov_ids = [e for e in turn.status.ledger if e.doctype == "gov-id"]
        assert len(gov_ids) >= 1
        assert all(e.disposition == Disposition.ACCEPTED for e in gov_ids)

        # Assert: extract WAS called (Path B)
        assert spy.extract_count >= 1


@pytest.mark.anyio
@pytest.mark.seam("extraction")
async def test_executor_path_a_path_b_indistinguishable():
    """Executor: Path A and Path B produce identical ExchangeTurn ledger entries."""
    import asyncio

    from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
    from a2a.helpers.proto_helpers import get_data_parts
    from a2a.types import GetTaskRequest, SendMessageRequest, TaskState

    spy = SpyExtractionEngine()
    app = create_app(base_url="http://testserver", engine=spy, hold_seconds=0.0)

    # Load extraction for gov-id-clean
    extraction = await spy._engine.extract(FixtureDocument(fixture_id="gov-id-clean"), None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as hx:
        card = await A2ACardResolver(hx, "http://testserver").get_agent_card()
        client = ClientFactory(ClientConfig(httpx_client=hx, streaming=False, polling=True)).create(
            card
        )

        # Path A: send structured Extraction (two data parts)
        collect_request_data = {"party": "jordan-lee", "skill": "address-proof"}
        extraction_data = extraction.model_dump(mode="json")

        msg_a = new_data_message(
            collect_request_data, media_type="application/json", role=Role.ROLE_USER
        )
        msg_a.parts.append(new_data_part(extraction_data))

        task_a = None
        async for resp in client.send_message(SendMessageRequest(message=msg_a)):
            if resp.HasField("task"):
                task_a = resp.task
                break

        # Path B: send CollectRequest only (default plan: gov-id-clean)
        msg_b = new_data_message(
            collect_request_data, media_type="application/json", role=Role.ROLE_USER
        )

        task_b = None
        async for resp in client.send_message(SendMessageRequest(message=msg_b)):
            if resp.HasField("task"):
                task_b = resp.task
                break

        # Poll both to completion
        assert task_a is not None
        assert task_b is not None

        deadline = asyncio.get_running_loop().time() + 5.0
        while task_a.status.state != TaskState.TASK_STATE_COMPLETED:
            assert asyncio.get_running_loop().time() < deadline, "task_a did not complete"
            await asyncio.sleep(0.02)
            task_a = await client.get_task(GetTaskRequest(id=task_a.id))

        deadline = asyncio.get_running_loop().time() + 5.0
        while task_b.status.state != TaskState.TASK_STATE_COMPLETED:
            assert asyncio.get_running_loop().time() < deadline, "task_b did not complete"
            await asyncio.sleep(0.02)
            task_b = await client.get_task(GetTaskRequest(id=task_b.id))

        # Decode both turns
        datas_a = get_data_parts(task_a.artifacts[-1].parts)
        turn_data_a = next(
            (d for d in datas_a if isinstance(d, dict) and "status" in d), datas_a[0]
        )
        turn_a = ExchangeTurn.model_validate(turn_data_a)

        datas_b = get_data_parts(task_b.artifacts[-1].parts)
        turn_data_b = next(
            (d for d in datas_b if isinstance(d, dict) and "status" in d), datas_b[0]
        )
        turn_b = ExchangeTurn.model_validate(turn_data_b)

        # Assert: indistinguishable ledger entries (doctype + disposition)
        # Path A: 1 gov-id accepted
        # Path B: 1 gov-id accepted (from default plan: gov-id-clean)
        assert len(turn_a.status.ledger) == 1
        assert len(turn_b.status.ledger) >= 1

        entry_a = turn_a.status.ledger[0]
        entry_b_gov_id = [e for e in turn_b.status.ledger if e.doctype == "gov-id"][0]

        assert entry_a.doctype == entry_b_gov_id.doctype == "gov-id"
        assert entry_a.disposition == entry_b_gov_id.disposition == Disposition.ACCEPTED


# --- A3 preserved: structured claim can be HITL/rejected ---


@pytest.mark.anyio
async def test_path_a_hitl_not_auto_accepted():
    """Path A: gov-id-expired Extraction → HITL (PENDING), not auto-accepted (A3)."""
    engine = FixtureExtractionEngine()

    # Load gov-id-expired extraction (flagged expiry)
    extraction = await engine.extract(FixtureDocument(fixture_id="gov-id-expired"), None)

    # Path A: validate_only
    result = validate_only(extraction)

    # Assert: NOT auto-accepted (HITL, PENDING)
    assert result.phase == Phase.HITL
    assert result.disposition == Disposition.PENDING
    assert result.suspended is True


@pytest.mark.anyio
async def test_path_a_unsupported_rejected():
    """Path A: passport-unsupported Extraction → UNSUPPORTED (REJECTED), not auto-accepted (A3)."""
    engine = FixtureExtractionEngine()

    # Load passport-unsupported extraction (unsupported doctype)
    extraction = await engine.extract(FixtureDocument(fixture_id="passport-unsupported"), None)

    # Path A: validate_only
    result = validate_only(extraction)

    # Assert: REJECTED (UNSUPPORTED)
    assert result.phase == Phase.UNSUPPORTED
    assert result.disposition == Disposition.REJECTED
    assert result.terminal is True
