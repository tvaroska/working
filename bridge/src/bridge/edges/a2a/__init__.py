"""A2A inbound edge (M1.8) — canonical ``a2a-sdk`` JSON-RPC server.

The C2 port-map target ``bridge.edges.a2a.app:create_app`` assembles the real
Bridge's inbound edge: a dynamic Agent Card from the skill registry (M1.3) and the
canonical JSON-RPC surface (``message/send``/``stream``, ``tasks/get``/``list``/
``cancel``/``resubscribe``) inherited from ``DefaultRequestHandler``. The edge runs a
real, core-computed collect round (M1.6 disposition → M1.4 ledger over M1.2 tasks) and
emits a contract-faithful ``ExchangeTurn``, so the mock→real swap (M1.13) is a
card-URL change only.
"""

from .app import build_agent_card, create_app

__all__ = ["build_agent_card", "create_app"]
