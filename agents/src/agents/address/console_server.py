"""Processing-Agent Console BFF (Frontend-v1, port 8010, SSE).

The agent's *mind* per turn: the classified ledger it was handed, its reasoning,
the authoritative :func:`~agents.address.satisfaction.is_satisfied` satisfaction
check, and the returned requirements list (``required | optional | satisfied |
waived``) with ``done``. **Sense B is watchable here** — the agent (not the
Bridge) rejects two bills from the *same* canonical issuer and asks for one more.

Wire shape (snake_case — the TS ``agent-console/src/domain/sense.ts`` maps to
camel, lessons B3):

- ``GET /console/scenarios`` → ``{"scenarios": [{"id", "label", "description"}]}``
- ``GET /console/stream?scenario=<id>`` → SSE:
    - ``event: snapshot`` — ``{"scenario", "party", "skill", "rule"}``
    - ``event: turn`` (one per Collect round) — ``{"round", "ledger_handed":[…],
      "reasoning", "satisfaction":{"done","outstanding","accepted_issuers"},
      "requirements":[{"item","status"}], "done", "terminal"}``
    - ``event: done`` — ``{"outcome"}``

The satisfaction verdict is :func:`is_satisfied` over the accumulated ledger
(authoritative — *LLM routes, code decides*, A3). It is **never** recomputed in
TS; the console relays the code gate's verdict.

Deviation from Frontend-v1 §4.1 (noted in the plan's "adapt & note" clause): the
console replays each Collect *round* by accumulating the scenario's fixture-backed
ledger entries and running ``is_satisfied`` per round, rather than driving a full
``Runner`` + live mock Bridge inside the SSE handler. This keeps the surface
deterministic and unit-testable without spinning a socket, while remaining
authoritative (the same ``is_satisfied`` gate the durable graph calls in
``graph.py``). The fixtures are the same eval corpus the mock scenarios use.

Import discipline: this is demo furniture (A9). It imports ``contract`` +
``satisfaction`` + the mock fixture loader; it does not import the production graph
assembly and nothing in ``__init__.py`` imports it.
"""

from __future__ import annotations

from contract import CollectionStatus, LedgerEntry
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

# The eval-fixture loader (shared with the mock Bridge — same corpus).
from ..mock_bridge.fixtures import load_entry
from ._bff import cors_middleware, health_route, json_response, sse_response
from .config import PARTY, SKILL
from .satisfaction import GOV_ID, UTILITY_BILL, SatisfactionResult, is_satisfied

__all__ = ["CONSOLE_SCENARIOS", "build_console_turns", "create_app", "app"]

# The Address satisfaction rule, relayed verbatim in the snapshot for legibility.
ADDRESS_RULE = "one accepted gov-id OR two accepted utility-bills from distinct issuers"


# A console scenario is an ordered list of *rounds*; each round names the fixture
# ledger ids handed to the agent so far (accumulated). Sense B is the round that
# hands two bills from the SAME canonical issuer (power-co) — still not done.
CONSOLE_SCENARIOS: dict[str, dict] = {
    "sense-b": {
        "label": "Sense B — reject two same-issuer bills",
        "description": (
            "Two utility bills from the same issuer (power-co) do not satisfy the "
            "distinct-issuer rule; the agent asks for one more from a different provider."
        ),
        "rounds": [
            ("bill-powerco-clean",),
            ("bill-powerco-clean", "bill-powerco-clean-2"),
            ("bill-powerco-clean", "bill-powerco-clean-2", "bill-aquautil-clean"),
        ],
    },
    "distinct-issuers": {
        "label": "Distinct issuers — two-bill happy path",
        "description": "One bill from power-co, then one from aqua-util — satisfied.",
        "rounds": [
            ("bill-powerco-clean",),
            ("bill-powerco-clean", "bill-aquautil-clean"),
        ],
    },
    "gov-id-instant": {
        "label": "Gov-id — instant accept",
        "description": "A clean gov-id satisfies the requirement in one round.",
        "rounds": [
            ("gov-id-clean",),
        ],
    },
}

DEFAULT_SCENARIO = "sense-b"


def _requirements_for(result: SatisfactionResult) -> list[dict]:
    """Project the satisfaction result into a requirements list (M1.9 vocabulary).

    ``required | optional | satisfied | waived`` — here the app emits a single
    "proof of address" item, ``satisfied`` when done else ``required``.
    """
    status = "satisfied" if result.done else "required"
    return [{"item": "proof of address", "status": status}]


