"""Task store seam: durable A2A task (no TTL).

Each A2A leg is one durable task (corresponds 1:1 with a session). The local adapter
uses InMemoryTaskStore; the GCP adapter uses DatabaseTaskStore. See
wiki/bridge-seams.md for the full contract.

CAVEAT: @runtime_checkable Protocols check method presence only, not signatures.
This is the desired behavior for M1.1 conformance smoke tests — real behavior and
signature validation are pinned by the shared suite in M1.2+. Keep every Protocol
method-only (no data attributes) or isinstance will raise/misbehave.

Invariant (lessons-learned.md A5): The classified ledger has no timestamp — in-memory
ordering rides on dict insertion order. Any persistent/GCP `list` implementation must
impose a deterministic sort key (the ledger/rows have no timestamp; in-memory rides
insertion order).
"""

from typing import Protocol, runtime_checkable

from a2a.types import Task

__all__ = ["TaskStoreSeam"]


@runtime_checkable
class TaskStoreSeam(Protocol):
    """Seam for durable task storage (mirrors a2a-sdk TaskStore).

    Local adapter: InMemoryTaskStore (a2a.server.tasks)
    GCP adapter: DatabaseTaskStore (Sprint 2)

    Methods mirror the a2a-sdk TaskStore ABC that the Bridge uses.
    """

    async def save(self, task: Task) -> None:
        """Save or update a task."""
        ...

    async def get(self, task_id: str) -> Task | None:
        """Retrieve a task by ID, or None if not found."""
        ...

    async def delete(self, task_id: str) -> None:
        """Delete a task."""
        ...

    async def list(self, **kwargs) -> list[Task]:
        """List tasks (with optional filtering via kwargs)."""
        ...
