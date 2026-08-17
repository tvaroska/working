"""Tests for the classified ledger projection (M1.4).

Pure unit tests (no fixtures, no async — direct construction). Build test tasks with
``create_leg_task`` (from ``aggregate``) then ``stamp_ledger_entry``; build
``LedgerEntry`` objects **inline** (they're ``contract`` models — do not read
``wiki/evals/...`` and do not import ``agents``).
"""

from contract import CollectionStatus, Disposition, ExtractedFields, Extraction, LedgerEntry

from bridge.aggregate import create_leg_task, ordinal_of
from bridge.ledger import build_exchange_turn, ledger_entry_of, stamp_ledger_entry


def test_round_trip():
    """stamp_ledger_entry then ledger_entry_of returns an equal LedgerEntry (D2)."""
    task = create_leg_task(context_id="ctx-1", ordinal=0, task_id="task-1")
    entry = LedgerEntry(
        id="doc-1",
        doctype="gov-id",
        disposition=Disposition.ACCEPTED,
        extraction=Extraction(fields=ExtractedFields(doctype="gov-id")),
    )

    stamp_ledger_entry(task, entry)
    recovered = ledger_entry_of(task)

    assert recovered is not None
    assert recovered.model_dump() == entry.model_dump()
    # Verify the JSON string coexists with the bridge_ordinal key
    assert ordinal_of(task) == 0


def test_ledger_entry_of_none_for_unstamped():
    """ledger_entry_of → None for a task with no stamped entry."""
    task = create_leg_task(context_id="ctx-1", ordinal=0, task_id="task-1")
    assert ledger_entry_of(task) is None


def test_deterministic_order():
    """Deterministic order (A5): shuffled input yields ordinal-ordered ledger.

    Three tasks with ordinals 0/1/2, fed in shuffled input order (task_ids chosen so
    their lexical sort contradicts the ordinal order), should result in ordinal order
    (0,1,2) in the ledger, independent of input order and task.id.
    """
    context_id = "ctx-1"
    # Ordinal 0 → task_id "t-z", ordinal 1 → "t-m", ordinal 2 → "t-a"
    # (lexical sort: t-a < t-m < t-z, contradicts ordinal order)
    task0 = create_leg_task(context_id=context_id, ordinal=0, task_id="t-z")
    task1 = create_leg_task(context_id=context_id, ordinal=1, task_id="t-m")
    task2 = create_leg_task(context_id=context_id, ordinal=2, task_id="t-a")

    entry0 = LedgerEntry(
        id="doc-0",
        doctype="gov-id",
        disposition=Disposition.ACCEPTED,
        extraction=Extraction(fields=ExtractedFields(doctype="gov-id")),
    )
    entry1 = LedgerEntry(
        id="doc-1",
        doctype="utility-bill",
        issuer="power-co",
        disposition=Disposition.ACCEPTED,
        extraction=Extraction(fields=ExtractedFields(doctype="utility-bill", issuer="power-co")),
    )
    entry2 = LedgerEntry(
        id="doc-2",
        doctype="utility-bill",
        issuer="water-co",
        disposition=Disposition.PENDING,
        extraction=Extraction(fields=ExtractedFields(doctype="utility-bill", issuer="water-co")),
    )

    stamp_ledger_entry(task0, entry0)
    stamp_ledger_entry(task1, entry1)
    stamp_ledger_entry(task2, entry2)

    # Feed in shuffled order (2, 0, 1)
    shuffled = [task2, task0, task1]
    turn = build_exchange_turn(context_id, shuffled)

    # Should be ordinal-ordered (0, 1, 2)
    assert len(turn.status.ledger) == 3
    assert turn.status.ledger[0].id == "doc-0"
    assert turn.status.ledger[1].id == "doc-1"
    assert turn.status.ledger[2].id == "doc-2"


def test_context_filtering():
    """Context filtering: tasks from a different context_id are excluded."""
    ctx1_task = create_leg_task(context_id="ctx-1", ordinal=0, task_id="task-1")
    ctx2_task = create_leg_task(context_id="ctx-2", ordinal=0, task_id="task-2")

    entry1 = LedgerEntry(
        id="doc-1",
        doctype="gov-id",
        disposition=Disposition.ACCEPTED,
        extraction=Extraction(fields=ExtractedFields(doctype="gov-id")),
    )
    entry2 = LedgerEntry(
        id="doc-2",
        doctype="utility-bill",
        issuer="power-co",
        disposition=Disposition.ACCEPTED,
        extraction=Extraction(fields=ExtractedFields(doctype="utility-bill", issuer="power-co")),
    )

    stamp_ledger_entry(ctx1_task, entry1)
    stamp_ledger_entry(ctx2_task, entry2)

    # Build turn for ctx-1 with both tasks
    turn = build_exchange_turn("ctx-1", [ctx1_task, ctx2_task])

    # Should contain only the ctx-1 entry
    assert len(turn.status.ledger) == 1
    assert turn.status.ledger[0].id == "doc-1"


