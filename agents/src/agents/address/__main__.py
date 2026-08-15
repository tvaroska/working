"""Runnable manual driver for the address agent (feeds M0.7).

Runs the real ``LlmAgent`` (real model from ``ADDRESS_AGENT_MODEL``) for one turn
against a locally-running mock Bridge, printing the rendered ``gov-id-clean``
summary::

    # terminal 1
    MOCK_BRIDGE_HOLD_SECONDS=2 uv run python -m agents.mock_bridge
    # terminal 2 (needs GOOGLE_API_KEY / Vertex config for the real model)
    uv run python -m agents.address

The port swap is transparent to the agent — only the injected client changes.
"""

import asyncio
import os

from bridge_client import A2ABridgeClient

from .agent import build_address_agent, run_once


async def _main() -> None:
    base_url = os.environ.get("BRIDGE_BASE_URL", "http://127.0.0.1:8080")
    client = A2ABridgeClient(base_url)
    try:
        agent = build_address_agent(client)
        summary = await run_once(agent)
        print(summary)
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(_main())
