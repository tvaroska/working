"""Shared helpers for reading A2A payloads out of ADK event streams.

The inbound extractor is now production code (``bridge_client.wire``); this module
re-exports it so existing tests keep a stable import path.
"""

from bridge_client.wire import extract_exchange_turn

__all__ = ["extract_exchange_turn"]
