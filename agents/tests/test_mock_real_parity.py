"""M1.13 — mock→real swap proof: terminal-outcome parity on local adapters.

The capstone integration proof of Milestone 1. The *same* durable Collect graph
(``tests.support.app.build_test_app``) is pointed at each backend by **card URL
only** — the mock Bridge (``LiveMockServer``) and the real Bridge edge
(``LiveBridgeServer``) — and both must reach the **same terminal outcome**: same
terminal reason (``is_satisfied(...).done``) + accepted-issuer set. There are **no
production agent edits**; the swap is a no-op for the agent.

Parity is **terminal-outcome, not ledger-identical** (docs/lessons-learned A2): the
mock and real legitimately diverge turn-by-turn (e.g. the mock ``reject-resubmit``
is a single terminal turn with a rejected passport; the real reaches the same
destination via a park→resume with a rejected blurry bill). We assert only the
destination, via the authoritative deterministic gate
(``agents.address.satisfaction.is_satisfied`` — *LLM routes, code decides*, A3),
never a step-by-step ledger match.

Seams exercised: **Sessions** (``InMemorySessionService``) and **Task store**
(``InMemoryTaskStore``, the default inside both ``create_app``s) — both local
adapters. S1-6 already proved durability across a restart; M1.13 proves swap
parity, so in-memory services suffice here. The local→GCP variants are Sprint 2.

Follows the sync-test + ``asyncio.run(...)`` idiom of ``test_durable_graph.py``
(agents has no anyio plugin — do not introduce ``@pytest.mark.anyio``).
"""

import asyncio
from dataclasses import dataclass

import pytest
from bridge.edges.a2a.plan import GOV_ID_INSTANT, REJECT_RESUBMIT, TWO_BILLS_DISTINCT
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.address.satisfaction import (
    TERMINAL_TURN_STATE_KEY,
    _coerce_status,
    is_satisfied,
)
from tests.support.app import build_test_app
from tests.support.live_bridge_server import LiveBridgeServer
from tests.support.live_server import LiveMockServer

PARTY = "jordan-lee"
APP_NAME = "address"

# Defensive cap so a broken integration fails fast rather than hangs; three test
# scenarios park at most once, so anything beyond this is a resume that never
# terminates.
MAX_RESUME_ROUNDS = 6


# --------------------------------------------------------------------------- #
# Helpers (park-agnostic driver; small ones replicate test_durable_graph.py)
# --------------------------------------------------------------------------- #


def _find_paused_call(events):
    """Return the function_call that paused the runner, or None."""
    for event in events:
        if not event.long_running_tool_ids:
            continue
        for fc in event.get_function_calls():
            if fc.id in event.long_running_tool_ids:
                return fc
    return None


def _collect_message(text: str = "collect the address proof") -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=text)])


def _resume_message(paused) -> types.Content:
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=paused.id,
                    name=paused.name,
                    response={"status": "provided"},
                )
            )
        ],
    )


def _make_runner(card_url: str, session_service) -> Runner:
    """A durable App runner for the graph pointed at ``card_url`` (the swap point)."""
    return Runner(
        app=build_test_app(card_url),
        session_service=session_service,
        artifact_service=InMemoryArtifactService(),
    )


async def _drive_to_terminal(card_url: str) -> dict | None:
    """Run the graph to its terminal turn, feeding a resume on each park.

    Park structure differs between backends (mock ``reject-resubmit`` is 0-park;
    real is 1-park), so the driver is park-agnostic: run, and whenever the run
    pauses on a ``LongRunningFunctionTool`` call feed a matching
    ``FunctionResponse`` and continue; repeat until a run completes with no pending
    pause; then read the terminal turn off shared session state.
    """
    session_service = InMemorySessionService()
    runner = _make_runner(card_url, session_service)
    await session_service.create_session(app_name=APP_NAME, user_id=PARTY, session_id="s1")
    message = _collect_message()
    for _ in range(MAX_RESUME_ROUNDS):
        events = [
            e async for e in runner.run_async(user_id=PARTY, session_id="s1", new_message=message)
        ]
        paused = _find_paused_call(events)
        if paused is None:
            break
        message = _resume_message(paused)
    session = await session_service.get_session(app_name=APP_NAME, user_id=PARTY, session_id="s1")
    await runner.close()
    return session.state.get(TERMINAL_TURN_STATE_KEY)


