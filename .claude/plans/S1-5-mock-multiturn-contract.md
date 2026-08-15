# S1-5 — Mock Bridge multi-turn contract

**Task (PLAN.md, Sprint 1):** Grow the mock into the *permanent* multi-turn contract
double: fixture document arrivals across turns, faked chase/timeout, distinct-issuer
bill fixtures, plus the `INPUT_REQUIRED` park + non-empty `status.message` progress
already tracered in S1-1. **Parity is terminal-outcome, not ledger-identical** — the
mock only has to reach the same *destination* (terminal reason + accepted-issuer set),
never mirror a real Bridge ledger step-by-step.

Depends on: S1-1 (park/resume, non-empty progress `status.message`), S1-3 (`is_satisfied`),
S1-4 (durable exchange `context_id` threaded across rounds). All done.

---

## Background you need before touching code

The mock lives in `agents/src/agents/mock_bridge/` (`fixtures.py`, `executor.py`,
`app.py`, `__init__.py`). Today it is single-shot: it loads **only** `gov-id-clean`
and every completed turn returns that one terminal entry. Park mode (S1-1) is a
separate first-turn `INPUT_REQUIRED` pause that a resume turn completes.

**How multi-turn arrivals must work (this is the crux).** In the `park=False`
completing path each Collect round is a **new A2A task under the same
`context_id`** (adr-0009 S1-4 amendment — you cannot re-send to a COMPLETED task).
S1-4 threads the exchange by state: `BridgeAgentTool` writes the returned turn's
`context_id` under `EXCHANGE_CONTEXT_STATE_KEY`; the send-path interceptor stamps it
onto the next round's `message/send`. On round 1 the message carries an empty
context and the a2a-sdk server **assigns** a fresh `context_id`; round 2+ reuse it.
The executor already records each first-turn `context.context_id` into
`context_ids_seen` — proof the same id arrives every round.

**Therefore the mock advances turns by keying a per-context round counter on
`context.context_id`.** Round *N* for a given context returns scenario step *N*.
This reuses exactly the mechanism S1-4's live test already relies on.

Relevant fixtures in `wiki/evals/address/expected.json` (issuer already canonical):
- `gov-id-clean` → gov-id, disposition accepted (the instant / path-A branch).
- `bill-powerco-clean` → utility-bill, issuer `power-co`, accepted.
- `bill-aquautil-clean` → utility-bill, issuer `aqua-util`, accepted (distinct issuer).

Two-bills timeline (path B) is described in `wiki/evals/address/timeline.json`:
round 1 = one PowerCo bill (1 distinct issuer < 2 → not satisfied → chase, with
overdue/reminder/escalated followups); a later round adds a distinct-issuer bill →
2 distinct issuers → satisfied. We collapse the SLA followups into **faked chase
progress messages** on the non-terminal round (parity is terminal-outcome, so the
exact followup ledger is not asserted).

`is_satisfied` (`agents/src/agents/address/satisfaction.py`) is the terminal-outcome
oracle: address is done on one accepted gov-id **OR** ≥2 accepted bills from
distinct canonical issuers; it returns `accepted_issuers` (sorted canonical set).
`bridge_client` must never import `agents.*`, but **tests may** import both — use
`is_satisfied` in the live parity test.

---

## Design

Introduce a small **scenario** abstraction so the mock is a scriptable multi-turn
double, and make the executor **stateful per context**. Keep `park` orthogonal
(do NOT fold it into scenario stepping) so all S1-1 tests stay green. Default
behavior stays exactly `gov-id-clean` terminal every round so S1-4's live durable
test (two rounds, both gov-id-clean) stays green.

### New file: `agents/src/agents/mock_bridge/scenarios.py`

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ScenarioStep:
    ledger_ids: tuple[str, ...]          # accumulated ledger entry ids returned this round
    terminal: bool
    outstanding: tuple[str, ...] = ()    # outstanding doctype refs when not terminal
    chase_messages: tuple[str, ...] = () # non-empty WORKING progress emitted before completing

