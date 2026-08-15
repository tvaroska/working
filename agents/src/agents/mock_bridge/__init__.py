"""Mock Document Bridge server (permanent contract double for testing)."""

from .app import build_agent_card, create_app
from .executor import MockBridgeExecutor
from .fixtures import build_exchange_turn, load_gov_id_clean_entry

__all__ = [
    "build_agent_card",
    "build_exchange_turn",
    "create_app",
    "load_gov_id_clean_entry",
    "MockBridgeExecutor",
]
