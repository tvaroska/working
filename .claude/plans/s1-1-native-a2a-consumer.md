# S1-1 — Native A2A consumer (adr-0009), full incl. park/resume

## Context

PLAN.md's first Sprint-1 bullet ("Native A2A consumer (`adr-0009`)") is the consumer-construct
switch: adopt the platform-native **`RemoteA2aAgent`** as the Bridge consumer, and redesign the
contract so a wait is a **native pause** (`INPUT_REQUIRED` → mock `LongRunningFunctionTool` call →
resume) and progress rides a **non-empty `TaskStatusUpdateEvent.status.message`**. This supersedes
the M0 hand-rolled `BridgeClient` poll loop (kept as a tracer-bullet double only). `RemoteA2aAgent`
is `@a2a_experimental` (ADK 2.7.0), so ADR-0009 (C5) mandates a **spike before leaning on it** —
this task is that spike plus the contract changes it validates.

**Scope decision (user chose "Full incl. park/resume"):** land the full park/resume tracer now —
mock does `WORKING → INPUT_REQUIRED → (resume) → COMPLETED`, proving native pause/resume — *without*
the multi-turn `is_satisfied` Collect loop (that stays in the next PLAN.md bullet). The park here is
a **mechanism tracer**, not real requirements logic.

### Verified facts (probed against the installed SDKs)

- `a2a-sdk` **1.1.2**, `google-adk` **2.7.0**. Types are protobuf messages.
- `RemoteA2aAgent(name, agent_card=<URL str>, *, use_legacy=True, httpx_client=...)` — accepts a
  card **URL string**; `use_legacy` already defaults `True` (pin explicitly).
- On an `INPUT_REQUIRED` task snapshot, `_handle_a2a_response` → `_add_mock_function_call(event,
  state)` injects a **long-running mock function call** (Runner pauses); the remote-response event
  carries `a2a:task_id` / `a2a:context_id` in `custom_metadata`.
- Resume: a `FunctionResponse` re-sent as the next user turn →
  `_create_a2a_request_for_user_function_response` re-attaches `task_id`/`context_id` → same task.
- Server side: when an incoming `message/send` carries a `task_id`, `DefaultRequestHandler` loads the
  existing task from the store and exposes it as **`context.current_task`** — so the mock executor
  can branch first-turn vs. resume on `context.current_task`.
- Progress `status.message` is consumed by `RemoteA2aAgent` **only over streaming** (the
  `TaskStatusUpdateEvent` branch, gated by `_compat.normalize_message` which drops the always-present
  empty proto message — lessons A11). The **park** message is on the `INPUT_REQUIRED` snapshot and is
  readable non-streaming.
- Helpers: `proto_helpers.new_text_message(text)` builds a proto `Message`;
  `TaskUpdater.start_work(message=...)` and `update_status(state, message=...)` attach it.

## Approach

### 1. Mock Bridge — park/resume mode + non-empty status messages
`agents/src/agents/mock_bridge/executor.py`, `app.py`, `fixtures.py`

- Add `park: bool = False` to `MockBridgeExecutor.__init__` and thread it through
  `create_app(..., park=False)`. **Default stays single-turn** so M0.6 and the port double are
  untouched.
- Executor branches on `context.current_task`:
  - **First turn** (`current_task is None` or state `SUBMITTED`/`WORKING`): enqueue `Task{SUBMITTED}`
    (as today) → `updater.start_work(message=new_text_message("Collecting address proof…"))` (this
    puts a **non-empty progress message** on the WORKING transition without adding events, so M0.6's
    `observed.count(WORKING) >= 2` still holds) → `sleep(hold_seconds)`.
    - If `park`: `updater.update_status(TASK_STATE_INPUT_REQUIRED,
      message=new_text_message("Awaiting additional proof to proceed."))` and **return** (do not
      complete).
    - Else (default): attach artifact + `complete()` exactly as today.
  - **Resume turn** (`current_task.status.state == INPUT_REQUIRED`): `start_work(message=…"Resuming
    with provided input."…)` → build the gov-id-clean `ExchangeTurn` (reuse
    `build_exchange_turn(context.context_id, self._ledger_entry)`) → `add_artifact` → `complete()`.
- `build_agent_card`: set `capabilities=AgentCapabilities(streaming=True, push_notifications=False)`
  (Sprint 1 needs streaming for progress consumption). Port is unaffected — it forces
  `ClientConfig(streaming=False, polling=True)`.

