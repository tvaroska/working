"""Aggregate model unit tests (M1.2).

Covers the exchange/task/session/party bindings and the deterministic
exchange-as-view read path (ADR-0003, lessons-learned A5). No seam fixture — these
are pure unit tests over ``bridge.aggregate``.
"""

from bridge.aggregate import (
    ORDINAL_KEY,
    ExchangeRecord,
    build_exchange_view,
    create_leg_task,
    mint_context_id,
    next_ordinal,
    ordinal_of,
    party_scope,
    session_id_for_task,
)


def test_mint_context_id_is_unique_and_prefixed():
    """Fresh id per call, ``ctx-`` prefixed (D2)."""
    a = mint_context_id()
    b = mint_context_id()
    assert a != b
    assert a.startswith("ctx-") and b.startswith("ctx-")


def test_session_id_binds_1_to_1_with_task():
    """session_id == task_id — the explicit 1:1 binding (D5)."""
    assert session_id_for_task("task-42") == "task-42"


def test_party_scope_falls_back_to_context():
    """Party is a plain reference string; falls back to the context (D6)."""
    ctx = mint_context_id()
    assert party_scope(None, ctx) == ctx
    assert party_scope("", ctx) == ctx
    assert party_scope("jordan-lee", ctx) == "jordan-lee"


def test_ordinal_stamp_round_trips_as_int():
    """The ordinal is stamped on the proto Struct and read back as int (A5)."""
    task = create_leg_task(context_id="ctx-1", ordinal=2, task_id="t2")
    assert ORDINAL_KEY in task.metadata
    assert ordinal_of(task) == 2


def test_next_ordinal_counts_existing():
    """next_ordinal returns the 0-based position for the next task in a context."""
    existing = [
        create_leg_task(context_id="ctx-1", ordinal=0, task_id="t0"),
        create_leg_task(context_id="ctx-1", ordinal=1, task_id="t1"),
    ]
    assert next_ordinal(existing) == 2
    assert next_ordinal([]) == 0


def test_build_exchange_view_orders_by_ordinal_not_input_or_id():
    """The headline A5 test: deterministic ordinal order, shuffled input, id-agnostic.

    Task ids are chosen so ``task.id`` sort order is the REVERSE of ordinal order,
    proving the view sorts by the durable ordinal, not by id or insertion order.
    """
    ctx = "ctx-view"
    # id "aaa" gets ordinal 2, "zzz" gets ordinal 0 → id-sort would invert ordinals.
    t0 = create_leg_task(context_id=ctx, ordinal=0, task_id="zzz")
    t1 = create_leg_task(context_id=ctx, ordinal=1, task_id="mmm")
    t2 = create_leg_task(context_id=ctx, ordinal=2, task_id="aaa")

    shuffled = [t2, t0, t1]
    view = build_exchange_view(ctx, shuffled)

    assert [ordinal_of(t) for t in view.tasks] == [0, 1, 2]
    assert [t.id for t in view.tasks] == ["zzz", "mmm", "aaa"]
    assert view.context_id == ctx


def test_build_exchange_view_filters_other_contexts():
    """Tasks from a different context are excluded from the view (D3)."""
    mine = create_leg_task(context_id="ctx-a", ordinal=0, task_id="a0")
    other = create_leg_task(context_id="ctx-b", ordinal=0, task_id="b0")

    view = build_exchange_view("ctx-a", [other, mine])

    assert [t.id for t in view.tasks] == ["a0"]


def test_exchange_record_defaults():
    """ExchangeRecord is minimal: identity + materialized flag + open state (D8)."""
    rec = ExchangeRecord(context_id="ctx-x")
    assert rec.context_id == "ctx-x"
    assert rec.materialized is True
    assert rec.state == {}
