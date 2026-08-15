"""M0 round-trip — agent -> transfer -> native sub-agent -> mock -> agent.

The M0 validation gate, updated for the native consumer (adr-0009): a real ADK
``LlmAgent`` delegates to its ``document_bridge`` sub-agent (a ``RemoteA2aAgent``),
which collects from the live mock Bridge over canonical A2A on a real socket. The
mock's ``gov-id-clean`` ``ExchangeTurn`` must survive the full A2A envelope and be
relayed back into the agent's event stream.

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
from tests.support.a2a_helpers import extract_exchange_turn
from tests.support.adk_stub import ScriptedTransferModel
from tests.support.live_server import LiveMockServer


async def _drive(card_url: str) -> dict | None:
    """Drive the address agent once; return the relayed ExchangeTurn payload."""
    agent = build_address_agent(card_url, model=ScriptedTransferModel())
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
    return extract_exchange_turn(events)


def test_round_trip_agent_bridge_agent():
    """Agent delegates to the native Bridge sub-agent and gets gov-id-clean back."""
    with LiveMockServer(hold_seconds=0.2, park=False) as server:
        payload = asyncio.run(_drive(server.card_url))

    assert payload is not None, "no ExchangeTurn relayed from the Bridge sub-agent"

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