def _fingerprint(turn: dict | None) -> tuple[bool, frozenset[str]]:
    """Terminal-outcome fingerprint: (done, accepted-issuer set). A2 parity unit."""
    res = is_satisfied(_coerce_status(turn or {}))
    return (res.done, frozenset(res.accepted_issuers))


# --------------------------------------------------------------------------- #
# Scenario config: (mock_kwargs, real_kwargs, expected_done, expected_issuers)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ScenarioConfig:
    mock_kwargs: dict
    real_kwargs: dict
    expected_done: bool
    expected_accepted_issuers: frozenset[str]


SCENARIO_CONFIG: dict[str, ScenarioConfig] = {
    # One accepted gov-id; no park either side. gov-id path has no bill issuers.
    "gov-id-instant": ScenarioConfig(
        mock_kwargs={"scenario": "gov-id-instant", "park": False},
        real_kwargs={"collect_plan": GOV_ID_INSTANT},
        expected_done=True,
        expected_accepted_issuers=frozenset(),
    ),
    # Two distinct-issuer bills. Mock MUST set park=True: with park=False a
    # content-less loop-back re-entry sends no parts, the gate re-reads the same
    # 1-bill turn, and the loop spins to MAX_ROUNDS with done=False (A12). park=True
    # delivers the second bill via a park/resume in one collect task. The real edge
    # parks natively (round0 non-terminal → INPUT_REQUIRED → resume).
    "two-bills": ScenarioConfig(
        mock_kwargs={"scenario": "two-bills", "park": True},
        real_kwargs={"collect_plan": TWO_BILLS_DISTINCT},
        expected_done=True,
        expected_accepted_issuers=frozenset({"power-co", "aqua-util"}),
    ),
    # Mock MUST stay park=False: it models resubmit as a single terminal turn
    # (resubmit is non-resumable, A1/A12) — a rejected passport + an accepted gov-id.
    # The real edge reaches the same terminal outcome via a park→resume (its plan has
    # a non-terminal round 0 blurry bill → resume → gov-id). This mismatch is exactly
    # why parity is terminal-outcome only.
    "reject-resubmit": ScenarioConfig(
        mock_kwargs={"scenario": "reject-resubmit", "park": False},
        real_kwargs={"collect_plan": REJECT_RESUBMIT},
        expected_done=True,
        expected_accepted_issuers=frozenset(),
    ),
}


# --------------------------------------------------------------------------- #
# The parity test — drive BOTH backends and compare terminal outcomes
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("scenario", ["gov-id-instant", "two-bills", "reject-resubmit"])
def test_terminal_outcome_parity(scenario):
    """Same terminal outcome against mock and real, changing only the card URL."""
    cfg = SCENARIO_CONFIG[scenario]

    # The only differing argument between the two runs is the card URL: both call
    # build_test_app(<card_url>) with the identical graph — the swap is card-URL-only.
    with LiveMockServer(hold_seconds=0.05, **cfg.mock_kwargs) as mock:
        mock_turn = asyncio.run(_drive_to_terminal(mock.card_url))
    with LiveBridgeServer(hold_seconds=0.02, **cfg.real_kwargs) as real:
        real_turn = asyncio.run(_drive_to_terminal(real.card_url))

    for label, turn in (("mock", mock_turn), ("real", real_turn)):
        assert turn is not None, f"{label}: no terminal turn recorded"
        assert turn["status"]["terminal"] is True, f"{label}: not terminal"
        res = is_satisfied(_coerce_status(turn))
        assert res.done is cfg.expected_done, f"{label}: done mismatch"
        assert (
            set(res.accepted_issuers) == cfg.expected_accepted_issuers
        ), f"{label}: accepted-issuer mismatch"

    # Terminal-outcome parity (A2): same destination, never a ledger-identical match.
    assert _fingerprint(mock_turn) == _fingerprint(real_turn)
