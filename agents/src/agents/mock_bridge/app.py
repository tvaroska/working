"""Mock Bridge application assembly — Agent Card + Starlette app.

Assembles an a2a-sdk server that serves a minimal Agent Card advertising an
address-proof skill and a JSON-RPC interface, and handles message/send requests
by running the mock executor.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from a2a.utils.constants import TransportProtocol
from starlette.applications import Starlette

from .executor import MockBridgeExecutor
from .scenarios import GOV_ID_INSTANT, SCENARIOS, MockScenario


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
            # streaming=True so the native RemoteA2aAgent consumer can receive
            # progress TaskStatusUpdateEvents (adr-0009).
            streaming=True,
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
    scenario: MockScenario | str | None = None,
    hold_seconds: float = 10.0,
    park: bool = False,
    evals_path: Path | None = None,
    task_store: TaskStore | None = None,
) -> Starlette:
    """Create the mock Bridge Starlette application.

    Args:
        base_url: The externally reachable base URL (baked into the Agent Card).
        scenario: The multi-turn scenario to script. None -> GOV_ID_INSTANT;
            str -> SCENARIOS[str]; MockScenario -> as-is.
        hold_seconds: How long the executor holds in WORKING state before completing.
        park: If True, the first turn parks at INPUT_REQUIRED and a resume turn
            completes it (the adr-0009 pause/resume tracer).
        evals_path: Optional explicit path to expected.json (for testing).
        task_store: Optional A2A task store. Defaults to ``InMemoryTaskStore``;
            pass a ``DatabaseTaskStore`` to make the mock's task state durable
            (the Task-store seam's DEFAULT swap — S1-6/ADR-0010). The swap is a
            no-op for the consumer: the same JSON-RPC surface, a different store.

    Returns:
        A Starlette app serving the Agent Card at /.well-known/agent-card.json
        and JSON-RPC at /.

    Note:
        The handler's aclose() is wired into Starlette's lifespan so the
        background execute() task drains cleanly on server stop.
    """
    # Resolve scenario
    if scenario is None:
        scenario = GOV_ID_INSTANT
    elif isinstance(scenario, str):
        if scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}")
        scenario = SCENARIOS[scenario]

    card = build_agent_card(base_url)
    executor = MockBridgeExecutor(
        scenario,
        evals_path=evals_path,
        hold_seconds=hold_seconds,
        park=park,
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
        # Startup
        yield
        # Shutdown
        await handler.aclose()

    app = Starlette(routes=routes, lifespan=lifespan)
    # Expose the executor so the seam suite can inspect captured requests
    # (e.g. the structured CollectRequest that arrived on message/send — S1-2).
    app.state.mock_executor = executor
    return app