def _reasoning_for(entries: list[LedgerEntry], result: SatisfactionResult) -> str:
    """A structured, human-legible summary of why the gate routes again vs. done.

    Sense B is the load-bearing line: two accepted bills but a single distinct
    issuer → the agent asks for one more from a different provider.
    """
    accepted = [e for e in entries if e.disposition.value == "accepted"]
    bills = [e for e in accepted if e.doctype == UTILITY_BILL]
    gov_ids = [e for e in accepted if e.doctype == GOV_ID]

    if result.done:
        if gov_ids:
            return "Accepted a gov-id — requirement satisfied; routing done."
        issuers = ", ".join(result.accepted_issuers)
        return (
            f"Accepted {len(bills)} utility bills from {len(result.accepted_issuers)} "
            f"distinct issuers ({issuers}); routing done."
        )

    if len(bills) >= 2 and len(result.accepted_issuers) == 1:
        # Sense B: two bills, one distinct issuer.
        issuer = result.accepted_issuers[0] if result.accepted_issuers else "the same issuer"
        return (
            f"Two accepted bills but both from {issuer} — the distinct-issuer rule is "
            f"not met. Rejecting the same-issuer set and asking for one more bill from a "
            f"different provider; routing again."
        )
    if len(result.accepted_issuers) == 1:
        return (
            f"One accepted bill from {result.accepted_issuers[0]}; need a second from a "
            f"distinct issuer (or a gov-id); routing again."
        )
    return "No accepted proof yet; requesting the outstanding document; routing again."


def build_console_turns(scenario_id: str) -> list[dict]:
    """Build the per-round ``turn`` frames for a scenario (pure, testable).

    Each round accumulates the scenario's fixture ledger ids, loads them as
    ``LedgerEntry``s, runs the authoritative ``is_satisfied`` gate, and shapes the
    frame. The final round is stamped ``terminal`` when the gate is done.
    """
    scenario = CONSOLE_SCENARIOS[scenario_id]
    rounds = scenario["rounds"]
    turns: list[dict] = []

    for index, ledger_ids in enumerate(rounds):
        entries = [load_entry(entry_id) for entry_id in ledger_ids]
        status = CollectionStatus(ledger=entries, outstanding=[], terminal=False)
        result = is_satisfied(status)
        is_last = index == len(rounds) - 1

        turns.append(
            {
                "round": index + 1,
                "ledger_handed": [e.model_dump(mode="json") for e in entries],
                "reasoning": _reasoning_for(entries, result),
                "satisfaction": {
                    "done": result.done,
                    "outstanding": result.outstanding,
                    "accepted_issuers": result.accepted_issuers,
                },
                "requirements": _requirements_for(result),
                "done": result.done,
                # Terminal when the gate is done, or the scenario's last scripted round.
                "terminal": result.done or is_last,
            }
        )
        if result.done:
            break

    return turns


def _scenario_list() -> list[dict]:
    return [
        {"id": key, "label": value["label"], "description": value["description"]}
        for key, value in CONSOLE_SCENARIOS.items()
    ]


async def _scenarios(_request: Request) -> JSONResponse:
    return json_response({"scenarios": _scenario_list()})


async def _stream(request: Request):
    scenario_id = request.query_params.get("scenario") or DEFAULT_SCENARIO
    if scenario_id not in CONSOLE_SCENARIOS:
        return json_response({"error": f"unknown scenario: {scenario_id}"}, status_code=404)

    turns = build_console_turns(scenario_id)
    outcome = "done" if (turns and turns[-1]["done"]) else "incomplete"

    frames: list[tuple[str, object]] = [
        (
            "snapshot",
            {
                "scenario": scenario_id,
                "party": PARTY,
                "skill": SKILL,
                "rule": ADDRESS_RULE,
            },
        )
    ]
    frames.extend(("turn", turn) for turn in turns)
    frames.append(("done", {"outcome": outcome}))

    return sse_response(frames)


def create_app() -> Starlette:
    """Create the Processing-Agent Console BFF app (testable without a socket)."""
    routes = [
        health_route(),
        Route("/console/scenarios", _scenarios, methods=["GET"]),
        Route("/console/stream", _stream, methods=["GET"]),
    ]
    return Starlette(routes=routes, middleware=cors_middleware())


# Module-level app so ``uvicorn agents.address.console_server:app`` works (C2).
app = create_app()
