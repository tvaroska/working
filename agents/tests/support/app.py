"""Test-only construction of the address ``App`` bound to a specific Bridge URL.

The production surface (``agents.address.agent``) assembles its ``Workflow`` + ``App``
as a module-level literal from the graph node builders, resolving the Bridge Agent
Card URL from the environment (``BRIDGE_CARD_URL`` / ``BRIDGE_BASE_URL``). Tests and
the manual driver, however, spin up a :class:`~tests.support.live_server.LiveMockServer`
on a random free port and must point the agent at *that* URL.

:func:`build_test_app` assembles the same graph (collect -> deterministic gate ->
present, with the conditional loop-back edge) with the collect node pointed straight
at ``card_url``. The edge wiring is duplicated from ``agent.py`` by design — the
graph *pieces* are shared (``graph.py``), but the top-level assembly is written at
each site rather than hidden behind a shared factory (ADR-0010 §8). Because
``card_url`` is passed directly to the collect-node builder, this needs no env
mutation.
"""

from google.adk.apps import App, ResumabilityConfig
from google.adk.workflow import START, Edge, Workflow

from agents.address.config import APP_NAME
from agents.address.graph import (
    GRAPH_DESCRIPTION,
    GRAPH_NAME,
    MAX_ROUNDS,
    ROUTE_AGAIN,
    ROUTE_DONE,
    build_collect_node,
    build_gate,
    build_present,
)


def build_test_app(card_url: str, *, max_rounds: int = MAX_ROUNDS):
    """Build the address ``App`` pointed at ``card_url`` (a live mock's card URL)."""
    collect = build_collect_node(card_url)
    gate = build_gate(max_rounds=max_rounds)
    present = build_present()

    graph = Workflow(
        name=GRAPH_NAME,
        description=GRAPH_DESCRIPTION,
        edges=[
            Edge(from_node=START, to_node=collect),
            Edge(from_node=collect, to_node=gate),
            # The conditional loop-back edge: not-done re-enters the collect node.
            Edge(from_node=gate, to_node=collect, route=ROUTE_AGAIN),
            Edge(from_node=gate, to_node=present, route=ROUTE_DONE),
        ],
    )

    return App(
        name=APP_NAME,
        root_agent=graph,
        resumability_config=ResumabilityConfig(is_resumable=True),
    )
