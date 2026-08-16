"""The durable *graph* form of the address agent (S1-6, ADR-0010).

This retires the in-turn ``BridgeAgentTool`` (a fresh throwaway ADK session per
call — which blocks native park/resume, docs/lessons-learned A12) in favour of a
**durable graph on one shared session**: the Collect loop runs as a native
``google.adk.workflow.Workflow`` (a node/edge graph) whose nodes are

1. the **collect node** — the platform-native ``RemoteA2aAgent`` Bridge consumer
   (``build_bridge_remote_agent``), run *directly* as a graph node (no
   ``AgentTool`` wrapper). ``BaseAgent`` subclasses the workflow ``BaseNode``, so
   the remote agent is a node with no adapter. A parked (``input-required``) A2A
   task surfaces as a ``LongRunningFunctionTool`` call that pauses the ADK Runner;
2. the deterministic **gate node** (:func:`_build_gate`) — a code-only
   ``FunctionNode`` that reads the latest collected ``ExchangeTurn`` back from the
   *shared* session events, records it to state, and sets ``ctx.route`` to loop
   back to the collect node (not done) or advance to the presenter (done). No
   model may set the route — "LLM routes, code decides" (A3); and
3. a terminal **present node** — a code node that exposes the terminal turn as the
   graph's output. (Swap in an ``LlmAgent`` here for a natural-language summary;
   the *routing* decision stays in the deterministic gate.)

The loop is a **conditional cycle**: ``collect -> gate``, ``gate --[again]-->
collect`` (the loop-back edge), ``gate --[done]--> present``. A ``Workflow``
conditional loop-back edge *does* re-enter and re-run the completed collect node:
the graph validator (``utils/_graph_validation.py``) requires loop-back edges to
be conditional (routed), and the scheduler re-runs a re-triggered COMPLETED node
with a fresh ``NodeState`` (``_workflow.py::_process_triggers`` skips a node only
while it is RUNNING or WAITING-with-interrupts). See ADR-0010 §8 / ADR-0012 for
the resolved spike gates.

Because the whole graph runs on **one** session, the collected ledger, the
exchange ``context_id``, and the peer A2A ``task_id``/``context_id`` (carried in
event ``custom_metadata``) all live in the durable session store. With a
``DatabaseSessionService`` behind the Sessions seam and
``ResumabilityConfig(is_resumable=True)``, a parked leg survives a process
restart and resumes — with no HTTP webhook and no ``adk web`` — by feeding a
``FunctionResponse`` (matching the paused call) to ``runner.run_async`` on a
fresh Runner pointed at the same database.
"""

import os

from google.adk.agents.context import Context
from google.adk.apps import App, ResumabilityConfig
from google.adk.models import BaseLlm
from google.adk.workflow import START, Edge, Workflow, node

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
PRESENT_NODE_NAME = "present"
GRAPH_NAME = "address_collect_loop"

# Route tags the deterministic gate emits on the conditional edges.
ROUTE_AGAIN = "again"  # not done -> loop back into the collect node
ROUTE_DONE = "done"  # done (or the round ceiling hit) -> advance to present

# State key holding the number of completed Collect rounds. Lives on the shared
# session so the ceiling survives a restart just like the ledger does.
ROUND_COUNT_STATE_KEY = "collect_round_count"

# A generous ceiling so a scenario that never terminates fails fast instead of
# looping forever; the deterministic gate normally routes ``done`` well before
# this. (Replaces ``LoopAgent.max_iterations``, which the graph no longer has.)
MAX_ROUNDS = int(os.environ.get("ADDRESS_MAX_ROUNDS", "8"))


def _latest_turn(events) -> dict | None:
    """Return the most-recently collected ``ExchangeTurn`` from session events.

    ``wire.extract_exchange_turn`` returns the *first* matching turn in the order
    it scans; the shared session accumulates one artifact per completed round, so
    scanning **reversed** yields the latest (freshest) turn — the one the gate
    must judge. Reusing the wire helper keeps the decode logic in one place.
    """
    return extract_exchange_turn(list(reversed(list(events))))


