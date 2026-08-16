"""ADK agent-loader entry point for ``adk web`` / ``adk api_server`` discovery.

``adk web`` enumerates agents with a ``NestedAgentLoader`` that only *lists* a
directory as an agent when it contains an ``agent.py`` (or ``root_agent.yaml``) —
a package that exposes ``app``/``root_agent`` from its ``__init__.py`` loads fine
by name (so ``/run`` works) but never appears in the web UI's app dropdown. This
module defines the module-level ``app`` (the resumable ``App``) and ``root_agent``
(the bare ``Workflow`` graph) so the address agent is **listed** and loads via the
``address.agent`` module path. The loader prefers a module-level ``app`` (an
``App``) over ``root_agent``, so ``adk web`` surfaces the durable construct
(ResumabilityConfig).

The ``Workflow`` + resumable ``App`` are assembled here as a **module-level
literal** from the node builders in ``graph.py`` (collect -> deterministic gate ->
present, with the conditional loop-back edge). The Bridge Agent Card URL — the
single mock->real / local->GCP swap point — is resolved from the environment
(``BRIDGE_CARD_URL`` / ``BRIDGE_BASE_URL``) via :func:`_default_card_url`, so this
production surface carries no test scaffolding. Tests and the manual driver
assemble their own ``App`` pointed at a live mock's random port via
``tests/support/app.py::build_test_app`` (the same edge wiring, duplicated by
design rather than hidden behind a shared factory — ADR-0010 §8).

``ResumabilityConfig(is_resumable=True)`` is what makes a parked leg resumable
across a process restart; it lives on ``App``, so a durable run must go through the
``App`` path (not a bare ``agent=``/``node=`` Runner) — docs/lessons-learned A13.
``ResumabilityConfig`` is ``@experimental`` in ADK 2.7.0 (ADR-0012). This only
sets the switch; the *durable stores* — ``DatabaseSessionService`` (Sessions seam)
and the Bridge's ``DatabaseTaskStore`` (Task-store seam) — are wired at ``Runner``
construction by the caller (the default ``__main__`` driver runs ``InMemory*`` for
a single-process demo).
"""

from google.adk.apps import App, ResumabilityConfig
from google.adk.workflow import START, Edge, Workflow

from .config import APP_NAME, _default_card_url
from .graph import (
    GRAPH_DESCRIPTION,
    GRAPH_NAME,
    ROUTE_AGAIN,
    ROUTE_DONE,
    build_collect_node,
    build_gate,
    build_present,
)

_collect = build_collect_node(_default_card_url())
_gate = build_gate()
_present = build_present()

root_agent = Workflow(
    name=GRAPH_NAME,
    description=GRAPH_DESCRIPTION,
    edges=[
        Edge(from_node=START, to_node=_collect),
        Edge(from_node=_collect, to_node=_gate),
        # The conditional loop-back edge: not-done re-enters the collect node.
        Edge(from_node=_gate, to_node=_collect, route=ROUTE_AGAIN),
        Edge(from_node=_gate, to_node=_present, route=ROUTE_DONE),
    ],
)

app = App(
    name=APP_NAME,
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)

__all__ = ["app", "root_agent"]
