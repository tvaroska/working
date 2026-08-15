"""Structural tests for the address ``LlmAgent`` + pure render helpers.

The agent is a real ``google-adk`` ``LlmAgent`` whose sole tool is a
``BridgeAgentTool`` wrapping the native ``RemoteA2aAgent`` Bridge consumer
(adr-0009 / S1-2 call-and-return). These tests are hermetic (no sockets, no API
key): they assert wiring shape only. The live tool -> mock round-trip is
``test_control_return.py``.
"""

import asyncio

from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.tools.function_tool import FunctionTool

from agents.address import build_address_agent, check_completeness
from agents.address.agent import BRIDGE_TOOL_NAME, GATE_TOOL_NAME
from agents.address.render import collection_to_dict, render_collection
from agents.mock_bridge import build_exchange_turn, load_gov_id_clean_entry
from bridge_client import BridgeAgentTool

CARD_URL = "http://127.0.0.1:8080/.well-known/agent-card.json"


def _gov_id_clean_turn(context_id: str = "test-ctx-001"):
    return build_exchange_turn(context_id, load_gov_id_clean_entry())


def test_build_address_agent_wires_bridge_tool():
    agent = build_address_agent(CARD_URL)
    assert isinstance(agent, LlmAgent)
    assert agent.name == "address_agent"
    assert agent.output_key == "address_result"

    # S1-4 Collect loop: two tools — the Bridge collect (call-and-return) and the
    # authoritative completeness gate the model routes on.
    assert len(agent.tools) == 2

    # The Bridge is consumed as a call-and-return AgentTool (S1-2), so control
    # returns to the address agent with the ExchangeTurn; it writes the turn to
    # state under COLLECTION_STATUS_STATE_KEY for the gate (S1-4).
    tool = agent.tools[0]
    assert isinstance(tool, BridgeAgentTool)
    assert tool.name == BRIDGE_TOOL_NAME == "document_bridge"
    assert tool.result_state_key == "collection_status"
    assert isinstance(tool.agent, RemoteA2aAgent)
    assert tool.agent.name == "document_bridge"

    # The second tool is the authoritative check_completeness gate — the model
    # routes, code decides. ADK stores the raw callable and wraps it lazily as a
    # FunctionTool; assert both the callable identity and the resolved wrapper.
    assert agent.tools[1] is check_completeness
    resolved = asyncio.run(agent.canonical_tools())
    gate = resolved[1]
    assert isinstance(gate, FunctionTool)
    assert gate.name == GATE_TOOL_NAME == "check_completeness"

    # No transfer sub-agent any more — the transfer path never returned control.
    assert not agent.sub_agents


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
