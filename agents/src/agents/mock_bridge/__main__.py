"""Mock Bridge runnable entrypoint.

Start the mock server with:
    uv run python -m agents.mock_bridge

Configuration via environment variables:
    MOCK_BRIDGE_HOST: Host to bind (default: 127.0.0.1)
    MOCK_BRIDGE_PORT: Port to bind (default: 8080)
    MOCK_BRIDGE_HOLD_SECONDS: How long to hold in WORKING state (default: 10.0)
    MOCK_BRIDGE_PARK: If "1"/"true", park at INPUT_REQUIRED and resume (adr-0009)
"""

import os

import uvicorn

from .app import create_app


def main():
    """Run the mock Bridge server with config from environment."""
    host = os.environ.get("MOCK_BRIDGE_HOST", "127.0.0.1")
    port = int(os.environ.get("MOCK_BRIDGE_PORT", "8080"))
    hold_seconds = float(os.environ.get("MOCK_BRIDGE_HOLD_SECONDS", "10.0"))
    park = os.environ.get("MOCK_BRIDGE_PARK", "").lower() in ("1", "true", "yes")

    base_url = f"http://{host}:{port}"
    app = create_app(base_url, hold_seconds=hold_seconds, park=park)

    print(f"Starting Mock Document Bridge at {base_url}")
    print(f"  Agent Card: {base_url}/.well-known/agent-card.json")
    print(f"  JSON-RPC: {base_url}/")
    print(f"  Hold duration: {hold_seconds}s")
    print(f"  Park mode: {park}")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
