"""Shared configuration for the address service agent.

These constants define the demo's fixed identity (party/skill, no skills registry
in M0), the ADK app name, the default model, and the single mock->real / local->GCP
swap point (the Bridge Agent Card URL). They live here — not in the graph module —
so both the graph and the package entry points import them without a cycle.
"""

import os

PARTY = "jordan-lee"
SKILL = "address-proof"
APP_NAME = "address"
DEFAULT_MODEL = os.environ.get("ADDRESS_AGENT_MODEL", "gemini-3.7-flash")


def _default_card_url() -> str:
    """Resolve the Bridge Agent Card URL from the environment.

    ``BRIDGE_CARD_URL`` wins; otherwise it is derived from ``BRIDGE_BASE_URL``
    (default ``http://127.0.0.1:8080``) + the well-known agent-card path. This is
    the single swap point between mock/real and local/GCP — a no-op for the agent.
    """
    explicit = os.environ.get("BRIDGE_CARD_URL")
    if explicit:
        return explicit
    base = os.environ.get("BRIDGE_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    return f"{base}/.well-known/agent-card.json"
