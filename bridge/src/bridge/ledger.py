"""Classified ledger projection over exchange tasks (M1.4).

The Bridge-core classified ledger is a **view, not a record** (ADR-0003): it is a
**pure fold** over an exchange's tasks (one doc per task) that produces
``list[LedgerEntry]``, deterministically ordered by the M1.2 ``bridge_ordinal`` sort
key. Nothing is stored; the projection is recomputed from tasks on every read.

Three tiers:
- **Carry convention** (:func:`stamp_ledger_entry`, :func:`ledger_entry_of`): how one
  ``LedgerEntry`` rides on one A2A ``Task`` (durably, backend-independently — parity
  with the M1.2 ordinal).
- **Deterministic fold** (:func:`project_ledger`): ordered by ``ordinal_of``,
  filtered to the context (reuses :func:`build_exchange_view`).
- **Container assembly** (:func:`project_collection_status`, :func:`build_exchange_turn`):
  producing ``CollectionStatus`` / ``ExchangeTurn`` — with ``outstanding`` and
  ``terminal`` as **caller-supplied inputs** (they are *not* computed here).

**Ownership split (docs/lessons-learned.md A5, wiki/bridge-collect.md sense-A/B):**
M1.4 carries ``outstanding`` and ``terminal`` as passthrough fields. The sense-A/sense-B
split makes ``outstanding`` an **advisory** the skill rule proposes (M1.6/M1.9) and
``terminal`` an outcome of disposition + the app's ``done`` — a model/projection
**may never mint completeness**. M1.4 depends only on M1.2 and must be callable
*before* M1.6/M1.9 exist, so the projection **carries** these fields through rather
than deciding them. M1.6 supplies per-doc disposition (already baked into each entry),
M1.9 supplies the advisory ``outstanding``, and the app owns the final ``done``.

Import discipline: imports ``contract`` + ``a2a.types`` + ``bridge.aggregate`` only.
Never imports ``agents``, ``seams``, or ``adapters``. Keep it out of
``bridge/__init__.py`` (preserve cheap ``import bridge`` + the no-agents-guard
clarity, same rule M1.2 followed for ``aggregate``).
"""

from __future__ import annotations

from collections.abc import Iterable

from a2a.types import Task
from contract import CollectionStatus, ExchangeTurn, LedgerEntry

from bridge.aggregate import ExchangeView, build_exchange_view

__all__ = [
    "LEDGER_ENTRY_KEY",
    "build_exchange_turn",
    "ledger_entry_of",
    "project_collection_status",
    "project_ledger",
    "stamp_ledger_entry",
]

#: Metadata key holding the durable per-task classified entry (M1.4 D2).
LEDGER_ENTRY_KEY = "bridge_ledger_entry"


def stamp_ledger_entry(task: Task, entry: LedgerEntry) -> None:
    """Stamp a classified ledger entry onto ``task.metadata`` (D2).

    Stores the entry as a JSON *string* scalar under :data:`LEDGER_ENTRY_KEY`. This
    is the durable, backend-independent carry convention — the entry survives the
    ``DatabaseTaskStore`` restart and needs no separate store, honoring "view, not
    record" (docs/lessons-learned A5).

    A JSON *string* scalar avoids the fragile protobuf-``Struct`` nested-dict path
    (verified working) and coexists with the M1.2 numeric ``bridge_ordinal`` key in
    the same Struct. Read back via :func:`ledger_entry_of`.

    Args:
        task: The A2A task to stamp.
        entry: The classified ledger entry to attach.
    """
    task.metadata[LEDGER_ENTRY_KEY] = entry.model_dump_json()


def ledger_entry_of(task: Task) -> LedgerEntry | None:
    """Read the stamped classified entry off a task, if any (D2).

    Returns ``None`` for a task with no stamped entry (e.g. an in-flight leg before
    disposition ran). Round-trips the JSON string stamped by
    :func:`stamp_ledger_entry`.

    Args:
        task: The A2A task to read from.

    Returns:
        The classified entry if stamped, else ``None``.
    """
    if LEDGER_ENTRY_KEY in task.metadata:
        return LedgerEntry.model_validate_json(task.metadata[LEDGER_ENTRY_KEY])
    return None


def project_ledger(view: ExchangeView) -> list[LedgerEntry]:
    """Project the classified ledger from an exchange view (D4).

    Folds over ``view.tasks`` (already ordinal-sorted by :func:`build_exchange_view`)
    and collects :func:`ledger_entry_of` for each task that **has** an entry (skip
    ``None`` — in-flight legs without a disposition yet).

    Because ``view.tasks`` is pre-sorted by ``ordinal_of``, the ledger order is
    deterministic regardless of the order tasks were fetched from a relational/GCP
    store — this is the concrete A5 answer for the *ledger* (M1.2 answered it for the
    *view*).

    Args:
        view: The exchange view (filtered + ordinal-sorted).

    Returns:
        A list of classified ledger entries, in ordinal order.
    """
    ledger = []
    for task in view.tasks:
        entry = ledger_entry_of(task)
        if entry is not None:
            ledger.append(entry)
    return ledger


def project_collection_status(
    view: ExchangeView,
    *,
    outstanding: Iterable[str] = (),
    terminal: bool = False,
) -> CollectionStatus:
    """Assemble a ``CollectionStatus`` from an exchange view (D3).

    ``outstanding`` and ``terminal`` are **caller-supplied inputs**, not computed by
    M1.4. The sense-A/sense-B split (ADR-0003, wiki/bridge-collect.md) makes
    ``outstanding`` an **advisory** the skill rule proposes (M1.9) and ``terminal``
    an outcome of disposition + the app's ``done`` — a model/projection **may never
    mint completeness** (docs/lessons-learned A3).

    Args:
        view: The exchange view (filtered + ordinal-sorted).
        outstanding: The advisory list of outstanding document references (M1.9).
        terminal: Whether the exchange is terminal (M1.6 + app-owned ``done``).

    Returns:
        The assembled collection status.
    """
    return CollectionStatus(
        ledger=project_ledger(view),
        outstanding=list(outstanding),
        terminal=terminal,
    )


def build_exchange_turn(
    context_id: str,
    tasks: Iterable[Task],
    *,
    outstanding: Iterable[str] = (),
    terminal: bool = False,
) -> ExchangeTurn:
    """Build an ``ExchangeTurn`` from raw tasks (D5).

    Convenience wrapper that builds the view internally via
    :func:`build_exchange_view` and wraps the status. Named for parity with the
    mock's ``build_exchange_turn`` output shape (``mock_bridge/fixtures.py``), so
    M1.13's mock→real swap compares like-for-like.

    Args:
        context_id: The exchange identity (A2A context_id).
        tasks: The candidate tasks (will be filtered to ``context_id``).
        outstanding: The advisory list of outstanding document references (M1.9).
        terminal: Whether the exchange is terminal (M1.6 + app-owned ``done``).

    Returns:
        The assembled exchange turn.
    """
    view = build_exchange_view(context_id, tasks)
    status = project_collection_status(view, outstanding=outstanding, terminal=terminal)
    return ExchangeTurn(context_id=context_id, status=status)
