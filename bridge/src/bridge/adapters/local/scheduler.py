"""Local scheduler adapter with in-memory timer store (M1.12).

In-memory scheduler with injectable virtual clock for the local development
environment. Satisfies the SchedulerSeam protocol.

Note: "Durable" in M1.12 describes the **seam concept** — the local adapter is
in-memory (timers lost on restart); restart-durability of the timer store is the
Sprint-2 GCP adapter (Cloud Tasks; A7 "deletion is the fired signal"), analogous
to the local/Database split for Sessions/Task-store (M1.2).
"""

from bridge.scheduler import (
    FollowupStatus,
    SlaPolicy,
    Timer,
    VirtualClock,
    followup_status,
    plan_followups,
)

__all__ = ["LocalScheduler"]


class LocalScheduler:
    """Local (in-memory) scheduler adapter with injectable clock.

    Implements the SchedulerSeam protocol with an in-memory timer store and a
    virtual clock (integer ticks). The clock is injectable for time-warp testing.

    Exactly-once invariant (lessons-learned.md A7):
    ``due(now)`` marks each returned timer ``fired=True`` IN PLACE before returning,
    so a fired timer NEVER re-appears in subsequent ``due()`` calls.

    Deterministic ordering (lessons-learned.md A5):
    ``due()`` output is sorted by ``(fire_at, sequence, id)`` — no timestamp.

    Args:
        clock: Injectable virtual clock (default: a fresh ``VirtualClock()`` at tick 0).
    """

    def __init__(self, clock: VirtualClock | None = None):
        """Initialize the scheduler with an optional injectable clock."""
        self.clock = clock or VirtualClock()
        self._timers: dict[str, Timer] = {}

    async def schedule(self, timer: Timer) -> None:
        """Schedule a new timer (upsert by ``timer.id`` — idempotent).

        Args:
            timer: The timer to schedule.
        """
        self._timers[timer.id] = timer

    async def due(self, now: int | None = None) -> list[Timer]:
        """Return all timers due at or before ``now``, marking them fired IN PLACE.

        CRITICAL (lessons-learned.md A7): This method marks each returned timer
        ``.fired = True`` before returning. The exactly-once emission guarantee
        rides on this invariant — a fired timer NEVER re-appears.

        Deterministic ordering (lessons-learned.md A5): output is sorted by
        ``(fire_at, sequence, id)`` — no timestamp.

        Args:
            now: The tick to check (default: ``self.clock.now()``).

        Returns:
            A list of fired timers, sorted deterministically.
        """
        if now is None:
            now = self.clock.now()

        # Select unfired timers that are due
        due_timers = [t for t in self._timers.values() if not t.fired and t.fire_at <= now]

        # Sort deterministically by (fire_at, sequence, id)
        due_timers.sort(key=lambda t: (t.fire_at, t.sequence, t.id))

        # Mark each timer fired IN PLACE (A7 exactly-once)
        for timer in due_timers:
            timer.fired = True

        return due_timers

    async def cancel(self, timer_id: str) -> None:
        """Cancel a scheduled timer by ID (idempotent — no error if missing).

        Args:
            timer_id: The timer ID to cancel.
        """
        self._timers.pop(timer_id, None)

    # --- Convenience helpers (not part of the seam Protocol) ---

    async def schedule_followups(
        self,
        sla: SlaPolicy,
        *,
        context_id: str,
        task_id: str | None = None,
        start: int | None = None,
    ) -> list[Timer]:
        """Plan and schedule the SLA ladder (nudges + escalation).

        A thin convenience over ``plan_followups`` + ``schedule`` for M1.13/demo wiring.
        Not part of the seam Protocol (documented as a helper).

        Args:
            sla: The SLA policy.
            context_id: The exchange ``context_id``.
            task_id: Optional task ID (for per-task timers).
            start: The tick to measure the ladder from (default: ``self.clock.now()``).

        Returns:
            The list of scheduled timers.
        """
        if start is None:
            start = self.clock.now()

        timers = plan_followups(sla, start=start, context_id=context_id, task_id=task_id)
        for timer in timers:
            await self.schedule(timer)
        return timers

    def followups_for(self, context_id: str) -> FollowupStatus:
        """Compute the follow-up status read-model for a context.

        A thin convenience over ``followup_status`` for M1.13/demo wiring. Not part
        of the seam Protocol (documented as a helper).

        Args:
            context_id: The exchange ``context_id``.

        Returns:
            A ``FollowupStatus`` snapshot.
        """
        return followup_status(self._timers.values(), context_id=context_id)
