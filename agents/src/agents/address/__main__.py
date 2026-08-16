"""Runnable manual driver for the address agent (the durable ``Workflow`` graph).

Runs the graph for one Collect exchange against a locally-running mock Bridge::

    # terminal 1
    MOCK_BRIDGE_HOLD_SECONDS=2 uv run python -m agents.mock_bridge
    # terminal 2
    uv run python -m agents.address

The graph is deterministic today (code gate + code presenter), so no model call is
made — no credentials are required for the default run. The mock->real swap is
transparent to the agent: only the Bridge Agent Card URL changes
(``BRIDGE_CARD_URL`` / ``BRIDGE_BASE_URL``). Drop an ``LlmAgent`` presenter into the
graph's present node for a natural-language summary (see ``graph.py``).
"""

import asyncio

from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .config import APP_NAME, PARTY
from .graph import build_address_app
from .satisfaction import TERMINAL_TURN_STATE_KEY


async def _main() -> None:
    session_service = InMemorySessionService()
    runner = Runner(
        app=build_address_app(),
        session_service=session_service,
        artifact_service=InMemoryArtifactService(),
    )
    session_id = "manual"
    await session_service.create_session(app_name=APP_NAME, user_id=PARTY, session_id=session_id)
    new_message = types.Content(role="user", parts=[types.Part(text="collect the address proof")])
    async for _ in runner.run_async(user_id=PARTY, session_id=session_id, new_message=new_message):
        pass
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=PARTY, session_id=session_id
    )
    await runner.close()
    print(session.state.get(TERMINAL_TURN_STATE_KEY))


if __name__ == "__main__":
    asyncio.run(_main())
