"""The transport-agnostic ``BridgeClient`` port and its ``a2a-sdk`` adapter.

The agent core depends only on the :class:`BridgeClient` port; the
:class:`A2ABridgeClient` adapter implements it over the canonical A2A surface.
This package imports only ``contract`` + stdlib + ``a2a-sdk`` + ``httpx`` and must
never import anything under ``agents.*`` (the client seam is agent-agnostic).
"""

from .a2a_client import A2ABridgeClient, request_to_message, task_to_exchange_turn
from .port import (
    BridgeClient,
    BridgeClientError,
    BridgeParkedError,
    BridgeTimeoutError,
)
from .remote_consumer import build_bridge_remote_agent

__all__ = [
    "BridgeClient",
    "BridgeClientError",
    "BridgeParkedError",
    "BridgeTimeoutError",
    "A2ABridgeClient",
    "build_bridge_remote_agent",
    "request_to_message",
    "task_to_exchange_turn",
]