def test_skip_unstamped():
    """Skip-unstamped: mix of stamped + unstamped tasks yields only stamped entries."""
    ctx = "ctx-1"
    task0 = create_leg_task(context_id=ctx, ordinal=0, task_id="task-0")
    task1 = create_leg_task(context_id=ctx, ordinal=1, task_id="task-1")
    task2 = create_leg_task(context_id=ctx, ordinal=2, task_id="task-2")

    entry0 = LedgerEntry(
        id="doc-0",
        doctype="gov-id",
        disposition=Disposition.ACCEPTED,
        extraction=Extraction(fields=ExtractedFields(doctype="gov-id")),
    )
    entry2 = LedgerEntry(
        id="doc-2",
        doctype="utility-bill",
        issuer="power-co",
        disposition=Disposition.ACCEPTED,
        extraction=Extraction(fields=ExtractedFields(doctype="utility-bill", issuer="power-co")),
    )

    stamp_ledger_entry(task0, entry0)
    # task1 left unstamped (in-flight leg)
    stamp_ledger_entry(task2, entry2)

    turn = build_exchange_turn(ctx, [task0, task1, task2])

    # Should contain only the stamped entries (0, 2), in ordinal order
    assert len(turn.status.ledger) == 2
    assert turn.status.ledger[0].id == "doc-0"
    assert turn.status.ledger[1].id == "doc-2"


def test_container_passthrough():
    """Container passthrough (D3): outstanding/terminal values unchanged."""
    ctx = "ctx-1"
    task = create_leg_task(context_id=ctx, ordinal=0, task_id="task-1")
    entry = LedgerEntry(
        id="doc-1",
        doctype="gov-id",
        disposition=Disposition.ACCEPTED,
        extraction=Extraction(fields=ExtractedFields(doctype="gov-id")),
    )
    stamp_ledger_entry(task, entry)

    # Test with outstanding and terminal
    turn = build_exchange_turn(
        ctx,
        [task],
        outstanding=["gov-id", "utility-bill"],
        terminal=True,
    )
    assert turn.status.outstanding == ["gov-id", "utility-bill"]
    assert turn.status.terminal is True

    # Test defaults
    turn_default = build_exchange_turn(ctx, [task])
    assert turn_default.status.outstanding == []
    assert turn_default.status.terminal is False


def test_empty_exchange():
    """Empty exchange: no tasks → ledger == [], CollectionStatus/ExchangeTurn valid."""
    ctx = "ctx-empty"
    turn = build_exchange_turn(ctx, [])

    assert turn.context_id == ctx
    assert turn.status.ledger == []
    assert turn.status.outstanding == []
    assert turn.status.terminal is False


def test_shape_parity():
    """Shape parity: assembled ExchangeTurn validates and has the mock's key set."""
    ctx = "ctx-1"
    task = create_leg_task(context_id=ctx, ordinal=0, task_id="task-1")
    entry = LedgerEntry(
        id="doc-1",
        doctype="gov-id",
        disposition=Disposition.ACCEPTED,
        extraction=Extraction(fields=ExtractedFields(doctype="gov-id")),
    )
    stamp_ledger_entry(task, entry)

    turn = build_exchange_turn(
        ctx,
        [task],
        outstanding=["utility-bill"],
        terminal=False,
    )

    # Should validate as contract.ExchangeTurn (already does by construction)
    assert turn.context_id == ctx
    assert isinstance(turn.status, CollectionStatus)

    # model_dump(mode="json") should have the mock's key set
    dumped = turn.model_dump(mode="json")
    assert "context_id" in dumped
    assert "status" in dumped
    assert "ledger" in dumped["status"]
    assert "outstanding" in dumped["status"]
    assert "terminal" in dumped["status"]
    # Verify ledger entries have the expected structure
    assert len(dumped["status"]["ledger"]) == 1
    assert dumped["status"]["ledger"][0]["id"] == "doc-1"
