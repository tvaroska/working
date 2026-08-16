"""Collect plan — the injectable "what documents arrived this round" stand-in (M1.8).

The A2A edge (M1.8) owns the *edge mechanism*: accept a ``CollectRequest``, drive one
real, core-computed collect round (M1.6 disposition → M1.4 ledger), and return a
contract-faithful ``ExchangeTurn``. It does NOT own where documents come from — that is
M1.11's dual-path intake feeding M1.7's fulfillment graph. ``CollectPlan`` is the small
seam that lets the edge drive a *real* collect against **fixture-backed** arrivals
without pulling in either of those. When M1.11 lands, the arrived-document source
becomes real Path-A/Path-B intake and slots into this seam.

Parity note (docs/lessons-learned **A2**): the named default plans mirror the mock's
scenarios (``agents/src/agents/mock_bridge/scenarios.py``) for M1.13 mock→real parity,
but parity is **terminal-outcome, not ledger-identical** — these plans reach the same
destination (terminal reason + accepted-issuer set), not the mock's step-by-step ledger.

Import discipline: imports only the stdlib. Never imports ``agents`` (the mock's
scenarios are mirrored by value, not by import) or the seams/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "DEFAULT_PLANS",
    "GOV_ID_INSTANT",
    "REJECT_RESUBMIT",
    "TWO_BILLS_DISTINCT",
    "CollectPlan",
    "CollectRound",
    "plan_for_skill",
]


@dataclass(frozen=True)
class CollectRound:
    """A single round's arrived documents + terminality (M1.8).

    Attributes:
        fixture_ids: The eval fixture ids that "arrived" this round (fed to the
            extraction engine + M1.6 ``classify_document``).
        terminal: Whether this round ends the exchange.
    """

    fixture_ids: tuple[str, ...]
    terminal: bool


@dataclass(frozen=True)
class CollectPlan:
    """A scripted sequence of collect rounds (M1.8 fixture stand-in).

    Round index clamps to the final round so an extra poll never regresses (parity with
    the mock's ``step_for_round`` clamp). M1.9 owns outstanding computation from the
    real satisfaction rule; this plan only scripts which documents arrive when.
    """

    rounds: tuple[CollectRound, ...]

    def round_for(self, index: int) -> CollectRound:
        """Return the round at ``index``, clamping to the final round."""
        if not self.rounds:
            raise ValueError("CollectPlan has no rounds")
        return self.rounds[min(index, len(self.rounds) - 1)]

    def is_terminal(self, index: int) -> bool:
        """Whether the round at ``index`` is terminal (clamped)."""
        return self.round_for(index).terminal


# One round, an accepted gov-id → the app's sense-B rule is satisfied instantly.
GOV_ID_INSTANT = CollectPlan((CollectRound(("gov-id-clean",), terminal=True),))

# Round 0: one Power Co. bill, non-terminal. Round 1: a distinct-issuer (aqua-util) bill
# → the app's count-to-two distinct-issuer rule is satisfied. Drives the park
# (INPUT_REQUIRED) → resume → COMPLETED path.
TWO_BILLS_DISTINCT = CollectPlan(
    (
        CollectRound(("bill-powerco-clean",), terminal=False),
        CollectRound(("bill-aquautil-clean",), terminal=True),
    )
)

# Round 0: a blurry bill (rejected/resubmit), non-terminal. Round 1: an accepted gov-id
# → terminal. On the real Bridge a resubmission is handled *inside one Collect task*
# (``resubmit`` is non-resumable — A1); this plan is a modeling convenience for the edge
# test's terminal-outcome parity with the mock's ``reject-resubmit`` (A2), NOT a claim
# about consumer round structure.
REJECT_RESUBMIT = CollectPlan(
    (
        CollectRound(("bill-aquautil-blurry",), terminal=False),
        CollectRound(("gov-id-clean",), terminal=True),
    )
)

#: Default plan per process skill (M1.8 fixture stand-in; M1.11 replaces the source).
DEFAULT_PLANS: dict[str, CollectPlan] = {"address-proof": GOV_ID_INSTANT}


def plan_for_skill(skill: str) -> CollectPlan:
    """Resolve the default collect plan for ``skill`` (falls back to GOV_ID_INSTANT)."""
    return DEFAULT_PLANS.get(skill, GOV_ID_INSTANT)
