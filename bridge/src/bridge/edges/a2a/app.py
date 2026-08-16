"""Inbound A2A edge assembly — Agent Card + Starlette app (M1.8).

Mirrors the mock's ``create_app`` factory (``agents/src/agents/mock_bridge/app.py``):
``DefaultRequestHandler(agent_executor, task_store, agent_card)`` + the canonical
``create_agent_card_routes`` / ``create_jsonrpc_routes`` behind a Starlette app whose
lifespan closes the handler. The real edge differs only in *where the ledger comes
from* (bridge core, not canned fixtures) and in the trust boundary + ``_status_for``
mapping carried by :class:`~bridge.edges.a2a.executor.BridgeExecutor`.

The Agent Card is **dynamic**, built from the skill registry (M1.3) — the same source
the mock→real swap (M1.13) will leave unchanged for the consumer. ``base_url`` defaults
to ``:8000`` to match the C2 port map (core = 8000).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskStore
from a2a.types import AgentCapabilities, AgentCard
from starlette.applications import Starlette

from bridge.adapters.local.extraction import FixtureExtractionEngine
from bridge.adapters.local.skill_registry import LocalSkillRegistry
from bridge.seams.extraction import ExtractionSeam

from .executor import BridgeExecutor
from .plan import CollectPlan

__all__ = ["build_agent_card", "create_app"]


def build_agent_card(
    base_url: str,
    *,
    registry: LocalSkillRegistry | None = None,
    version: str = "0.0.0",
) -> AgentCard:
    """Build the dynamic Agent Card from the skill registry (M1.3).

    Advertises the registry's process skills (``address-proof`` by default) and sets
    ``streaming=True`` so the native ``RemoteA2aAgent`` consumer receives progress
    ``TaskStatusUpdateEvent``s (parity with the mock).

    Args:
        base_url: The externally reachable base URL (the card interface URL is
            ``f"{base_url}/"``).
        registry: The skill registry. Defaults to ``LocalSkillRegistry()``.
        version: The card version.

    Returns:
        The dynamic Agent Card.
    """
    registry = registry or LocalSkillRegistry()
    return registry.build_agent_card(
        base_url=base_url,
        version=version,
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
    )


def create_app(
    base_url: str = "http://127.0.0.1:8000",
    *,
    registry: LocalSkillRegistry | None = None,
    engine: ExtractionSeam | None = None,
    task_store: TaskStore | None = None,
    collect_plan: CollectPlan | None = None,
    strict: bool = False,
    hold_seconds: float = 0.0,
) -> Starlette:
    """Create the real Bridge's inbound A2A edge Starlette application (M1.8).

    Args:
        base_url: The externally reachable base URL (baked into the Agent Card;
            interface URL is ``f"{base_url}/"``). Defaults to ``:8000`` (C2 port map).
        registry: Skill registry (card source, M1.3). Defaults to
            ``LocalSkillRegistry()`` (loads ``skills/``; honors ``BRIDGE_SKILLS_DIR``).
        engine: Extraction seam driving collect content. Defaults to
            ``FixtureExtractionEngine()``.
        task_store: The JSON-RPC handler's task store. Defaults to
            ``InMemoryTaskStore()`` (the in→durable swap is a no-op for the consumer).
        collect_plan: An explicit collect plan applied to every request; when None the
            plan is resolved per-request by skill.
        strict: Trust boundary mode (A6). Permissive by default.
        hold_seconds: Progress hold before completing (shrinkable for tests).

    Returns:
        A Starlette app serving the Agent Card at ``/.well-known/agent-card.json`` and
        JSON-RPC at ``/``.
    """
    registry = registry or LocalSkillRegistry()
    engine = engine or FixtureExtractionEngine()

    card = build_agent_card(base_url, registry=registry)
    # The registry loads skills/ by default; the edge advertises the address-proof
    # process skill (M1.3). Fail loud if it is missing rather than serving a card the
    # consumer cannot route against.
    assert any(s.id == "address-proof" for s in card.skills), (
        "Agent Card must advertise the address-proof process skill (check "
        "BRIDGE_SKILLS_DIR / the skills/ tree)."
    )

    executor = BridgeExecutor(
        engine=engine,
        collect_plan=collect_plan,
        strict=strict,
        hold_seconds=hold_seconds,
    )
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store if task_store is not None else InMemoryTaskStore(),
        agent_card=card,
    )

    routes = [
        *create_agent_card_routes(card),
        *create_jsonrpc_routes(handler, rpc_url="/"),
    ]

    @asynccontextmanager
    async def lifespan(app):
        yield
        await handler.aclose()

    app = Starlette(routes=routes, lifespan=lifespan)
    # Expose the executor so tests can inspect captured requests (parity with the mock's
    # app.state.mock_executor).
    app.state.executor = executor
    return app
