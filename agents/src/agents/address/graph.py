"""The durable *graph* form of the address agent (S1-6, ADR-0010).

This retires the in-turn ``BridgeAgentTool`` (a fresh throwaway ADK session per
call — which blocks native park/resume, docs/lessons-learned A12) in favour of a
**durable loop on one shared session**: the Collect loop runs as a native ADK
iteration agent whose sub-agents are

1. the **collect node** — the platform-native ``RemoteA2aAgent`` Bridge consumer
   (``build_bridge_remote_agent``), run *directly* as a sub-agent (no
   ``AgentTool`` wrapper). A parked (``input-required``) A2A task surfaces as a
   ``LongRunningFunctionTool`` call that pauses the ADK Runner; and
2. the deterministic **gate node** (:class:`_SatisfactionGate`) — a code-only
   ``BaseAgent`` that reads the latest collected ``ExchangeTurn`` back from the
   *shared* session events, records it to state, and **escalates** (terminates
   the loop) exactly when the authoritative :func:`is_satisfied` says done. No
   model may set the route — "LLM routes, code decides" (A3).

Because the whole loop runs on **one** session, the collected ledger, the
exchange ``context_id``, and the peer A2A ``task_id``/``context_id`` (carried in
event ``custom_metadata``) all live in the durable session store. With a
``DatabaseSessionService`` behind the Sessions seam and
``ResumabilityConfig(is_resumable=True)``, a parked leg survives a process
restart and resumes — with no HTTP webhook and no ``adk web`` — by feeding a
``FunctionResponse`` (matching the paused call) to ``runner.run_async`` on a
fresh Runner pointed at the same database.

**Construct = ``LoopAgent`` (the ADR-0010 §8 fallback), not ``Workflow``.**
The intended construct was ``google.adk.workflow.Workflow`` with a conditional
loop-back edge, but that edge cannot re-enter the collect node: the Workflow
scheduler fast-forwards any node that already COMPLETED in the current
invocation (``workflow.utils._replay_interceptor.check_interception`` Case 1),
so the not-done→collect loop never re-runs — spike gate 2's loop-back portion
fails at runtime. ``LoopAgent`` re-runs its sub-agents each iteration on the
shared session, propagates the ``input-required`` pause, and terminates on
``escalate`` — proven by ``tests/test_durable_graph.py``. It is ``@deprecated``
in ADK 2.7.0; the SDK-risk is tracked under ADR-0001 / ADR-0012. See the ADR-0012
experimental-surface register for the recorded spike outcomes.
"""

import os
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LoopAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.apps import App, ResumabilityConfig
from google.adk.events import Event, EventActions
from google.adk.models import BaseLlm

from bridge_client import build_bridge_remote_agent
from bridge_client.bridge_tool import EXCHANGE_CONTEXT_STATE_KEY
from bridge_client.wire import extract_exchange_turn
from contract import CollectRequest

from .agent import (
    APP_NAME,
    DEFAULT_MODEL,
    PARTY,
    SKILL,
    _default_card_url,
)
from .satisfaction import (
    COLLECTION_STATUS_STATE_KEY,
    _coerce_status,
    is_satisfied,
)

COLLECT_NODE_NAME = "document_bridge"
GATE_NODE_NAME = "satisfaction_gate"
GRAPH_NAME = "address_collect_loop"
# A generous ceiling so a scenario that never terminates fails fast instead of
# looping forever; the deterministic gate normally escalates well before this.
MAX_ROUNDS = int(os.environ.get("ADDRESS_MAX_ROUNDS", "8"))


def _latest_turn(events) -> dict | None:
    """Return the most-recently collected ``ExchangeTurn`` from session events.

    ``wire.extract_exchange_turn`` returns the *first* matching turn in the order
    it scans; the shared session accumulates one artifact per completed round, so
    scanning **reversed** yields the latest (freshest) turn — the one the gate
    must judge. Reusing the wire helper keeps the decode logic in one place.
    """
    return extract_exchange_turn(list(reversed(list(events))))


class _SatisfactionGate(BaseAgent):
    """Deterministic loop gate — the "code decides" half of the Collect loop.

    Reads the latest collected ``ExchangeTurn`` from the shared session, records
    it (and the exchange ``context_id``) to state so it survives a restart and so
    the send-path interceptor threads the same exchange across rounds, then calls
    the authoritative :func:`is_satisfied` and **escalates** (ends the loop) iff
    the collection is done. A model is never consulted; the verdict is a pure
    function of the ledger.
    """

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        turn = _latest_turn(ctx.session.events)
        done = is_satisfied(_coerce_status(turn or {})).done

        state_delta: dict[str, object] = {}
        if turn is not None:
            # Record the collected turn (parity with check_completeness's contract
            # and the durable state the restart proof asserts survives) and thread
            # the exchange context so the next round continues the same A2A
            # exchange rather than opening a fresh one.
            state_delta[COLLECTION_STATUS_STATE_KEY] = turn
            if turn.get("context_id"):
                state_delta[EXCHANGE_CONTEXT_STATE_KEY] = turn["context_id"]

        yield Event(
            author=self.name,
            actions=EventActions(escalate=done, state_delta=state_delta),
        )


def build_address_graph(
    bridge_card_url: str | None = None,
    *,
    model: str | BaseLlm = DEFAULT_MODEL,
    max_rounds: int = MAX_ROUNDS,
) -> LoopAgent:
    """Build the durable Collect-loop graph consuming the Bridge (S1-6).

    Args:
        bridge_card_url: URL of the Bridge's Agent Card — the single mock->real /
            local->GCP swap point; defaults to the environment
            (``BRIDGE_CARD_URL`` / ``BRIDGE_BASE_URL``), mirroring
            :func:`agent.build_address_agent`.
        model: Unused by the deterministic loop today (the gate is code, not a
            model); accepted for signature parity with ``build_address_agent`` so
            a future LLM presenter can be attached without changing callers.
        max_rounds: Loop ceiling (``LoopAgent.max_iterations``).

    Returns:
        A ``LoopAgent`` whose sub-agents are the ``RemoteA2aAgent`` collect node
        and the deterministic :class:`_SatisfactionGate`, to be run on **one
        shared, durable session**.
    """
    del model  # reserved for a future presenter; the gate is deterministic code.
    card_url = bridge_card_url or _default_card_url()
    collect = build_bridge_remote_agent(
        card_url,
        name=COLLECT_NODE_NAME,
        collect_request=CollectRequest(party=PARTY, skill=SKILL),
    )
    gate = _SatisfactionGate(name=GATE_NODE_NAME)

    return LoopAgent(
        name=GRAPH_NAME,
        description="Durable address-proof Collect loop (S1-6).",
        sub_agents=[collect, gate],
        max_iterations=max_rounds,
    )


def build_address_app(
    bridge_card_url: str | None = None,
    *,
    model: str | BaseLlm = DEFAULT_MODEL,
    max_rounds: int = MAX_ROUNDS,
) -> App:
    """Wrap :func:`build_address_graph` in a resumable ``App``.

    ``ResumabilityConfig(is_resumable=True)`` is what makes a parked leg
    resumable across a process restart; it lives on ``App``, so a durable run
    must go through the ``App`` path (not a bare ``agent=``/``node=`` Runner) —
    docs/lessons-learned A13. ``ResumabilityConfig`` is ``@experimental`` in ADK
    2.7.0 (ADR-0012).
    """
    return App(
        name=APP_NAME,
        root_agent=build_address_graph(bridge_card_url, model=model, max_rounds=max_rounds),
        resumability_config=ResumabilityConfig(is_resumable=True),
    )
