"""Mock Bridge application assembly — Agent Card + Starlette app.

Assembles an a2a-sdk server that serves a minimal Agent Card advertising an
address-proof skill and a JSON-RPC interface, and handles message/send requests
by running the mock executor.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from a2a.utils.constants import TransportProtocol
from starlette.applications import Starlette

from .executor import MockBridgeExecutor
from .fixtures import load_gov_id_clean_entry


def build_agent_card(base_url: str) -> AgentCard:
    """Build the Agent Card advertising the mock Bridge's capabilities.

    Args:
        base_url: The externally reachable base URL (e.g., http://127.0.0.1:8080).

    Returns:
        An AgentCard with a JSONRPC interface, address-proof skill, and
        streaming=False.

    Note:
        The card's interface url must match the RPC endpoint's actual URL
        (base_url + "/") so ClientFactory.create can find it.
    """
    return AgentCard(
        name="Mock Document Bridge",
        description="Mock A2A Document Bridge for contract validation (M0 tracer bullet)",
        version="0.0.0",
        supported_interfaces=[
            AgentInterface(
                url=f"{base_url}/",
                protocol_binding=TransportProtocol.JSONRPC.value,
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(
            streaming=False,
            push_notifications=False,
        ),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[
            AgentSkill(
                id="address-proof",
                name="Address proof collection",
                description="Collect and verify address proof documents (gov-id or utility bills)",
                tags=["address"],
                input_modes=["application/json"],
                output_modes=["application/json"],
            )
        ],
    )


def create_app(
    base_url: str = "http://127.0.0.1:8080",
    *,
    hold_seconds: float = 10.0,
    evals_path: Path | None = None,
) -> Starlette:
    """Create the mock Bridge Starlette application.

    Args:
        base_url: The externally reachable base URL (baked into the Agent Card).
        hold_seconds: How long the executor holds in WORKING state before completing.
        evals_path: Optional explicit path to expected.json (for testing).

    Returns:
        A Starlette app serving the Agent Card at /.well-known/agent-card.json
        and JSON-RPC at /.

    Note:
        The handler's aclose() is wired into Starlette's lifespan so the
        background execute() task drains cleanly on server stop.
    """
    entry = load_gov_id_clean_entry(evals_path)
    card = build_agent_card(base_url)
    executor = MockBridgeExecutor(entry, hold_seconds=hold_seconds)
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )

    routes = [
        *create_agent_card_routes(card),
        *create_jsonrpc_routes(handler, rpc_url="/"),
    ]

    @asynccontextmanager
    async def lifespan(app):
        # Startup
        yield
        # Shutdown
        await handler.aclose()

    app = Starlette(routes=routes, lifespan=lifespan)
    return app
