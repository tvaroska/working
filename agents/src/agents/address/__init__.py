"""Address verification service agent (Phase 1 demo).

The agent is a durable ``Workflow`` graph (ADR-0010): a ``RemoteA2aAgent`` collect
node -> a deterministic Sense-B gate -> a present node, on one shared, resumable
session. The module-level :data:`app` (a resumable ``App``) is the ``adk web`` /
deploy entry point; :data:`root_agent` is the bare graph for tooling that wants one.

The interim ``AgentTool`` wiring (``build_address_agent`` + ``BridgeAgentTool``) was
retired here once the graph landed; it lives on in git history.
"""

from .config import APP_NAME, PARTY, SKILL
from .graph import app, build_address_app, build_address_graph, root_agent
from .satisfaction import (
    COLLECTION_STATUS_STATE_KEY,
    SatisfactionResult,
    check_completeness,
    is_satisfied,
)

__all__ = [
    "app",
    "root_agent",
    "build_address_app",
    "build_address_graph",
    "PARTY",
    "SKILL",
    "APP_NAME",
    "is_satisfied",
    "SatisfactionResult",
    "check_completeness",
    "COLLECTION_STATUS_STATE_KEY",
]
