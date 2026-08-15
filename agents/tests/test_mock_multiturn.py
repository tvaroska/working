"""S1-5 — Multi-turn mock Bridge contract live seam test (terminal-outcome parity).

Drives the two-bills scenario over real sockets and asserts the mock reaches the
same terminal outcome (is_satisfied.done True, accepted issuers {aqua-util, power-co})
over one durable exchange context. Parity is terminal-outcome, not ledger-identical.
"""

import asyncio

from google.adk.agents.invocation_context import (
    InvocationContext,
    new_invocation_context_id,
)
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.tools.tool_context import ToolContext

from agents.address.agent import APP_NAME, PARTY, SKILL
from agents.address.satisfaction import (
    COLLECTION_STATUS_STATE_KEY,
    is_satisfied,
)
from bridge_client import (
    EXCHANGE_CONTEXT_STATE_KEY,
    BridgeAgentTool,
    build_bridge_remote_agent,
)
from contract import CollectionStatus, CollectRequest
from tests.support.live_server import LiveMockServer


async def _make_tool_context(agent) -> ToolContext:
    """Build a real ToolContext backed by an InMemory session for direct tool runs.

    State writes persist on the session across calls (State.__setitem__ writes the
    backing session.state), so re-running the same tool with this context re-seeds
    the next round's child session — exactly the cross-AgentTool channel S1-4 uses.
    """
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=PARTY)
    invocation_context = InvocationContext(
        session_service=session_service,
        invocation_id=new_invocation_context_id(),
        agent=agent,
        session=session,
    )
    return ToolContext(invocation_context)


async def _run_two_rounds(card_url: str):
    """Run two collect rounds reusing the same tool_context (state persists)."""
    bridge = build_bridge_remote_agent(
        card_url,
        name="document_bridge",
        collect_request=CollectRequest(party=PARTY, skill=SKILL),
    )
    tool = BridgeAgentTool(
        bridge,
        skip_summarization=False,
        result_state_key=COLLECTION_STATUS_STATE_KEY,
    )
    tool_context = await _make_tool_context(bridge)

    round1 = await tool.run_async(args={}, tool_context=tool_context)
    state_after_1 = dict(tool_context.state.to_dict())
    round2 = await tool.run_async(args={}, tool_context=tool_context)
    return round1, round2, state_after_1


def test_two_bills_terminal_outcome_parity_live():
    """Two collect rounds reach is_satisfied.done True via 2 distinct issuers."""
    with LiveMockServer(hold_seconds=0.2, scenario="two-bills") as server:
        round1, round2, state_after_1 = asyncio.run(_run_two_rounds(server.card_url))
        context_ids_seen = list(server.executor.context_ids_seen)

    # Round 1: non-empty context id (X), one PowerCo bill, not satisfied.
    x = round1["context_id"]
    assert x, "round 1 turn carried no context id"
    assert len(round1["status"]["ledger"]) == 1
    assert round1["status"]["ledger"][0]["id"] == "bill-powerco-clean"

    status1 = CollectionStatus.model_validate(round1["status"])
    result1 = is_satisfied(status1)
    assert not result1.done, "Round 1 should not be satisfied (only 1 distinct issuer)"

    # After round 1 the parent state holds the collection + threaded context id.
    assert state_after_1[COLLECTION_STATUS_STATE_KEY]["context_id"] == x
    assert state_after_1[EXCHANGE_CONTEXT_STATE_KEY] == x

    # Round 2: same exchange context, terminal=True, is_satisfied.done True.
    assert round2["context_id"] == x
    assert len(context_ids_seen) == 2
    assert context_ids_seen[0] == context_ids_seen[1] == x

    status2 = CollectionStatus.model_validate(round2["status"])
    result2 = is_satisfied(status2)
    assert result2.done, "Round 2 should be satisfied (2 distinct issuers)"
    # Terminal-outcome parity: accepted issuers = {aqua-util, power-co} (sorted).
    assert result2.accepted_issuers == ["aqua-util", "power-co"]
