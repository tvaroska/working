"""ADK agent-loader entry point for ``adk web`` / ``adk api_server`` discovery.

``adk web`` enumerates agents with a ``NestedAgentLoader`` that only *lists* a
directory as an agent when it contains an ``agent.py`` (or ``root_agent.yaml``) —
a package that exposes ``app``/``root_agent`` from its ``__init__.py`` loads fine
by name (so ``/run`` works) but never appears in the web UI's app dropdown. This
shim defines the module-level ``app`` (the resumable ``App``) and ``root_agent``
(the bare ``Workflow`` graph) so the address agent is **listed** and loads via the
``address.agent`` module path. The loader prefers a module-level ``app`` (an
``App``) over ``root_agent``, so ``adk web`` surfaces the durable construct
(ResumabilityConfig) — see ``graph.py``.

These are built with the default (environment) Bridge card URL. Tests and the
manual driver call :func:`agents.address.graph.build_address_app` directly to
inject a live mock's card URL (the mock->real seam swap).
"""

from .graph import build_address_app

app = build_address_app()
root_agent = app.root_agent

__all__ = ["app", "root_agent"]
