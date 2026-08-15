"""Network-free unit tests for the BridgeClient port and its a2a-sdk adapter.

Covers the wire encode/decode helpers, context-id backfill, malformed-payload
error, and port abstractness. The live end-to-end round-trip is M0.6.
"""

import asyncio

import pytest
from a2a.helpers.proto_helpers import get_data_parts, new_data_part
from a2a.types import Artifact, Part, Role, Task, TaskState, TaskStatus

from bridge_client import (
    A2ABridgeClient,
    BridgeClient,
    BridgeClientError,
    request_to_message,
    task_to_exchange_turn,
)
from contract import (
    CollectionStatus,
    CollectRequest,
    Disposition,
    ExchangeTurn,
    ExtractedFields,
    Extraction,
    LedgerEntry,
)


def _gov_id_clean_turn(context_id: str = "test-ctx-001") -> ExchangeTurn:
    """The M0.2 gov-id-clean shape, mirrored from tests/test_contract.py."""
    return ExchangeTurn(
        context_id=context_id,
        status=CollectionStatus(
            ledger=[
                LedgerEntry(
                    id="gov-id-clean",
                    doctype="gov-id",
                    issuer=None,
                    disposition=Disposition.ACCEPTED,
                    extraction=Extraction(
                        fields=ExtractedFields(
                            doctype="gov-id",
                            issuer=None,
                            key_fields={
                                "name": "Jordan Lee",
                                "address": "14 Elm Row, Springfield",
                                "doc_number": "DL-8392047",
                            },
                        ),
                        overall_confidence=0.96,
                        legible=True,
                    ),
                )
            ],
            outstanding=[],
            terminal=True,
        ),
    )


def _task_with_turn(turn: ExchangeTurn, *, context_id: str) -> Task:
    part = new_data_part(turn.model_dump(mode="json"))
    artifact = Artifact(artifact_id="art-1", parts=[part])
    return Task(
        id="t-1",
        context_id=context_id,
        status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
        artifacts=[artifact],
    )


def test_request_to_message_roundtrip():
    request = CollectRequest(party="jordan-lee", skill="address-proof")
    msg = request_to_message(request)

    assert msg.role == Role.ROLE_USER
    assert get_data_parts(msg.parts)[0] == request.model_dump(mode="json")


def test_request_to_message_carries_context_id():
    request = CollectRequest(party="jordan-lee", skill="address-proof", context_id="ctx-1")
    msg = request_to_message(request)
    assert msg.context_id == "ctx-1"

    # With context_id=None it still builds (empty proto context id).
    none_msg = request_to_message(CollectRequest(party="jordan-lee", skill="address-proof"))
    assert none_msg.context_id == ""


def test_task_to_exchange_turn_decodes_artifact():
    turn = _gov_id_clean_turn()
    task = _task_with_turn(turn, context_id="test-ctx-001")

    decoded = task_to_exchange_turn(task)
    assert decoded == turn


def test_task_to_exchange_turn_backfills_context_id():
    turn = _gov_id_clean_turn(context_id="")
    task = _task_with_turn(turn, context_id="ctx-9")

    decoded = task_to_exchange_turn(task)
    assert decoded.context_id == "ctx-9"


def test_task_to_exchange_turn_raises_on_missing_data_part():
    # No artifacts at all.
    empty = Task(
        id="t-2",
        context_id="ctx-2",
        status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
    )
    with pytest.raises(BridgeClientError):
        task_to_exchange_turn(empty)

    # An artifact with only a text part (no data part).
    text_only = Task(
        id="t-3",
        context_id="ctx-3",
        status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
        artifacts=[Artifact(artifact_id="a", parts=[Part(text="not json")])],
    )
    with pytest.raises(BridgeClientError):
        task_to_exchange_turn(text_only)


def test_port_is_abstract():
    with pytest.raises(TypeError):
        BridgeClient()  # type: ignore[abstract]

    assert issubclass(A2ABridgeClient, BridgeClient)


def test_collect_errors_offline():
    """Point the adapter at an unroutable URL; collect must funnel to BridgeClientError.

    The card resolve fails fast offline, so this stays quick and network-free in
    effect (no live server is reachable). Driven with asyncio.run to avoid a
    pytest-asyncio dependency.
    """

    async def _run() -> None:
        client = A2ABridgeClient(
            "http://127.0.0.1:1",
            poll_interval=0.01,
            poll_timeout=0.1,
        )
        try:
            with pytest.raises(BridgeClientError):
                await client.collect(CollectRequest(party="jordan-lee", skill="address-proof"))
        finally:
            await client.aclose()

    asyncio.run(_run())
