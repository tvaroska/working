"""Mock Document Bridge server (permanent contract double for testing)."""

from .app import build_agent_card, create_app
from .executor import MockBridgeExecutor
from .fixtures import build_exchange_turn, load_entry, load_gov_id_clean_entry
from .scenarios import (
    GOV_ID_INSTANT,
    REJECT_RESUBMIT,
    SCENARIOS,
    TWO_BILLS,
    MockScenario,
    ScenarioStep,
)

__all__ = [
    "build_agent_card",
    "build_exchange_turn",
    "create_app",
    "GOV_ID_INSTANT",
    "load_entry",
    "load_gov_id_clean_entry",
    "MockBridgeExecutor",
    "MockScenario",
    "REJECT_RESUBMIT",
    "SCENARIOS",
    "ScenarioStep",
    "TWO_BILLS",
]
