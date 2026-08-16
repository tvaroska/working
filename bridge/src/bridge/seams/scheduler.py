"""Scheduler seam: durable timers + injectable virtual clock.

The scheduler manages proactive follow-up (SLA nudges, overdue→escalation) with
durable timers and an injectable virtual clock for time-warp testing. See
wiki/bridge-seams.md and M1.12 for the full contract.

CAVEAT: @runtime_checkable Protocols check method presence only, not signatures.
This is the desired behavior for M1.1 conformance smoke tests — real behavior and
signature validation are pinned by the shared suite in M1.2+. Keep every Protocol
method-only (no data attributes) or isinstance will raise/misbehave.

Invariant (lessons-learned.md A7 — CRITICAL): The `due(now)` method marks each
returned timer `fired` IN PLACE before returning. This is how the no-duplicate
guarantee is achieved — exactly-once emission rides on this invariant. The M1.12
implementation must preserve this contract, and any persistent adapter must enforce
it (e.g., via an atomic mark-as-fired + return operation).
"""

from typing import Any, Protocol, runtime_checkable

__all__ = ["SchedulerSeam"]


@runtime_checkable
class SchedulerSeam(Protocol):
    """Seam for durable timers and virtual clock.

    Local adapter: LocalScheduler (bridge.adapters.local, injectable clock)
    GCP adapter: DatabaseScheduler + CloudScheduler (Sprint 2)

    Manages proactive follow-up:
    - SLA cadence/deadline/max-nudges from skill policy (M1.3)
    - overdue → escalated transition
    - Injectable virtual clock for time-warp testing (frontend Theater mode)

    Note: The concrete Timer type and virtual clock mechanism are defined by M1.12;
    signatures use `object` here as a placeholder.
    """

    async def schedule(self, timer: object) -> None:
        """Schedule a new timer.

        # M1.12 defines the Timer type.
        """
        ...

    async def due(self, now: Any) -> list[object]:
        """Return all timers due at or before `now`, marking them fired IN PLACE.

        CRITICAL (lessons-learned.md A7): This method MUST mark each returned timer
        as `fired` before returning. The exactly-once emission guarantee rides on
        this invariant — callers assume a timer returned here will never be returned
        again.

        # M1.12 defines the Timer type and `now` representation.
        """
        ...

    async def cancel(self, timer_id: str) -> None:
        """Cancel a scheduled timer by ID."""
        ...
