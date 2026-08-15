"""The native ``RemoteA2aAgent`` Bridge consumer and pure A2A wire helpers.

Our agents consume the Bridge through ADK's platform-native ``RemoteA2aAgent``
(adr-0009): the mock->real and local->GCP swap is a **different Agent Card URL**,
not different agent code. The M0 hand-rolled ``BridgeClient`` port + poll loop was
removed once the wire contract was validated (see adr-0009 amendment).

This package imports only ``contract`` + stdlib + ``a2a-sdk`` + ``httpx`` +
``google-adk`` and must never import anything under ``agents.*``.
"""

from .remote_consumer import build_bridge_remote_agent
from .wire import (
    BridgeWireError,
    request_to_message,
    task_to_exchange_turn,
)

__all__ = [
    "build_bridge_remote_agent",
    "BridgeWireError",
    "request_to_message",
    "task_to_exchange_turn",
]
