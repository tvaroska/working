"""Manual end-to-end run of two Collect scenarios against a live mock Bridge.

Run (from the ``agents/`` package root, so ``tests`` resolves as a package)::

    uv run python -m tests.manual_run_scenarios

Scenario 1 — single turn (``gov-id-instant``): one accepted gov-id, terminal on
round 1; the gate routes ``done`` immediately.

Scenario 2 — rejection then resubmission (``reject-resubmit``): round 1 returns a
*rejected* unsupported doc (non-terminal); the deterministic gate sees no accepted
proof and routes ``again``, which re-enters the collect node for a fresh Collect
round (NOT a HITL park/resume — resubmit is deliberately non-resumable). Round 2
returns the accepted gov-id, terminal, and the gate routes ``done``.

Both run on one shared in-memory durable session through the stock ADK Runner.
"""

import asyncio

from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.address.graph import ROUND_COUNT_STATE_KEY
from agents.address.satisfaction import (
    TERMINAL_TURN_STATE_KEY,
    _coerce_status,
    is_satisfied,
)
from bridge_client.wire import extract_exchange_turn
from tests.support.app import build_test_app
from tests.support.live_server import LiveMockServer

PARTY = "jordan-lee"
APP_NAME = "address"


def _all_turns(events):
    """Every persisted ExchangeTurn in the session, oldest-first (one per round)."""
    turns = []
    for event in events:
        turn = extract_exchange_turn([event])
        if turn is not None:
            turns.append(turn)
    return turns


def _fmt_ledger(turn):
    return [(e["doctype"], e["issuer"], e["disposition"]) for e in turn["status"]["ledger"]]


async def _run(scenario: str, park: bool = False):
    with LiveMockServer(hold_seconds=0.1, park=park, scenario=scenario) as server:
        session_service = InMemorySessionService()
        runner = Runner(
            app=build_test_app(server.card_url),
            session_service=session_service,
            artifact_service=InMemoryArtifactService(),
        )
        await session_service.create_session(app_name=APP_NAME, user_id=PARTY, session_id="s1")
        msg = types.Content(role="user", parts=[types.Part(text="collect the address proof")])
        async for _ in runner.run_async(user_id=PARTY, session_id="s1", new_message=msg):
            pass
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=PARTY, session_id="s1"
        )
        await runner.close()

    turns = _all_turns(session.events)
    final = session.state.get(TERMINAL_TURN_STATE_KEY)
    rounds = session.state.get(ROUND_COUNT_STATE_KEY)
    verdict = is_satisfied(_coerce_status(final or {}))

    print(f"\n=== scenario: {scenario} ===")
    for i, t in enumerate(turns, 1):
        print(f"  round {i}: terminal={t['status']['terminal']!s:5} ledger={_fmt_ledger(t)}")
    print(f"  gate rounds counted : {rounds}")
    print(f"  terminal            : {final['status']['terminal']}")
    print(f"  gate done           : {verdict.done}")
    print(f"  accepted issuers    : {verdict.accepted_issuers}")


async def _main():
    await _run("gov-id-instant")
    await _run("reject-resubmit")


if __name__ == "__main__":
    asyncio.run(_main())
