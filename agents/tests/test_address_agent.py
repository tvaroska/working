"""Structural tests for the address ``LlmAgent`` + pure render helpers.

The agent is a real ``google-adk`` ``LlmAgent`` whose sole sub-agent is the
native ``RemoteA2aAgent`` Bridge consumer (adr-0009). These tests are hermetic
(no sockets, no API key): they assert wiring shape only. The live
transfer -> sub-agent -> mock round-trip is ``test_round_trip.py``.
"""

from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

from agents.address import build_address_agent
from agents.address.agent import BRIDGE_SUBAGENT_NAME
from agents.address.render import collection_to_dict, render_collection
from agents.mock_bridge import build_exchange_turn, load_gov_id_clean_entry

CARD_URL = "http://127.0.0.1:8080/.well-known/agent-card.json"


def _gov_id_clean_turn(context_id: str = "test-ctx-001"):
    return build_exchange_turn(context_id, load_gov_id_clean_entry())


def test_build_address_agent_wires_bridge_subagent():
    agent = build_address_agent(CARD_URL)
    assert isinstance(agent, LlmAgent)
    assert agent.name == "address_agent"
    assert agent.output_key == "address_result"

    # The Bridge is consumed as a single native RemoteA2aAgent sub-agent.
    assert len(agent.sub_agents) == 1
    bridge = agent.sub_agents[0]
    assert isinstance(bridge, RemoteA2aAgent)
    assert bridge.name == BRIDGE_SUBAGENT_NAME == "document_bridge"

    # No hand-rolled FunctionTool consumer any more (adr-0009).
    assert not agent.tools


def test_render_collection():
    turn = _gov_id_clean_turn()
    rendered = render_collection(turn)
    assert "gov-id-clean" in rendered
    assert "gov-id" in rendered
    assert "Jordan Lee" in rendered
    assert "14 Elm Row, Springfield" in rendered


def test_collection_to_dict():
    turn = _gov_id_clean_turn(context_id="ctx-xyz")
    result = collection_to_dict(turn)
    assert result["context_id"] == "ctx-xyz"
    assert len(result["documents"]) == 1
    doc = result["documents"][0]
    assert doc["id"] == "gov-id-clean"
    assert doc["doctype"] == "gov-id"
    assert doc["key_fields"]["name"] == "Jordan Lee"
    assert doc["key_fields"]["address"] == "14 Elm Row, Springfield"
