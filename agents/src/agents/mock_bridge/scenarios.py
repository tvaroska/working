"""Multi-turn scenario abstraction for the mock Bridge.

A scenario scripts the mock's multi-turn evolution: each step declares which ledger
entry ids to return on that round, whether the turn is terminal, which doctypes
remain outstanding, and faked chase/timeout progress messages. Round index clamps to
the final (terminal) step so a caller that polls once more never regresses.

Parity is terminal-outcome, not ledger-identical — the mock only has to reach the
same destination (terminal reason + accepted-issuer set), never mirror a real Bridge
ledger step-by-step.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioStep:
    """A single round's returned state in a multi-turn scenario."""

    ledger_ids: tuple[str, ...]
    """Accumulated ledger entry ids returned this round."""

    terminal: bool
    """Whether this round ends the exchange (terminal=True)."""

    outstanding: tuple[str, ...] = ()
    """Outstanding doctype refs when not terminal."""

    chase_messages: tuple[str, ...] = ()
    """Non-empty WORKING progress emitted before completing (faked chase/timeout)."""


@dataclass(frozen=True)
class MockScenario:
    """A multi-turn script for the mock Bridge."""

    name: str
    steps: tuple[ScenarioStep, ...]

    def step_for_round(self, round_index: int) -> ScenarioStep:
        """Get the step for a given round, clamping to the final step.

        Args:
            round_index: Zero-based round index.

        Returns:
            The step for this round. Extra rounds keep returning the final (terminal)
            step so a caller that polls once more never regresses — protects S1-4's
            two-round live test.
        """
        return self.steps[min(round_index, len(self.steps) - 1)]


GOV_ID_INSTANT = MockScenario(
    "gov-id-instant",
    (ScenarioStep(("gov-id-clean",), terminal=True),),
)

TWO_BILLS = MockScenario(
    "two-bills",
    (
        ScenarioStep(
            ("bill-powerco-clean",),
            terminal=False,
            outstanding=("utility-bill",),
            chase_messages=(
                "Follow-up sent: statement overdue.",
                "Reminder sent — awaiting a second distinct issuer.",
                "Escalated: still only one distinct issuer on file.",
            ),
        ),
        ScenarioStep(
            ("bill-powerco-clean", "bill-aquautil-clean"),
            terminal=True,
        ),
    ),
)

SCENARIOS = {s.name: s for s in (GOV_ID_INSTANT, TWO_BILLS)}
