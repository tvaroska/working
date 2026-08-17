"""Shared in-process demo world for the ops + time-warp BFF servers (Frontend-v1).

The Servicer Ops Dashboard (``ops_server``) and the time-warp control
(``timewarp_server``) share **one** virtual clock + M1.12 scheduler so that
advancing the clock in time-warp surfaces ``overdue → escalated`` on ops. This
module holds that shared state (:class:`DemoWorld`): the clock, a ``LocalScheduler``
with the address SLA ladder pre-scheduled, and a small seeded read-model (exchanges
in flight + a HITL item).

Cross-process caveat (honest deviation, Frontend-v1 §4.4): when the four BFF
servers run as *separate* uvicorn processes, each builds its own ``DemoWorld`` — an
in-memory object cannot be shared across processes. Within-process wiring (the
pytest suite and any single-process harness) shares one world by passing it to both
``create_app`` factories; the Playwright e2e drives ops + time-warp through the
one-shot network stub (lessons B1) rather than a live shared clock. A truly shared,
cross-process clock is a Sprint-2 concern (the scheduler seam over a real store).

Demo furniture (lessons A9): imports ``bridge`` (the scheduler seam) + the mock
fixture loader. Never imported by ``__init__.py`` / the production graph.
"""

from __future__ import annotations

from bridge.adapters.local.scheduler import LocalScheduler
from bridge.scheduler import FollowupState, SlaPolicy, Timer, VirtualClock
from contract import Disposition, LedgerEntry

from ..mock_bridge.fixtures import load_entry

__all__ = ["DemoWorld", "address_sla"]

# The exchange context the SLA ladder is attached to (the one time-warp escalates).
CHASING_EXCHANGE = "exchange-two-bills"
HITL_EXCHANGE = "exchange-hitl"


def address_sla() -> SlaPolicy:
    """The address-proof SLA policy (deadline 3 / cadence 2 / max_nudges 2 — C1).

    Prefers the value loaded from the ``address-proof`` skill; falls back to the C1
    constants if the skill registry cannot resolve it (keeps the demo self-contained).
    """
    try:
        from bridge.adapters.local.skill_registry import LocalSkillRegistry

        skill = LocalSkillRegistry()._skills.get("address-proof")
        if skill is not None and skill.policy is not None and skill.policy.sla is not None:
            return skill.policy.sla
    except Exception:
        pass
    return SlaPolicy(deadline=3, cadence=2, max_nudges=2)


class _Exchange:
    """A minimal in-flight exchange in the ops read-model."""

    def __init__(
        self,
        exchange_id: str,
        party: str,
        ledger: list[LedgerEntry],
        outstanding: list[str],
    ):
        self.id = exchange_id
        self.party = party
        self.ledger = ledger
        self.outstanding = outstanding

    @property
    def terminal(self) -> bool:
        return not self.outstanding and all(
            e.disposition == Disposition.ACCEPTED for e in self.ledger
        )


class DemoWorld:
    """The shared clock + scheduler + seeded read-model driving ops & time-warp."""

    def __init__(self) -> None:
        self.sla = address_sla()
        self._reset_state()

    # --- lifecycle -------------------------------------------------------- #
    def _reset_state(self) -> None:
        self.clock = VirtualClock()
        self.scheduler = LocalScheduler(clock=self.clock)
        # Chasing exchange: one accepted bill, still awaiting a second distinct issuer.
        chasing = _Exchange(
            CHASING_EXCHANGE,
            party="jordan-lee",
            ledger=[load_entry("bill-powerco-clean")],
            outstanding=["utility-bill"],
        )
        # HITL exchange: an expired gov-id sits PENDING awaiting a human decision.
        hitl = _Exchange(
            HITL_EXCHANGE,
            party="jordan-lee",
            ledger=[load_entry("gov-id-expired")],
            outstanding=["gov-id"],
        )
        self.exchanges: dict[str, _Exchange] = {chasing.id: chasing, hitl.id: hitl}
        # Schedule the SLA ladder on the chasing exchange (from tick 0).
        self._timers = self.scheduler._timers  # (mutated by due() in place — A7)
        for timer in _plan(self.sla, context_id=CHASING_EXCHANGE):
            self._timers[timer.id] = timer

    def reset(self) -> None:
        """Replay: reset the clock, scheduler, and read-model to their seeds."""
        self._reset_state()

    # --- time-warp -------------------------------------------------------- #
    async def advance(self, ticks: int) -> list[Timer]:
        """Advance the virtual clock N ticks and fire due timers (exactly-once, A7)."""
        if ticks < 0:
            raise ValueError("ticks must be non-negative")
        self.clock.advance(ticks)
        return await self.scheduler.due(self.clock.now())

    async def step(self) -> list[Timer]:
        """Advance one tick and fire due timers."""
        return await self.advance(1)

    def now(self) -> int:
        return self.clock.now()

    def followups_for(self, context_id: str):
        return self.scheduler.followups_for(context_id)

    # --- ops read-model --------------------------------------------------- #
    def resolve_hitl(self, doc_id: str, accept: bool) -> bool:
        """Resolve a pending (HITL) ledger entry by id. Returns True if found."""
        for exchange in self.exchanges.values():
            for i, entry in enumerate(exchange.ledger):
                if entry.id == doc_id and entry.disposition == Disposition.PENDING:
                    new_disp = Disposition.ACCEPTED if accept else Disposition.REJECTED
                    exchange.ledger[i] = entry.model_copy(update={"disposition": new_disp})
                    if accept and doc_id.startswith("gov-id"):
                        exchange.outstanding = []
                    return True
        return False

    def read_model(self) -> dict:
        """Project the seeded exchanges + scheduler into the ops read-model snapshot."""
        exchanges = []
        escalation_queue = []
        hitl_queue = []
        for exchange in self.exchanges.values():
            followup = self.followups_for(exchange.id)
            exchanges.append(
                {
                    "id": exchange.id,
                    "party": exchange.party,
                    "ledger": [e.model_dump(mode="json") for e in exchange.ledger],
                    "outstanding": exchange.outstanding,
                    "terminal": exchange.terminal,
                    "followup": {
                        "state": followup.state.value,
                        "nudges_fired": followup.nudges_fired,
                        "escalated": followup.escalated,
                    },
                }
            )
            if followup.state != FollowupState.ON_TRACK:
                escalation_queue.append(
                    {
                        "exchange_id": exchange.id,
                        "state": followup.state.value,
                        "nudges_fired": followup.nudges_fired,
                        "escalated": followup.escalated,
                    }
                )
            for entry in exchange.ledger:
                if entry.disposition == Disposition.PENDING:
                    hitl_queue.append(
                        {
                            "exchange_id": exchange.id,
                            "doc_id": entry.id,
                            "doctype": entry.doctype,
                            "issuer": entry.issuer,
                        }
                    )
        return {
            "now": self.now(),
            "exchanges": exchanges,
            "hitl_queue": hitl_queue,
            "escalation_queue": escalation_queue,
        }


def _plan(sla: SlaPolicy, *, context_id: str) -> list[Timer]:
    from bridge.scheduler import plan_followups

    return plan_followups(sla, start=0, context_id=context_id)
