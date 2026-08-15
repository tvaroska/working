"""Runnable manual driver for the address agent (feeds M0.7).

Runs the real ``LlmAgent`` (real model from ``ADDRESS_AGENT_MODEL``, default
``gemini-3.7-flash``) for one turn against a locally-running mock Bridge::

    # terminal 1
    MOCK_BRIDGE_HOLD_SECONDS=2 uv run python -m agents.mock_bridge
    # terminal 2 (needs Vertex AI application-default credentials)
    uv run python -m agents.address

Vertex AI (global region) is the default runtime: this driver sets
``GOOGLE_GENAI_USE_VERTEXAI=TRUE`` and ``GOOGLE_CLOUD_LOCATION=global`` when they
are unset (explicit env still wins), and relies on ``GOOGLE_CLOUD_PROJECT`` +
application-default credentials. The mock->real swap is transparent to the agent —
only the Bridge Agent Card URL changes (``BRIDGE_CARD_URL`` / ``BRIDGE_BASE_URL``).
"""

import asyncio
import os

from .agent import build_address_agent, run_once


def _apply_vertex_defaults() -> None:
    """Default to Vertex AI in the global region unless the env overrides it."""
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")


async def _main() -> None:
    _apply_vertex_defaults()
    agent = build_address_agent()
    summary = await run_once(agent)
    print(summary)


if __name__ == "__main__":
    asyncio.run(_main())
