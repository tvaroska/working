"""Local exchange store adapter (M1.2).

In-memory exchange store for the local development environment, implementing the
ADR-0003 view-by-default semantics. Satisfies the ``ExchangeStoreSeam`` protocol.

An exchange is a *view over its tasks* by default (see
``bridge.aggregate.build_exchange_view``); a stored record exists ONLY once the
exchange has been materialized because it holds exchange-only state. So:

- ``get`` returns ``None`` for an unmaterialized exchange (the caller derives the
  view over tasks instead).
- ``materialize`` is **one-way** and idempotent: the first call creates and stores
  the record; a later call returns the existing record without clobbering its
  exchange-only state, and never mints a new ``context_id``.

Backing is an in-memory ``dict`` keyed by ``context_id`` (this is the *local*
adapter; the GCP relational adapter — which needs a deterministic sort key per
lessons-learned A5 — lands in Sprint 2).
"""

from bridge.aggregate import ExchangeRecord

__all__ = ["LocalExchangeStore"]


class LocalExchangeStore:
    """Local (in-memory) exchange store adapter (ADR-0003 view-by-default)."""

    def __init__(self) -> None:
        self._records: dict[str, ExchangeRecord] = {}

    async def get(self, context_id: str) -> ExchangeRecord | None:
        """Return the materialized record for ``context_id``, or ``None``.

        ``None`` means the exchange has not been materialized — the caller uses the
        derived view over tasks (ADR-0003).
        """
        return self._records.get(context_id)

    async def save(self, record: ExchangeRecord) -> None:
        """Upsert a materialized record, keyed by ``record.context_id``."""
        self._records[record.context_id] = record

    async def materialize(self, context_id: str, **kwargs) -> ExchangeRecord:
        """Materialize an exchange — one-way and idempotent (ADR-0003).

        First call creates and stores a record; if already materialized, returns the
        existing record unchanged (no clobber of exchange-only state). Never mints a
        new id — the record's ``context_id`` is the caller's ``context_id``.
        """
        existing = self._records.get(context_id)
        if existing is not None:
            return existing
        record = ExchangeRecord(context_id=context_id, materialized=True, state=dict(kwargs))
        self._records[context_id] = record
        return record
