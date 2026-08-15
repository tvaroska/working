"""M0 round-trip — agent -> ``document_bridge`` tool -> mock -> agent.

The M0 validation gate, updated for the S1-2 call-and-return wiring (adr-0009): a
real ADK ``LlmAgent`` calls its ``document_bridge`` ``BridgeAgentTool`` (a
``RemoteA2aAgent`` underneath), which collects from the live mock Bridge over
canonical A2A on a real socket. The mock's ``gov-id-clean`` ``ExchangeTurn`` must
survive the full A2A envelope and come back as the **tool result** (control
returned to the caller — the transfer path never did).

Wire-level state ordering (WORKING before COMPLETED) is locked separately by the
raw-client contract test (``test_native_consumer.py`` Test A); here we assert the
payload fidelity end to end through the agent + native construct.
"""

import asyncio
import json
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

from agents.address import build_address_agent
from agents.address.agent import APP_NAME, PARTY
from tests.support.adk_stub import ScriptedToolCallModel
from tests.support.live_server import LiveMockServer


def _tool_result_turn(events) -> dict | None:
    """Return the ExchangeTurn dict carried by the document_bridge tool response."""
    for event in events:
        for fr in event.get_function_responses():
            if fr.name != "document_bridge":
                continue
            resp = fr.response
            # ADK may wrap a non-dict tool result under a 'result' key.
            if isinstance(resp, dict) and "status" in resp:
                return resp
            if isinstance(resp, dict) and isinstance(resp.get("result"), dict):
                return resp["result"]
    return None


async def _drive(card_url: str) -> dict | None:
    """Drive the address agent once; return the ExchangeTurn from the tool result."""
    agent = build_address_agent(card_url, model=ScriptedToolCallModel())
    runner = InMemoryRunner(agent, app_name=APP_NAME)
    session_id = "m0-round-trip"
    await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=PARTY,
        session_id=session_id,
    )

    events = [
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
    return _tool_result_turn(events)


def test_round_trip_agent_bridge_agent():
    """Agent calls the Bridge tool and gets gov-id-clean back as the tool result."""
    with LiveMockServer(hold_seconds=0.2, park=False) as server:
        payload = asyncio.run(_drive(server.card_url))

    assert payload is not None, "no ExchangeTurn returned as the tool result"

    # Payload fidelity against raw expected.json (avoids tautology with fixtures).
    evals_path = Path(__file__).resolve().parents[2] / "wiki/evals/address/expected.json"
    evals = json.loads(evals_path.read_text())
    gov = next(d for d in evals["documents"] if d["id"] == "gov-id-clean")
    expected_key_fields = gov["extraction"]["fields"]["key_fields"]

    ledger = payload["status"]["ledger"]
    assert len(ledger) == 1
    doc = ledger[0]
    assert doc["id"] == "gov-id-clean"
    assert doc["doctype"] == "gov-id"
    assert doc["disposition"] == "accepted"
    assert doc["extraction"]["fields"]["key_fields"] == expected_key_fields
    assert doc["extraction"]["fields"]["key_fields"]["name"] == "Jordan Lee"
    assert doc["extraction"]["fields"]["key_fields"]["address"] == "14 Elm Row, Springfield"
