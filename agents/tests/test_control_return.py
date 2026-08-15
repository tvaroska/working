"""S1-2 — control-return wiring (``AgentTool``) + structured ``CollectRequest``.

Two changes closed here (adr-0009 amendment open consequences), each covered in
the seam suite:

- **Send path:** the outbound ``message/send`` carries the structured
  ``CollectRequest`` as a single JSON DataPart (not free conversation text). An
  interceptor unit test locks the contract; a live test asserts the mock actually
  received the DataPart.
- **Control return:** the Bridge is wired as a ``BridgeAgentTool`` (call-and-
  return), so control returns to the address agent with the ``ExchangeTurn`` as
  the tool result — a ``function_response`` event exists in the caller's stream
  (the transfer path never emitted one).
"""

import asyncio

from a2a.helpers.proto_helpers import (
    get_data_parts,
    get_message_text,
    new_text_message,
)
from google.adk.runners import InMemoryRunner
from google.genai import types

from agents.address import build_address_agent
from agents.address.agent import APP_NAME, PARTY, SKILL
from bridge_client import build_collect_request_interceptor
from contract import CollectRequest
from tests.support.adk_stub import ScriptedToolCallModel
from tests.support.live_server import LiveMockServer

EXPECTED_DATA = CollectRequest(party=PARTY, skill=SKILL).model_dump(mode="json")


# --------------------------------------------------------------------------- #
# Interceptor unit tests (hermetic — no sockets, no ADK Runner)
# --------------------------------------------------------------------------- #


def test_interceptor_injects_collect_request_datapart():
    """A fresh send (no task_id) is rewritten to the CollectRequest DataPart."""
    interceptor = build_collect_request_interceptor(
        CollectRequest(party=PARTY, skill=SKILL)
    )
    fresh = new_text_message("whatever the model happened to say")

    sentinel = object()
    msg, params = asyncio.run(interceptor.before_request(None, fresh, sentinel))

    assert params is sentinel  # params passed through untouched
    datas = get_data_parts(msg.parts)
    assert len(datas) == 1, "expected exactly one JSON DataPart"
    assert datas[0] == EXPECTED_DATA


def test_interceptor_passthrough_on_resume():
    """A resume request (task_id set) is passed through unchanged (S1-4 guard)."""
    interceptor = build_collect_request_interceptor(
        CollectRequest(party=PARTY, skill=SKILL)
    )
    resume = new_text_message(
        "Here is the requested proof.",
        task_id="task-123",
        context_id="ctx-1",
    )

    msg, _ = asyncio.run(interceptor.before_request(None, resume, None))

    assert msg is resume, "resume request must not be rewritten"
    assert get_message_text(msg) == "Here is the requested proof."
    assert not get_data_parts(msg.parts), "resume must carry no CollectRequest"


# --------------------------------------------------------------------------- #
# Live seam test — send-path DataPart + control return
# --------------------------------------------------------------------------- #


def _find_bridge_function_response(events) -> dict | None:
    """Return the document_bridge tool's function_response payload, or None."""
    for event in events:
        for fr in event.get_function_responses():
            if fr.name == "document_bridge":
                return dict(fr.response)
    return None


async def _drive(card_url: str):
    """Drive the address agent once; return its full event stream."""
    agent = build_address_agent(card_url, model=ScriptedToolCallModel())
    runner = InMemoryRunner(agent, app_name=APP_NAME)
    session_id = "s1-2-control-return"
    await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=PARTY,
        session_id=session_id,
    )
    return [
        event
        async for event in runner.run_async(
            user_id=PARTY,
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text="Collect the address proof.")],
            ),
        )
    ]


def test_send_path_datapart_and_control_return_live():
    """Mock receives the CollectRequest DataPart; control returns with the turn."""
    with LiveMockServer(hold_seconds=0.2, park=False) as server:
        events = asyncio.run(_drive(server.card_url))
        captured = server.executor.last_request_data

    # Send path: the mock received a structured CollectRequest DataPart, not text.
    assert captured is not None, "mock captured no inbound DataPart"
    assert captured["party"] == "jordan-lee"
    assert captured["skill"] == "address-proof"
    assert captured == EXPECTED_DATA

    # Control return: a document_bridge function_response exists in the caller's
    # stream (the turn did not end inside the sub-agent, as transfer would).
    response = _find_bridge_function_response(events)
    assert response is not None, "no document_bridge tool result — control never returned"

    # And that tool result is the gov-id-clean ExchangeTurn (structured dict).
    turn = response if "status" in response else response.get("result", {})
    ledger = turn["status"]["ledger"]
    assert len(ledger) == 1
    doc = ledger[0]
    assert doc["id"] == "gov-id-clean"
    assert doc["doctype"] == "gov-id"
    assert doc["disposition"] == "accepted"
    assert doc["extraction"]["fields"]["key_fields"]["name"] == "Jordan Lee"
    assert (
        doc["extraction"]["fields"]["key_fields"]["address"]
        == "14 Elm Row, Springfield"
    )