@dataclass(frozen=True)
class MockScenario:
    name: str
    steps: tuple[ScenarioStep, ...]

    def step_for_round(self, round_index: int) -> ScenarioStep:
        # clamp: extra rounds keep returning the final (terminal) step so a caller
        # that polls once more never regresses — protects S1-4's two-round live test.
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
```

### `fixtures.py` — generalize entry loading

- Add `load_entry(entry_id: str, evals_path: Path | None = None) -> LedgerEntry`
  that resolves any doc id from `expected.json`, mapping `expected_disposition →
  disposition` and building `Extraction` explicitly (the raw eval entry has extra
  keys that fail `extra="forbid"` — copy the exact mapping already in
  `load_gov_id_clean_entry`). Factor the path-resolution block (env var
  `ADDRESS_EVALS_PATH` → `parents[4]/wiki/evals/address/expected.json`) into a
  private `_resolve_evals_path` helper reused by both loaders.
- Reimplement `load_gov_id_clean_entry` as `load_entry("gov-id-clean", evals_path)`
  (keep the public name — it is exported and used by existing tests).
- Generalize `build_exchange_turn` to accept a list and explicit flags, staying
  back-compatible with the current single-entry call:
  `build_exchange_turn(context_id, ledger, *, terminal=True, outstanding=None)`
  where `ledger` is a `LedgerEntry` or `list[LedgerEntry]` (normalize to a list),
  and `outstanding` defaults to `[]`. Existing `test_build_exchange_turn`
  (`build_exchange_turn("ctx-1", entry)`) must still yield terminal=True /
  outstanding=[].

### `executor.py` — stateful, scenario-driven

- Constructor becomes:
  `__init__(self, scenario: MockScenario, *, evals_path: Path | None = None,
  hold_seconds: float = 10.0, park: bool = False)`.
  - Eagerly load every distinct id across `scenario.steps` via
    `fixtures.load_entry`, caching into `self._entries: dict[str, LedgerEntry]`
    (fail fast at construction if a fixture id is missing).
  - Keep `self.last_request_data` and `self.context_ids_seen` (seam suite reads
    them). Add `self._rounds: dict[str, int] = {}` (per-context round counter).
- `execute(context, event_queue)`:
  1. **Park resume branch unchanged** (S1-1): if `park` and
     `context.current_task` is `INPUT_REQUIRED`, call `_complete(...)` with the
     scenario's **final** step (`scenario.steps[-1]`) and `return`. (Default park
     scenario = gov-id-instant → still completes with `gov-id-clean`, so S1-1 tests
     pass.)
  2. Capture `last_request_data` from the inbound message's data parts and append
     `context.context_id` to `context_ids_seen` (unchanged from today).
  3. Compute the round: `r = self._rounds.get(ctx, 0); self._rounds[ctx] = r + 1`
     (`ctx = context.context_id`); `step = self._scenario.step_for_round(r)`.
  4. Enqueue the `Task(SUBMITTED)` object, then `updater.start_work(message=
     new_text_message("Collecting address proof…"))`, then
     `await asyncio.sleep(self._hold_seconds)` — same ordering as today (start_work
     must precede the sleep so `message/send` returns immediately).
  5. **Faked chase/timeout:** for each `msg` in `step.chase_messages`, emit
     `await updater.update_status(TaskState.TASK_STATE_WORKING,
     message=new_text_message(msg))`. These are the S1-1 non-empty progress
     `status.message`s standing in for SLA followups. **Do not** emit
     `INPUT_REQUIRED` here — the non-terminal completing round still COMPLETES with
     a non-terminal ledger; it does not park.
  6. If `park` and this is the first turn → `update_status(INPUT_REQUIRED,
     message=new_text_message("Awaiting additional proof to proceed."))` and
     `return` (S1-1 path preserved).
  7. Else `await self._complete(context, event_queue, step=step, resume=False)`.
- `_complete(self, context, event_queue, *, step, resume)`:
  - On `resume=True`, emit the existing `start_work("Resuming with provided
    input…")`.
  - Build ledger from `[self._entries[i] for i in step.ledger_ids]`; call
    `build_exchange_turn(context.context_id, ledger, terminal=step.terminal,
    outstanding=list(step.outstanding))`; attach as `new_data_part(turn.model_dump
    (mode="json"))` and `updater.complete()` — unchanged mechanics.
- `cancel` unchanged.

### `app.py` — plumb scenario selection

- `create_app(..., scenario: MockScenario | str | None = None, ...)`.
  Resolve: `None → GOV_ID_INSTANT`; `str → SCENARIOS[str]` (raise a clear
  `KeyError`/`ValueError` on unknown name); `MockScenario → as-is`.
- Stop calling `load_gov_id_clean_entry` here; construct
  `MockBridgeExecutor(scenario, evals_path=evals_path, hold_seconds=..., park=...)`.
  The executor now owns fixture loading. Keep `app.state.mock_executor` exposure.
- Card build is unchanged (still advertises the `address-proof` skill,
  `streaming=True`).

### `__init__.py` — exports

- Export `MockScenario`, `ScenarioStep`, `SCENARIOS`, `GOV_ID_INSTANT`,
  `TWO_BILLS`, and `load_entry` alongside the existing names.

### `tests/support/live_server.py`

- Add `scenario: MockScenario | str | None = None` to `LiveMockServer.__init__`
  and pass it through to `create_app` in `__enter__`. Default `None` keeps every
  existing caller (gov-id-instant) unchanged.

---

## Tests

Run with `uv run pytest` from `agents/` (fallback `.venv/bin/pytest`). All must pass.

### Update `tests/test_mock_bridge.py`
- `test_executor_emits_working_then_completed`: construct via the new API —
  `MockBridgeExecutor(GOV_ID_INSTANT, evals_path=..., hold_seconds=0.0)` (import
  `GOV_ID_INSTANT` from `agents.mock_bridge`). Assertions otherwise unchanged
  (SUBMITTED → WORKING → artifact → COMPLETED, one `gov-id-clean` entry).

### Add to `tests/test_mock_bridge.py` (hermetic, FakeQueue — no sockets)
- `test_load_entry_distinct_issuer_bills`: `load_entry("bill-powerco-clean")` and
  `load_entry("bill-aquautil-clean")` → doctype `utility-bill`, issuers `power-co`
  / `aqua-util`, disposition `accepted`.
- `test_two_bills_scenario_steps`: `TWO_BILLS.step_for_round(0)` not terminal, 1
  id, outstanding `("utility-bill",)`, chase messages non-empty;
  `step_for_round(1)` terminal, 2 ids; `step_for_round(2)` clamps to the terminal
  step.
- `test_executor_two_bills_multiturn`: with `MockBridgeExecutor(TWO_BILLS,
  hold_seconds=0.0)` and a `FakeQueue`, call `execute()` **twice with the same
  `context_id`** (reuse the existing FakeQueue pattern; fresh queue each call).
  - Round 1: at least one `WORKING` status event carries a **non-empty**
    `status.message` (the faked chase), final event COMPLETED, decoded
    `ExchangeTurn.status.terminal is False`, ledger = `[bill-powerco-clean]`.
  - Round 2: COMPLETED, terminal True, ledger ids `{bill-powerco-clean,
    bill-aquautil-clean}`.
  - (Assert progress text via `a2a.helpers.proto_helpers.get_message_text` on the
    WORKING events' `status.message`.)

### New file `tests/test_mock_multiturn.py` (live seam — real sockets)
Headline S1-5 parity test. Mirror `test_collect_loop._run_two_rounds` but drive the
`two-bills` scenario and assert **terminal-outcome parity via `is_satisfied`**:
- `with LiveMockServer(hold_seconds=0.2, scenario="two-bills") as server:` build
  `build_bridge_remote_agent(card_url, name="document_bridge",
  collect_request=CollectRequest(party=PARTY, skill=SKILL))`, wrap in
  `BridgeAgentTool(..., skip_summarization=False,
  result_state_key=COLLECTION_STATUS_STATE_KEY)`, make a real `ToolContext`
  (copy `_make_tool_context` from `test_collect_loop`), run two rounds reusing the
  same tool_context (state persists → interceptor threads the same context).
- Assertions:
  - Round 1 turn: `context_id` non-empty (call it X); ledger has the PowerCo bill;
    `is_satisfied(CollectionStatus.model_validate(round1["status"])).done is False`.
  - Round 2 turn: `context_id == X` (same exchange); `is_satisfied(...).done is
    True` and `.accepted_issuers == ["aqua-util", "power-co"]` (sorted canonical
    set — the terminal-outcome parity claim).
  - `server.executor.context_ids_seen == [X, X]` (one durable exchange, no fresh
    context per round).
- Import `is_satisfied`, `CollectionStatus`, `COLLECTION_STATUS_STATE_KEY`,
  `PARTY`, `SKILL`, `APP_NAME` from the same places `test_collect_loop.py` does.

Do not weaken the existing S1-1 park tests (`test_native_consumer.py`) or the S1-4
durable test — they must remain green untouched.

---

## Acceptance criteria
- `agents/src/agents/mock_bridge/scenarios.py` exists with `MockScenario`,
  `ScenarioStep`, `GOV_ID_INSTANT`, `TWO_BILLS`, `SCENARIOS`.
- Mock is stateful per `context_id`: successive Collect rounds under one exchange
  return the scripted, **accumulating** ledger; round index clamps to the terminal
  step.
- `load_entry` loads any eval doc; the two distinct-issuer bill fixtures load with
  canonical issuers `power-co` / `aqua-util`.
- Non-terminal rounds emit faked chase/timeout as **non-empty** `WORKING`
  `status.message` progress; no spurious `INPUT_REQUIRED` on the completing path.
- S1-1 `INPUT_REQUIRED` park + resume→COMPLETED preserved (default gov-id).
- Live seam test proves multi-turn arrivals reach the **same terminal outcome**
  (`is_satisfied.done` True, accepted issuers `{aqua-util, power-co}`) over one
  durable exchange context — parity asserted as terminal-outcome, not
  ledger-identical.
- `uv run pytest` fully green.

## Gotchas (do not rediscover)
- **Per-context round counter, not a global one.** Key on `context.context_id`;
  round 1 gets a server-assigned context, round 2+ reuse it via the S1-4
  interceptor. A global counter breaks concurrent exchanges and the clamp logic.
- **Clamp `step_for_round`** so an extra round never regresses off the end — this is
  what keeps S1-4's two-round default-scenario live test (both rounds gov-id-clean)
  green.
- **Keep `park` orthogonal.** Do not merge park into scenario stepping; S1-1 tests
  pass `park=True` with the default scenario and expect gov-id-clean on resume.
- Chase progress must be `WORKING` status updates (non-empty message), **not**
  `INPUT_REQUIRED` — the non-terminal round still COMPLETES with a non-terminal
  ledger so the caller's `is_satisfied` gate drives the next round.
- `start_work()` must precede the `hold` sleep, else `message/send` blocks and the
  async surface is defeated (pre-existing invariant in the executor docstring).
- `build_exchange_turn` / executor constructor signature changes ripple to
  `test_mock_bridge.py` and `app.py`; update both. `load_gov_id_clean_entry` name
  is exported and used — keep it.
- `bridge_client` must not import `agents.*`; only the *test* imports `is_satisfied`.
- Raw eval entries have extra keys (`issuer_raw`, `expected_disposition`, …) that
  fail `LedgerEntry`/`Extraction` `extra="forbid"` — `load_entry` must map
  explicitly, exactly like the current `load_gov_id_clean_entry`.
```
