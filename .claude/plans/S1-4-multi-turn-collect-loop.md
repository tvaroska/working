# S1-4 — Multi-turn Collect loop (durable exchange context across rounds)

## Context

PLAN.md Sprint-1 bullet **S1-4** (depends on S1-2, S1-3). Grow the M0/S1-2 one-shot
call-and-return into the **Collect loop where the app decides "done"**:

```
call document_bridge (AgentTool) → run is_satisfied gate → if not done, request the
outstanding proof again → repeat → terminate on satisfied and present the result.
```

with **one durable A2A exchange context spanning the loop's turns (no fresh exchange
per round)**.

This is the "LLM routes, code decides" loop: the model routes (calls the Bridge tool,
then the gate, decides whether to loop), the deterministic `check_completeness` gate
(S1-3) decides done. Design references already read: `wiki/bridge-collect.md` ("the loop
is the mechanism", "the app decides done"), `wiki/bridge-a2a-consumer.md` ("transfer vs.
call-and-return", "two mechanisms for long-running work"), `docs/decisions/adr-0009-*.md`,
`docs/decisions/adr-0008-*.md`.

## What already exists (verified — do not re-derive)

- **`BridgeAgentTool`** (`agents/src/bridge_client/bridge_tool.py`): an `AgentTool` over the
  `RemoteA2aAgent` that overrides `run_async` to scan **all** child events, extract the
  `ExchangeTurn` from the `inline_data` DataPart via `wire.extract_exchange_turn`, and
  return it as a validated JSON dict. `skip_summarization=True` by default. It forwards
  child `state_delta` to the parent (`tool_context.state.update(...)`) but **does not**
  currently write the returned turn to state.
- **`build_collect_request_interceptor(collect_request)`** and
  `build_bridge_remote_agent(card_url, *, collect_request=...)`
  (`agents/src/bridge_client/remote_consumer.py`): the send-path interceptor replaces the
  outbound parts with the `CollectRequest` JSON DataPart on a **fresh** send (no
  `task_id`), and **passes through unchanged on resume** (truthy `task_id`). On a fresh
  send it already preserves `a2a_request.context_id` when set:
  `if a2a_request.context_id: msg.context_id = a2a_request.context_id`.
- **`is_satisfied(CollectionStatus)` + `check_completeness(tool_context)`**
  (`agents/src/agents/address/satisfaction.py`): the authoritative gate. `check_completeness`
  reads the latest collection from `tool_context.state[COLLECTION_STATUS_STATE_KEY]`
  (`"collection_status"`), coerces `ExchangeTurn|CollectionStatus|dict`, returns
  `{done, outstanding, accepted_issuers}`. Never reads model args; never raises.
  **This is the single S1-3↔S1-4 coupling point: S1-4 must write the returned turn under
  `COLLECTION_STATUS_STATE_KEY`.**
- **Address agent** (`agents/src/agents/address/agent.py`): `build_address_agent` builds
  `bridge = build_bridge_remote_agent(card_url, name="document_bridge",
  collect_request=CollectRequest(party=PARTY, skill=SKILL))` and
  `tools=[BridgeAgentTool(bridge)]`, single tool, `output_key="address_result"`.
- **Mock** (`agents/src/agents/mock_bridge/executor.py`, `app.py`): returns the
  `gov-id-clean` ledger (which **satisfies** the gate in one round). Records
  `last_request_data` (first-turn inbound data part). `app.state.mock_executor` is exposed
  for seam assertions. Multi-turn *document arrivals* (a not-yet-satisfying ledger that
  fills over turns) are **S1-5**, not S1-4.
- **Baseline:** `uv run pytest` = **40 passed**. Do not regress.

### SDK facts verified by reading the installed `google-adk` 2.7.0 source

- **`RemoteA2aAgent._construct_message_parts_from_session` derives the outbound
  `context_id` by scanning prior session events for
  `custom_metadata["a2a:context_id"]`** (`remote_a2a_agent.py` ~678-749). The context id
  and task id are persisted on the agent's own emitted events (~845-863, 919-937). The
  interceptor then runs (`_run_async_impl` ~999-1009) and **its returned message is what
  gets sent** — so the interceptor can override `context_id`.
- **The `before_request` interceptor gets `(ctx: InvocationContext, a2a_request, params)`
  and `ctx.session.state` is live** (`a2a/agent/utils.py:65` reads `ctx.session.state`).
  The interceptor can read threaded state.
- **`BridgeAgentTool.run_async` creates a fresh `InMemorySessionService` + a brand-new
  child session per call**, seeding it from the parent's filtered state:
  `state_dict = {k:v for k,v in tool_context.state.to_dict() if not k.startswith("_adk")}`
  then `create_session(..., state=state_dict)`. **Consequence (the crux of S1-4):** the
  child session has **no prior events**, so `_construct_message_parts_from_session` finds
  no `a2a:context_id` and the RemoteA2aAgent would start a **new exchange every round**.
  Parent→child state seeding is the ONLY channel that survives across AgentTool calls.
- Writing `tool_context.state[key] = v` inside a tool propagates to the parent session via
  the tool's `function_response` event `state_delta` (standard ADK ToolContext behaviour).

## Design decision — what "one durable A2A task + context spans the loop" means here

There is a real tension to resolve explicitly (the S1-2 plan and `bridge_tool.py` docstring
flagged it as an open S1-4 concern): the loop is driven by **repeated `AgentTool` calls**,
and each call runs in a **fresh child session**, so native `LongRunningFunctionTool`
park/resume durability (which relies on the peer `task_id`/`context_id` persisting on the
*caller* session) **does not survive across AgentTool invocations**.

**Decision (record this in the code + docs):**

1. **The durable, load-bearing, testable invariant for S1-4 is the exchange *context*: the
   same A2A `context_id` is threaded through every round** — the loop continues **one
   exchange**, it does not mint a fresh exchange per round. We achieve this by threading the
   `context_id` through **session state** (the only cross-AgentTool channel) and having the
   interceptor stamp it on the outbound `message/send`.
2. **We deliberately do NOT reuse the A2A `task_id` across rounds in the park=False path.**
   Each round in S1-4 runs the mock's hold→`COMPLETED` path, so each `message/send` legitimately
   opens a new task **under the same context** (A2A: a context groups tasks; re-sending to a
   *completed* task_id is not valid). The "single task reused across turns" phrasing applies to
   the **parked (`input-required`) native pause/resume** timescale (adr-0009 §2), whose
   cross-AgentTool durability is a **separate, later concern** — call it out, do not solve it
   here (park=False throughout S1-4; the mock's park mode stays an S1-1 tracer / S1-5 growth).

State this reconciliation in the module docstrings and the adr-0009/wiki notes so a reviewer
does not read "no new task per round" as a regression.

## Ordered implementation steps

### Step 1 — `BridgeAgentTool` writes results + threads the exchange context to state
`agents/src/bridge_client/bridge_tool.py`

- Add a module constant (bridge-owned, so `bridge_client` imports nothing from `agents.*`):
  `EXCHANGE_CONTEXT_STATE_KEY = "bridge_exchange_context_id"`.
- Extend `__init__` with `result_state_key: str | None = None` (the key under which the
  returned `ExchangeTurn` dict is written for the gate; the address agent passes
  `COLLECTION_STATUS_STATE_KEY`). Keep it optional/`None` so existing S1-2 callers/tests are
  unchanged.
- In `run_async`, **after** `turn = extract_exchange_turn(events)` succeeds and is validated
  to `turn_dict`:
  - if `self.result_state_key`: `tool_context.state[self.result_state_key] = turn_dict`.
  - if `turn_dict.get("context_id")`:
    `tool_context.state[EXCHANGE_CONTEXT_STATE_KEY] = turn_dict["context_id"]`.
  These deltas flush to the parent session and are re-seeded into the next round's child
  session, which is how both the gate read (Step 3) and the context threading (Step 2) work.
- Update the module docstring: the "S1-4/S1-5 concern (not solved here)" paragraph now reads
  that S1-4 threads the **exchange context** across rounds via state (with the decision note
  above); native cross-AgentTool task_id/park-resume durability remains out of scope.

### Step 2 — Interceptor threads `context_id` from session state onto the outbound send
`agents/src/bridge_client/remote_consumer.py`

- `build_collect_request_interceptor(collect_request, *, context_state_key: str = EXCHANGE_CONTEXT_STATE_KEY)`
  (import `EXCHANGE_CONTEXT_STATE_KEY` from `.bridge_tool`, or define it in one place and
  import in both — keep a single source of truth).
- In `_before_request(ctx, a2a_request, params)`:
  - **Resume guard unchanged:** `if a2a_request.task_id: return a2a_request, params`.
  - Fresh send: build `msg = request_to_message(collect_request)` as today, then set the
    context id with this precedence:
    `threaded = ctx.session.state.get(context_state_key) if ctx and ctx.session else None`
    then `msg.context_id = threaded or a2a_request.context_id or None`.
    (Keep the a2a-sdk proto discipline: assign `.context_id`, never `.model_dump()`.)
- `build_bridge_remote_agent(...)`: add `context_state_key: str = EXCHANGE_CONTEXT_STATE_KEY`
  and pass it into `build_collect_request_interceptor` when `collect_request` is provided.
  Behaviour with `collect_request=None` stays unchanged (no config → S1-1 tests green).
- Gotcha: `ctx.session.state` is populated because `BridgeAgentTool` seeds the child session
  with the parent's filtered state (verified). `ctx` may be `None` in the hermetic interceptor
  unit test — guard with `if ctx and ctx.session`.

### Step 3 — Address agent: wire the loop (Bridge tool + gate tool + loop instruction)
`agents/src/agents/address/agent.py`

- Import `check_completeness` and `COLLECTION_STATUS_STATE_KEY` from
  `.satisfaction` (or via `agents.address`).
- Build the Bridge tool with the result-state key so the gate can read it:
  `BridgeAgentTool(bridge, result_state_key=COLLECTION_STATUS_STATE_KEY)`.
- Register **two** tools: `tools=[BridgeAgentTool(bridge, result_state_key=...), check_completeness]`.
  `check_completeness` is a plain function → ADK auto-wraps it as a `FunctionTool`; its
  `tool_context: ToolContext` param is ADK-injected (the model cannot pass the ledger — the
  "code decides" guarantee, preserved).
- Rewrite `INSTRUCTION` to the loop protocol (keep it short, deterministic-friendly):
  1. Call `document_bridge` to collect the address proof for the party.
  2. Call `check_completeness` to ask the **authoritative gate** whether the requirement is
     satisfied. You may never decide "complete" yourself.
  3. If `done` is `false`, call `document_bridge` **again** to chase the outstanding proof
     (`outstanding` tells you what is still needed). Repeat 2–3.
  4. When `done` is `true`, present the collected document id(s) and their structured fields.
- Keep `PARTY`, `SKILL`, `output_key`, `_default_card_url`, `run_once`, and the module-level
  `root_agent = build_address_agent()` (build stays side-effect-free — no network until a turn
  runs). Update `BRIDGE_TOOL_NAME`-related comments if wording changes.

### Step 4 — Scripted model that routes on the gate verdict (for hermetic loop tests)
`agents/tests/support/adk_stub.py`

- Keep the existing `ScriptedToolCallModel` (single call) for S1-2/round-trip tests — do not
  change it.
- Add a **`ScriptedLoopModel(BaseLlm)`** that genuinely routes on the authoritative gate,
  so the test exercises "LLM routes, code decides":
  - Inspect the incoming `llm_request.contents` for the most recent `function_response`.
    - No prior tool response yet → emit a `function_call` to `document_bridge` (args `{}`).
    - Last response was from `document_bridge` → emit a `function_call` to `check_completeness`.
    - Last response was from `check_completeness`:
      - if its payload `done` is `True` → emit final text (e.g. `"Address proof collected."`).
      - else → emit another `function_call` to `document_bridge` (chase again).
  - This makes the loop length data-driven by the gate, not a fixed script — the real
    behaviour under test.

### Step 5 — Mock: record context ids seen (minimal; do not build S1-5 doc arrivals)
`agents/src/agents/mock_bridge/executor.py`

- Add `self.context_ids_seen: list[str] = []` in `__init__`.
- In `execute`, on the **first-turn** branch (where `last_request_data` is captured), append
  `context.context_id` to `context_ids_seen`.
- Nothing else changes: the mock still returns `gov-id-clean` (satisfies in one round). The
  not-satisfying-then-satisfying document arrivals are S1-5. This capture is only so the live
  seam test can assert the **same context id** arrives on round 2.

### Step 6 — Tests
Add `agents/tests/test_collect_loop.py`; touch supports as above. All must pass under
`uv run pytest`.

1. **Interceptor context-threading unit test (hermetic, no sockets/ADK):**
   - State carries `EXCHANGE_CONTEXT_STATE_KEY = "ctx-abc"` → a fresh send (no `task_id`)
     returns a message with `context_id == "ctx-abc"` and the `CollectRequest` DataPart.
     (Build a tiny fake `ctx` with a `.session.state` dict; the interceptor only reads
     `ctx.session.state.get`.)
   - No state → `context_id` is `None`/empty (falls back).
   - Resume (`task_id` set) still passes through unchanged (regression guard for S1-2).

2. **`BridgeAgentTool` writes state (hermetic):** confirm that after a run the tool writes
   the turn under `result_state_key` and the context id under `EXCHANGE_CONTEXT_STATE_KEY`.
   Prefer to fold this into the live test (3) rather than mocking ADK internals; if done in
   isolation, drive one `BridgeAgentTool.run_async` against `LiveMockServer` with a real
   `ToolContext` and assert `tool_context.state` afterwards.

3. **Live durable-context seam test (real sockets, the headline S1-4 property):**
   - `with LiveMockServer(hold_seconds=0.2, park=False) as server:` — drive **two**
     `document_bridge` collect rounds, threading parent state between them the way ADK would
     (round 1's `tool_context.state` deltas seed round 2's call). Simplest robust harness:
     invoke `BridgeAgentTool(bridge, result_state_key="collection_status").run_async` twice
     using one persistent parent `ToolContext`/session (or a real `InMemoryRunner`-backed
     `ToolContext`), OR run the full LlmAgent with `ScriptedLoopModel` for two rounds.
   - Assert:
     - round 1 returns an `ExchangeTurn` with a non-empty `context_id` (= X);
     - after round 1 the parent state holds `collection_status` and
       `bridge_exchange_context_id == X`;
     - round 2's outbound carries context id X: `server.executor.context_ids_seen[0] ==
       server.executor.context_ids_seen[1] == X` (same exchange, no fresh context per round).

4. **Hermetic loop-orchestration test (the loop iterates + terminates on the gate):**
   Since the live mock satisfies in one round, prove the *iteration* logic deterministically:
   - Build an `LlmAgent` (via a small local `build_*` helper in the test, or reuse
     `build_address_agent` structure) whose Bridge tool is a **fake** async function tool
     that pops the next scripted `ExchangeTurn` and writes it to
     `tool_context.state[COLLECTION_STATUS_STATE_KEY]` (mimicking `BridgeAgentTool`'s state
     write), and whose second tool is the real `check_completeness`. Script the fake to
     return a **not-satisfying** ledger first (e.g. a single `bill-powerco-clean`, one issuer)
     then a **satisfying** one (add `bill-aquautil-clean` → two distinct issuers, or return
     `gov-id-clean`). Load these from `wiki/evals/address/expected.json` with the explicit
     `LedgerEntry` mapping used in `test_satisfaction.py`/`fixtures.py`.
   - Drive with `ScriptedLoopModel`. Assert: `document_bridge` (fake) called **twice**,
     `check_completeness` called each round, first gate verdict `done=False`, final `done=True`,
     and the agent terminates with a final text response (no infinite loop — cap the fake's
     scripted turns; if the model asks for a third collect, the fake should raise/stop the test).

5. **Regression:** `test_control_return.py`, `test_round_trip.py`, `test_satisfaction.py`,
   `test_native_consumer.py` (A/B), `test_address_agent.py`, `test_mock_bridge.py`,
   `test_contract.py`, `test_scaffold.py` all stay green. Note `test_address_agent.py`
   currently asserts `len(agent.tools) == 1` — **update it to `== 2`** and assert the second
   tool is the `check_completeness` gate (a `FunctionTool` named `check_completeness`), Bridge
   tool still first and a `BridgeAgentTool`, `sub_agents` still empty.

### Step 7 — Docs + tracker
- `docs/decisions/adr-0009-native-a2a-consumer.md`: append a short S1-4 note under the
  Amendment — the multi-turn loop landed; the exchange **context** is threaded across rounds
  via session state (interceptor stamps it); task_id is **not** reused in the park=False
  completing path (record the decision + reason). Do not contradict §2's park/resume model.
- `wiki/bridge-a2a-consumer.md`: flip the "Sprint 1 (remaining)" line — S1-4 loop landed;
  note the durable-context-via-state mechanism and the task-vs-context distinction.
- `wiki/bridge-collect.md`: optional one-line note that the Address loop is now wired
  agent-side (gate-routed) — keep it `📋`/status-neutral per CLAUDE.md (no "done"/test-count
  claims in the spec).
- `agents/README.md`: if it documents the single-tool wiring, update to the two-tool loop
  (document_bridge + check_completeness).
- `PLAN.md`: mark **S1-4** `- [x]` with
  `_(done <date>; Plan: /home/boris/working/.claude/plans/S1-4-multi-turn-collect-loop.md)_`.

## Seams touched

- **A2A consumer edge** (`bridge_client`): the send-path interceptor + `BridgeAgentTool` gain
  the context-threading/state-write behaviour. Covered by the seam suite (interceptor unit
  test + live durable-context test). Card-URL swap point (mock→real / local→GCP) is
  **unchanged** — still just a different Agent Card URL.
- No new managed-service boundary and **no new local/GCP adapter pair** — S1-4 is agent-side
  loop wiring plus the consumer's context threading. `check_completeness` (S1-3) is agent-side
  sense-B logic, not a seam. (The mock stays the permanent contract double; its multi-turn
  document arrivals are S1-5.)

## Gotchas (do not rediscover)

- **Fresh child session per AgentTool call wipes native context/task durability.** State
  seeding (parent→child) is the ONLY channel that survives — thread `context_id` through
  state, not through the RemoteA2aAgent's own event history.
- **Interceptor runs on resume too** — keep the `task_id` passthrough guard, or a resume
  would be rewritten into a fresh `CollectRequest` (breaks S1-2 test + any future park/resume).
- **`ctx` may be `None`** in the hermetic interceptor unit test — guard `ctx and ctx.session`.
- **a2a-sdk 1.x proto discipline:** set `msg.context_id = ...` / read `.task_id`; never
  `.model_dump()` on A2A types (contract Pydantic models still use `model_dump`).
- **`bridge_client` must never import `agents.*`** — keep `EXCHANGE_CONTEXT_STATE_KEY` defined
  in `bridge_client`; the *address* package supplies `COLLECTION_STATUS_STATE_KEY` to the tool
  via the `result_state_key` constructor arg (dependency points the allowed direction).
- **The gate is authoritative — the model must call it, never mint "done."** Do not add a
  `done` field to the model's own reasoning path; route on `check_completeness`'s verdict.
- **Only `Disposition.ACCEPTED` counts; two PowerCo variants = one issuer** (S1-3 invariant) —
  reuse it, don't reimplement, when building the not-satisfying-then-satisfying fixture ledgers.
- **Cap the loop in tests** so a model-stub bug can't spin forever (fake tool raises after its
  scripted turns are exhausted).
- **Live tests are socket-based and async** — reuse `LiveMockServer` + `asyncio.run`, small
  `hold_seconds` (0.2), as the existing seam tests do.

## Verification

- `uv run pytest` (fallback `.venv/bin/pytest`) from `agents/` — all green, incl. new
  `test_collect_loop.py` and the updated `test_address_agent.py`; baseline is 40 passing.
- `uv run ruff check` — clean.
- Manual (optional): `MOCK_BRIDGE_HOLD_SECONDS=2 uv run python -m agents.mock_bridge` +
  `uv run python -m agents.address` — the agent collects, runs the gate, and (against the
  gov-id-clean mock) terminates satisfied in one round, presenting the id + fields.

## Acceptance criteria

1. The address agent runs a **loop**: `document_bridge` (AgentTool call-and-return) → the
   authoritative `check_completeness` gate → if not done, chase the outstanding proof again →
   terminate on satisfied and present the result. The gate decides "done"; the model routes.
2. **`check_completeness` is wired as a second tool** and reads the collection from session
   state (written by `BridgeAgentTool` under `COLLECTION_STATUS_STATE_KEY`), never from model
   args. The model can never mint "complete."
3. **One durable exchange context spans the loop:** the same A2A `context_id` is threaded
   across rounds (via session state + the send-path interceptor), asserted live
   (`context_ids_seen` identical across two rounds). No fresh exchange per round. The
   deliberate non-reuse of `task_id` in the completing path is recorded (adr-0009 note).
4. The loop-iteration behaviour (not-done → chase → done → terminate) is covered by a
   deterministic test; the durable-context property by a live seam test.
5. Card-URL swap point unchanged; S1-1 (`test_native_consumer.py` A/B), S1-2, S1-3 stay green;
   full suite + ruff green.
6. adr-0009 / `wiki/bridge-a2a-consumer.md` updated (loop landed, context-via-state mechanism,
   task-vs-context distinction); PLAN.md S1-4 marked done. No premature "done"/test-count
   claims added to the `wiki/` spec (CLAUDE.md).

## Out of scope (later bullets)

- **S1-5** — mock multi-turn *document arrivals* (a ledger that fills across turns), faked
  chase/timeout, distinct-issuer bill fixtures, growing the `INPUT_REQUIRED` park/progress
  tracer into the permanent multi-turn contract double. (S1-4 only records `context_ids_seen`;
  it does not add turn-keyed document fixtures.)
- Native `LongRunningFunctionTool` park/resume **durability across AgentTool calls** (fresh
  child session limitation) — parked (weeks-scale) timescale; `PushNotificationConfig` wakeup
  (Phase 3, adr-0008).
- Real Gemini extraction, disposition/classification/canonicalization inside a real Bridge
  (there is no `bridge/` yet), frontend, GCP/Terraform.
```
