"""LocalExchangeStore behavior tests (M1.2, ADR-0003 view-by-default).

Driven through the shared ``adapter`` fixture (seam="exchange_store"), so the same
assertions will run against the GCP relational adapter in Sprint 2. Verifies:
- get(unmaterialized) → None (the exchange is a view over tasks by default);
- materialize is one-way, idempotent, and never mints a new id;
- save/get round-trips a materialized record.
"""

import pytest

from bridge.aggregate import ExchangeRecord


@pytest.mark.seam("exchange_store")
@pytest.mark.anyio
async def test_get_unmaterialized_returns_none(adapter):
    """An unmaterialized exchange has no record — the caller uses the task view."""
    assert await adapter.get("ctx-unknown") is None


@pytest.mark.seam("exchange_store")
@pytest.mark.anyio
async def test_materialize_is_one_way_and_idempotent(adapter):
    """materialize keeps the same context_id and never clobbers on re-materialize."""
    ctx = "ctx-materialize"
    first = await adapter.materialize(ctx, program="address")
    assert first.context_id == ctx
    assert first.materialized is True
    assert first.state == {"program": "address"}

    # After materialize, get returns the stored record.
    assert await adapter.get(ctx) is first

    # Re-materialize is idempotent: same id, existing record returned, no clobber
    # of exchange-only state even with different init kwargs.
    second = await adapter.materialize(ctx, program="benefits")
    assert second is first
    assert second.context_id == ctx
    assert second.state == {"program": "address"}


@pytest.mark.seam("exchange_store")
@pytest.mark.anyio
async def test_save_then_get_round_trips(adapter):
    """save upserts a materialized record; get returns it by context_id."""
    rec = ExchangeRecord(context_id="ctx-save", state={"note": "hello"})
    await adapter.save(rec)

    got = await adapter.get("ctx-save")
    assert got is not None
    assert got.context_id == "ctx-save"
    assert got.state == {"note": "hello"}
