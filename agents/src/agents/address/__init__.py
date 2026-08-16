"""Address verification service agent (Phase 1 demo).

The agent is a durable ``Workflow`` graph (ADR-0010): a ``RemoteA2aAgent`` collect
node -> a deterministic Sense-B gate -> a present node, on one shared, resumable
session. The module-level :data:`app` (a resumable ``App``) is the ``adk web`` /
deploy entry point; :data:`root_agent` is the bare graph for tooling that wants one.
"""

from .agent import app, root_agent
from .config import APP_NAME, PARTY, SKILL
from .graph import build_address_app
from .satisfaction import (
    TERMINAL_TURN_STATE_KEY,
    SatisfactionResult,
    is_satisfied,
)

__all__ = [
    "app",
    "root_agent",
    "build_address_app",
    "PARTY",
    "SKILL",
    "APP_NAME",
    "is_satisfied",
    "SatisfactionResult",
    "TERMINAL_TURN_STATE_KEY",
]
