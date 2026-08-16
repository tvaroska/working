"""Exchange store seam: Bridge-invented (ADR-0003 view-by-default).

An exchange is the A2A context (1:1 with context_id). Phase-1 Address stays a
view over tasks (ADR-0003) — the store is present for parity/future materialization.
Identity is the A2A context_id, never a new ID. See wiki/bridge-seams.md.

CAVEAT: @runtime_checkable Protocols check method presence only, not signatures.
This is the desired behavior for M1.1 conformance smoke tests — real behavior and
signature validation are pinned by the shared suite in M1.2+. Keep every Protocol
method-only (no data attributes) or isinstance will raise/misbehave.

Invariants:
- ADR-0003: Exchange is a view over tasks by default; materialization is a one-way
  transition on first exchange-only state.
- lessons-learned.md A5: Deterministic ordering required for persistent adapters.
"""

from typing import Protocol, runtime_checkable

__all__ = ["ExchangeStoreSeam"]


@runtime_checkable
class ExchangeStoreSeam(Protocol):
    """Seam for exchange storage (view over tasks by default).

    Local adapter: LocalExchangeStore (bridge.adapters.local)
    GCP adapter: DatabaseExchangeStore (Sprint 2)

    Exchange = the A2A context (context_id is identity). Phase-1 Address is a
    view over tasks (ADR-0003); the store provides future materialization.

    Note: The concrete exchange record type is defined by M1.2; signatures use
    `object` here as a placeholder.
    """

    async def get(self, context_id: str) -> object | None:
        """Retrieve an exchange by context_id, or None if unmaterialized.

        None means the exchange has not been materialized yet; the caller should
        use the derived view over tasks (ADR-0003).
        """
        ...

    async def save(self, record: object) -> None:
        """Save or update an exchange record.

        # M1.2 defines the concrete exchange record type.
        """
        ...

    async def materialize(self, context_id: str, **kwargs) -> object:
        """Materialize an exchange (one-way transition on first exchange-only state).

        This is a one-way transition: once materialized, the exchange is a record,
        not a view. kwargs allow passing initial state.

        # M1.2 defines the concrete exchange record type and kwargs.
        """
        ...
