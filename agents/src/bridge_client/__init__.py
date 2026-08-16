"""The native ``RemoteA2aAgent`` Bridge consumer and pure A2A wire helpers.

Our agents consume the Bridge through ADK's platform-native ``RemoteA2aAgent``
(adr-0009): the mock->real and local->GCP swap is a **different Agent Card URL**,
not different agent code.

This package imports only ``contract`` + stdlib + ``a2a-sdk`` + ``httpx`` +
``google-adk`` and must never import anything under ``agents.*``.
"""

from .remote_consumer import (
    EXCHANGE_CONTEXT_STATE_KEY,
    build_bridge_remote_agent,
    build_collect_request_interceptor,
)
from .wire import (
    BridgeWireError,
    extract_exchange_turn,
    latest_exchange_turn,
    request_to_message,
    task_to_exchange_turn,
)

__all__ = [
    "EXCHANGE_CONTEXT_STATE_KEY",
    "build_bridge_remote_agent",
    "build_collect_request_interceptor",
    "BridgeWireError",
    "extract_exchange_turn",
    "latest_exchange_turn",
    "request_to_message",
    "task_to_exchange_turn",
]