### 2. Native consumer factory
`agents/src/bridge_client/remote_consumer.py` (new), exported from `bridge_client/__init__.py`

- `build_bridge_remote_agent(agent_card_url, *, name="document_bridge", use_legacy=True,
  httpx_client=None) -> RemoteA2aAgent` — card-configured (URL string), `use_legacy` **pinned** with
  a comment citing adr-0009's integration-extension-mode pin. This is the swap point: mock→real /
  local→GCP is a different card URL, not different agent code.
- Leave the M0 `BridgeClient` port + `A2ABridgeClient` in place (tracer-bullet double).

### 3. Port guard — park ≠ failure
`agents/src/bridge_client/port.py`, `agents/src/bridge_client/a2a_client.py`

- Remove `INPUT_REQUIRED` / `AUTH_REQUIRED` from `_TERMINAL_FAILURE_STATES`.
- Add `BridgeParkedError(BridgeClientError)` in `port.py`; in the poll loop, on a park state raise
  it with a clear message: the M0 port cannot resume — parked collections require the native
  `RemoteA2aAgent` consumer (adr-0009). This honors "park is not a failure/rejection" while staying
  honest that the port has no resume path (prevents a silent hang-until-timeout). Update the module
  docstring/comment accordingly.

### 4. Tests — seam coverage (defensive: contract-level + native-construct spike)
`agents/tests/test_native_consumer.py` (new); generalize `_LiveMockServer`

- Lift `_LiveMockServer` into `tests/support/` (or add a `park` kwarg in place) so both this test and
  M0.6 can request park mode; pass `park` through to `create_app`.
- **Test A — contract-level (deterministic, no RemoteA2aAgent):** drive the park-mode mock with a
  raw a2a-sdk client (mirror `A2ABridgeClient`'s send/poll): assert observed states go
  `WORKING → INPUT_REQUIRED`, the `INPUT_REQUIRED` snapshot's `status.message` is **non-empty**, then
  send a resume `message/send` to the **same `task_id`/`context_id`** → assert `COMPLETED` with the
  gov-id-clean artifact. Locks the wire contract regardless of ADK internals.
- **Test B — native-construct spike:** run `build_bridge_remote_agent(card_url)` as the root agent in
  an `InMemoryRunner` (no LLM — `RemoteA2aAgent` relays). First `run_async` → assert a **paused
  long-running function call** surfaces (`event.long_running_tool_ids` non-empty) carrying
  `a2a:task_id`/`a2a:context_id`. Resume: feed a `FunctionResponse` for that call as the next user
  turn → assert the returned event content carries the **gov-id-clean** `ExchangeTurn` payload.
- **Test C — port guard:** point `A2ABridgeClient` at the park-mode mock → assert it raises
  `BridgeParkedError` (not a generic failure, not a hang).
- If Test B hits an experimental-API wall, Tests A+C still lock the contract and guard; report the
  wall per adr-0009 C5 rather than forcing it.

### 5. Docs + tracker
- `agents/README.md`: note the native `RemoteA2aAgent` consumer + park/resume mode env/usage.
- `PLAN.md`: mark the first Sprint-1 bullet done — convert to `- [x]` with `_(done 2026-08-15; Plan:
  /home/boris/working/.claude/plans/s1-1-native-a2a-consumer.md)_`, and add a one-line scope note
  that the park is a mechanism tracer; the multi-turn `is_satisfied` Collect loop remains in the next
  bullet.
- Copy this plan to the repo at `.claude/plans/s1-1-native-a2a-consumer.md` (the /implement naming
  convention) and link it from PLAN.md.

## Verification

- `uv run pytest` — all green, including the untouched M0.6 round-trip (`test_round_trip.py`) and the
  new `test_native_consumer.py` (Tests A/B/C).
- `uv run ruff check` — clean.
- Manual (optional): `MOCK_BRIDGE_PARK=1 uv run python -m agents.mock_bridge`, confirm a first
  `message/send` parks at `INPUT_REQUIRED` with a non-empty status message and a resume completes.

## Out of scope (next PLAN.md bullet)
Multi-turn Collect loop, `is_satisfied` gate (`gov-id OR 2 distinct bills`), fixture document
arrivals, chase/timeout. PushNotificationConfig for weeks-scale wakeup stays Phase 3 (adr-0008).
