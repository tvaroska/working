"""The durable *graph* form of the address agent (S1-6, ADR-0010).

The Collect loop runs as a native ``google.adk.workflow.Workflow`` (a node/edge
graph) on **one shared, durable session**, whose nodes are

1. the **collect node** — the platform-native ``RemoteA2aAgent`` Bridge consumer
   (``build_bridge_remote_agent``), run *directly* as a graph node: ``BaseAgent``
   subclasses the workflow ``BaseNode``, so the remote agent is a node with no
   adapter. A parked (``input-required``) A2A task surfaces as a
   ``LongRunningFunctionTool`` call that pauses the ADK Runner;
2. the deterministic **gate node** (:func:`build_gate`) — a code-only
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

This module holds the graph's reusable *pieces* — the node builders
(:func:`build_collect_node`, :func:`build_gate`, :func:`build_present`) and the
graph constants (names, routes, description). The pieces are assembled into the
``Workflow`` + resumable ``App`` at two sites: the production module-level literal
in ``agent.py`` (env-resolved Bridge card URL) and ``tests/support/app.py`` (a
live mock's URL). The edge wiring is intentionally written at both sites rather
than behind a shared factory — see ADR-0010 §8.
"""

import os

from google.adk.agents.context import Context
from google.adk.workflow import node

from bridge_client import EXCHANGE_CONTEXT_STATE_KEY, build_bridge_remote_agent
from bridge_client.wire import latest_exchange_turn
from contract import CollectRequest

from .config import (
    PARTY,
    SKILL,
)
from .satisfaction import (
    TERMINAL_TURN_STATE_KEY,
    _coerce_status,
    is_satisfied,
)

COLLECT_NODE_NAME = "document_bridge"
GATE_NODE_NAME = "satisfaction_gate"
PRESENT_NODE_NAME = "present"
GRAPH_NAME = "address_collect_loop"
GRAPH_DESCRIPTION = "Durable address-proof Collect loop (S1-6)."

# Route tags the deterministic gate emits on the conditional edges.
ROUTE_AGAIN = "again"  # not done -> loop back into the collect node
ROUTE_DONE = "done"  # done (or the round ceiling hit) -> advance to present

# State key holding the number of completed Collect rounds. Lives on the shared
# session so the ceiling survives a restart just like the ledger does.
ROUND_COUNT_STATE_KEY = "collect_round_count"

# A generous ceiling so a scenario that never terminates fails fast instead of
# looping forever; the deterministic gate normally routes ``done`` well before this.
MAX_ROUNDS = int(os.environ.get("ADDRESS_MAX_ROUNDS", "8"))


def build_collect_node(card_url: str):
    """Build the collect node — the platform-native ``RemoteA2aAgent`` Bridge consumer.

    ``card_url`` is the Bridge Agent Card URL, the single mock->real / local->GCP
    swap point. It is captured into the ``RemoteA2aAgent`` at construction, so each
    assembly site passes the URL it resolved (env default in ``agent.py``; a live
    mock's port in tests). ``rerun_on_resume=True`` means a parked collect leg
    resumes mid-flight (re-run with the resolved ``FunctionResponse``) rather than
    being fast-forwarded on resume.
    """
    return node(
        build_bridge_remote_agent(
            card_url,
            name=COLLECT_NODE_NAME,
            collect_request=CollectRequest(party=PARTY, skill=SKILL),
        ),
        name=COLLECT_NODE_NAME,
        rerun_on_resume=True,
    )


def build_gate(max_rounds: int = MAX_ROUNDS):
    """Build the deterministic loop-gate node — the "code decides" half of Collect.

    The gate reads the latest collected ``ExchangeTurn`` from the shared session,
    records it (and the exchange ``context_id``) to state so it survives a restart
    and so the send-path interceptor threads the same exchange across rounds, then
    calls the authoritative :func:`is_satisfied` and sets ``ctx.route`` to loop
    back (:data:`ROUTE_AGAIN`) or advance (:data:`ROUTE_DONE`). A model is never
    consulted; the route is a pure function of the ledger. A round counter forces
    :data:`ROUTE_DONE` at ``max_rounds`` so a non-terminating scenario cannot loop
    forever.
    """

    async def _gate(ctx: Context) -> None:
        turn = latest_exchange_turn(ctx.session.events)
        done = is_satisfied(_coerce_status(turn or {})).done

        if turn is not None:
            # Record the collected turn (the durable state the restart proof asserts
            # survives) and thread the exchange context so the next round continues
            # the same A2A exchange rather than opening a fresh one.
            ctx.state[TERMINAL_TURN_STATE_KEY] = turn
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
    return ctx.state.get(TERMINAL_TURN_STATE_KEY)


def build_present():
    """Build the terminal present node (see :func:`_present`)."""
    return node(_present, name=PRESENT_NODE_NAME)