def _build_gate(max_rounds: int):
    """Build the deterministic loop-gate node — the "code decides" half of Collect.

    The gate reads the latest collected ``ExchangeTurn`` from the shared session,
    records it (and the exchange ``context_id``) to state so it survives a restart
    and so the send-path interceptor threads the same exchange across rounds, then
    calls the authoritative :func:`is_satisfied` and sets ``ctx.route`` to loop
    back (:data:`ROUTE_AGAIN`) or advance (:data:`ROUTE_DONE`). A model is never
    consulted; the route is a pure function of the ledger. A round counter forces
    :data:`ROUTE_DONE` at ``max_rounds`` so a non-terminating scenario cannot loop
    forever (the ``LoopAgent.max_iterations`` ceiling, re-expressed for the graph).
    """

    async def _gate(ctx: Context) -> None:
        turn = _latest_turn(ctx.session.events)
        done = is_satisfied(_coerce_status(turn or {})).done

        if turn is not None:
            # Record the collected turn (parity with check_completeness's contract
            # and the durable state the restart proof asserts survives) and thread
            # the exchange context so the next round continues the same A2A
            # exchange rather than opening a fresh one.
            ctx.state[COLLECTION_STATUS_STATE_KEY] = turn
            if turn.get("context_id"):
                ctx.state[EXCHANGE_CONTEXT_STATE_KEY] = turn["context_id"]

        rounds = int(ctx.state.get(ROUND_COUNT_STATE_KEY, 0)) + 1
        ctx.state[ROUND_COUNT_STATE_KEY] = rounds

        ctx.route = ROUTE_DONE if (done or rounds >= max_rounds) else ROUTE_AGAIN

    return node(_gate, name=GATE_NODE_NAME)


async def _present(ctx: Context) -> dict | None:
    """Terminal node: expose the collected terminal ``ExchangeTurn`` as output.

    Deterministic by design — the routing decision already happened in the gate
    ("LLM routes, code decides"). Swap an ``LlmAgent`` in here for a
    natural-language summary of the terminal turn without touching the loop.
    """
    return ctx.state.get(COLLECTION_STATUS_STATE_KEY)


def build_address_graph(
    bridge_card_url: str | None = None,
    *,
    model: str | BaseLlm = DEFAULT_MODEL,
    max_rounds: int = MAX_ROUNDS,
) -> Workflow:
    """Build the durable Collect-loop graph consuming the Bridge (S1-6).

    Args:
        bridge_card_url: URL of the Bridge's Agent Card — the single mock->real /
            local->GCP swap point; defaults to the environment
            (``BRIDGE_CARD_URL`` / ``BRIDGE_BASE_URL``), mirroring
            :func:`agent.build_address_agent`.
        model: Unused by the deterministic loop today (the gate is code and the
            presenter is code); accepted for signature parity with
            ``build_address_agent`` so an ``LlmAgent`` presenter can be attached
            without changing callers.
        max_rounds: Loop ceiling enforced by the deterministic gate.

    Returns:
        A ``Workflow`` graph whose nodes are the ``RemoteA2aAgent`` collect node,
        the deterministic gate, and a terminal present node, to be run on **one
        shared, durable session**.
    """
    del model  # reserved for a future presenter; the gate/presenter are code.
    card_url = bridge_card_url or _default_card_url()

    # rerun_on_resume=True: a parked collect leg resumes mid-flight (re-run with
    # the resolved FunctionResponse) rather than being fast-forwarded on resume.
    collect = node(
        build_bridge_remote_agent(
            card_url,
            name=COLLECT_NODE_NAME,
            collect_request=CollectRequest(party=PARTY, skill=SKILL),
        ),
        name=COLLECT_NODE_NAME,
        rerun_on_resume=True,
    )
    gate = _build_gate(max_rounds)
    present = node(_present, name=PRESENT_NODE_NAME)

    return Workflow(
        name=GRAPH_NAME,
        description="Durable address-proof Collect loop (S1-6).",
        edges=[
            Edge(from_node=START, to_node=collect),
            Edge(from_node=collect, to_node=gate),
            # The conditional loop-back edge: not-done re-enters the collect node.
            Edge(from_node=gate, to_node=collect, route=ROUTE_AGAIN),
            Edge(from_node=gate, to_node=present, route=ROUTE_DONE),
        ],
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
