"""Local scheduler adapter (skeleton — M1.12 fills in behavior).

In-memory scheduler with injectable virtual clock for the local development
environment. Satisfies the SchedulerSeam protocol. Real behavior lands in M1.12.
"""

from typing import Any

__all__ = ["LocalScheduler"]


class LocalScheduler:
    """Local (in-memory) scheduler adapter with injectable clock.

    Skeleton conforming to SchedulerSeam. Methods raise NotImplementedError
    until M1.12 implements the real in-memory timer store + virtual clock logic.

    Args:
        clock: Injectable virtual clock (unused for now; M1.12 defines the interface)
    """

    def __init__(self, clock: Any = None):
        """Initialize the scheduler with an optional injectable clock."""
        self.clock = clock

    async def schedule(self, timer: object) -> None:
        """Schedule a new timer."""
        raise NotImplementedError("M1.12: durable timers + virtual clock")

    async def due(self, now: Any) -> list[object]:
        """Return all timers due at or before `now`, marking them fired IN PLACE."""
        raise NotImplementedError("M1.12: durable timers + virtual clock")

    async def cancel(self, timer_id: str) -> None:
        """Cancel a scheduled timer by ID."""
        raise NotImplementedError("M1.12: durable timers + virtual clock")
