"""Aggregate model as Bridge-core code (M1.2).

Encodes the four-level aggregate model from ``wiki/bridge-aggregate-model.md`` and
the exchange-as-view-over-tasks read path (ADR-0003):

- **exchange** = the A2A context, 1:1 with ``context_id`` (minted at request time,
  never re-minted — not even on materialization). There is no separate exchange id.
- **task** = one leg's durable work, ≈ one ADK session, keyed 1:1
  (``session_id == task_id`` — see :func:`session_id_for_task`).
- **party** = a stable counterparty *reference string*, NOT an aggregate (no model,
  no store — see :func:`party_scope`).

Deterministic ordering (docs/lessons-learned **A5**): the A2A ``Task`` has no
timestamp and a relational/GCP task store returns rows unordered, so a durable,
backend-independent sort key is baked in from day one — a per-context ordinal
stamped into ``task.metadata["bridge_ordinal"]`` at creation. :func:`build_exchange_view`
sorts by that ordinal. Chronological order *beyond* this ordinal is not guaranteed
and needs no extra state.

Restore is platform-DEFAULT when a durable store is used (docs/lessons-learned
**A13**): this module carries the aggregate conventions; durability is proven by the
``Database*`` local variants (see ``bridge.adapters.local``).

Import discipline: this module imports ``contract`` + ``a2a`` only — never
``agents`` (guarded by ``tests/test_no_agents_import.py``) and never the seams or
adapters (the dependency direction is adapters → aggregate). Keep it out of
``bridge/__init__.py`` so ``import bridge`` stays cheap.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from uuid import uuid4

from a2a.types import Task, TaskState, TaskStatus
from pydantic import BaseModel, Field

__all__ = [
    "ORDINAL_KEY",
    "ExchangeRecord",
    "ExchangeView",
    "build_exchange_view",
    "create_leg_task",
    "mint_context_id",
    "next_ordinal",
    "ordinal_of",
    "party_scope",
    "session_id_for_task",
    "stamp_ordinal",
    "tasks_for_context",
]

#: Metadata key holding the durable per-context ordinal (A5 sort key).
ORDINAL_KEY = "bridge_ordinal"


def mint_context_id() -> str:
    """Mint a fresh exchange identity = the A2A ``context_id`` (D2, ADR-0003).

    Returns a new id per call. Materialization must *reuse* this id, never mint a
    new one — the exchange identity IS the ``context_id``.
    """
    return f"ctx-{uuid4().hex}"


def session_id_for_task(task_id: str) -> str:
    """Return the ADK session id bound 1:1 to ``task_id`` (D5).

    The task↔session binding is identity: ``session_id == task_id``. This helper
    makes the 1:1 convention explicit and greppable
    (``wiki/bridge-aggregate-model.md``: "one task is one runtime session, keyed
    one-to-one").
    """
    return task_id


def party_scope(party: str | None, context_id: str) -> str:
    """Return the counterparty reference for a leg (D6).

    Party is a plain stable reference string, not an aggregate — it rides on
    ``CollectRequest.party`` and falls back to the exchange ``context_id`` when
    none is supplied. Do not build a Party model/store
    (``wiki/bridge-aggregate-model.md``: "Party is not an aggregate").
    """
    return party or context_id


def next_ordinal(existing: Iterable[Task]) -> int:
    """Return the next 0-based ordinal for a context (count of existing tasks, A5)."""
    return sum(1 for _ in existing)


def stamp_ordinal(task: Task, ordinal: int) -> None:
    """Stamp the durable per-context ordinal onto ``task.metadata`` (A5, D4).

    ``task.metadata`` is a ``google.protobuf.Struct``; numeric values round-trip as
    floats (read back via :func:`ordinal_of`, which casts to ``int``).
    """
    task.metadata[ORDINAL_KEY] = ordinal


def ordinal_of(task: Task) -> int:
    """Read the stamped per-context ordinal back off a task (A5 sort key).

    Returns ``0`` for an unstamped task (defensive; the aggregate always stamps).
    The Struct stores the value as a float, so cast to ``int``.
    """
    if ORDINAL_KEY in task.metadata:
        return int(task.metadata[ORDINAL_KEY])
    return 0


def create_leg_task(
    *,
    context_id: str,
    ordinal: int,
    task_id: str,
    state: TaskState = TaskState.TASK_STATE_SUBMITTED,
) -> Task:
    """Mint a leg task under ``context_id`` with its ordinal stamped (D4).

    ``context_id`` is the exchange grouping key (ADR-0003). The ordinal is the
    durable, backend-independent sort key (A5).
    """
    task = Task(id=task_id, context_id=context_id, status=TaskStatus(state=state))
    stamp_ordinal(task, ordinal)
    return task


@dataclass(frozen=True)
class ExchangeView:
    """A read-only view of an exchange = its tasks, deterministically ordered (D3).

    The exchange is a *view over its tasks* by default (ADR-0003); this type is the
    derived read path, not a stored record.

    # M1.4: the classified-ledger projection folds a LedgerEntry over these tasks
    # (one doc per task). That fold is NOT built here.
    """

    context_id: str
    tasks: list[Task] = field(default_factory=list)


def build_exchange_view(context_id: str, tasks: Iterable[Task]) -> ExchangeView:
    """Build the exchange view over ``tasks`` for ``context_id`` (D3, D4, ADR-0003).

    Filters ``tasks`` to those whose ``.context_id == context_id`` and sorts them by
    the durable stamped ordinal (:func:`ordinal_of`) — deterministic regardless of
    input order or ``task.id`` (A5). The caller supplies the candidate tasks; this
    sidesteps the proto ``TaskStore.list`` + ``ServerCallContext`` plumbing so the
    view is unit-testable from an explicit list (M1.8 feeds it the fetched tasks).
    """
    in_context = [t for t in tasks if t.context_id == context_id]
    in_context.sort(key=ordinal_of)
    return ExchangeView(context_id=context_id, tasks=in_context)


class ExchangeRecord(BaseModel):
    """A materialized exchange record (D8) — the concrete type the M1.1 Protocol deferred.

    An exchange is a view over tasks by default (ADR-0003); a record exists ONLY
    once the exchange holds exchange-only state that forces materialization
    (Requirements artifact / program membership / skill binding / reopen — Phase
    2/3). Kept minimal on purpose: do not pre-model those aggregates here.

    ``context_id`` is the identity — the same A2A context id, never a new one.
    """

    context_id: str
    materialized: bool = True
    state: dict = Field(default_factory=dict)


async def tasks_for_context(task_store, context_id: str, *, call_context) -> list[Task]:
    """Fetch the tasks in ``context_id`` from a real A2A ``TaskStore`` (D3).

    Convenience wrapper over the proto ``TaskStore.list`` call for callers (M1.8)
    that already hold a ``ServerCallContext``. The primary, unit-testable M1.2 API
    is :func:`build_exchange_view` over an explicit task list; this helper feeds it.

    # M1.8 wires this through the A2A edge with its live ServerCallContext.
    """
    from a2a.types import ListTasksRequest

    response = await task_store.list(ListTasksRequest(context_id=context_id), call_context)
    return list(response.tasks)
