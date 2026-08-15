"""Network-free, API-key-free tests for the address ``LlmAgent`` scaffold (M0.5).

A ``FakeBridgeClient`` (port double) plus a scripted ``BaseLlm`` stub let the real
``google-adk`` ``LlmAgent`` run one turn deterministically — no sockets, no Gemini.
The live socket round-trip (and WORKING-before-COMPLETED assertion) is M0.6.
"""

import asyncio

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from agents.address import PARTY, SKILL, build_address_agent
from agents.address.agent import run_once
from agents.address.render import collection_to_dict, render_collection
from agents.mock_bridge import build_exchange_turn, load_gov_id_clean_entry
from tests.support.adk_stub import FakeBridgeClient, ScriptedToolCallModel


def _gov_id_clean_turn(context_id: str = "test-ctx-001"):
    return build_exchange_turn(context_id, load_gov_id_clean_entry())


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


def test_build_address_agent_wires_tool():
    agent = build_address_agent(FakeBridgeClient())
    assert isinstance(agent, LlmAgent)
    assert agent.name == "address_agent"
    assert len(agent.tools) == 1
    tool = agent.tools[0]
    assert isinstance(tool, FunctionTool)
    assert tool.name == "collect_address_proof"


def test_agent_runs_one_turn():
    fake_client = FakeBridgeClient()
    agent = build_address_agent(fake_client, model=ScriptedToolCallModel())

    final_text = asyncio.run(run_once(agent))

    # (a) The tool reached the port with the hard-coded party + skill.
    assert len(fake_client.requests) == 1
    request = fake_client.requests[0]
    assert request.party == PARTY == "jordan-lee"
    assert request.skill == SKILL == "address-proof"

    # (b) The turn completed with a final response (stub's fixed final text).
    assert final_text == "Collected the address proof."


def test_agent_tool_result_surfaces_gov_id_clean():
    """The tool closure returns the collection_to_dict payload for gov-id-clean."""
    fake_client = FakeBridgeClient()
    agent = build_address_agent(fake_client, model=ScriptedToolCallModel())
    tool = agent.tools[0]

    result = asyncio.run(tool.func())
    assert result["documents"][0]["id"] == "gov-id-clean"
