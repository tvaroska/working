# S1-6 — Durable graph consumer + park/resume spike (no HTTP)

> **Goal:** move the Collect loop off the in-turn `BridgeAgentTool` (fresh throwaway
> session → blocks native park/resume) onto a **native `google.adk.workflow.Workflow`
> graph on one shared, durable session**, and prove a parked address-agent leg survives
> a simulated process restart and resumes to the *same* state — **no webhook, no `adk web`**,
> resume driven manually via `runner.run_async(...)`.
>
> Decisions this executes: **ADR-0010** (durable consumer construct + state restore),
> ADR-0009 (native consumer + wire vocabulary), ADR-0001 (SDK-risk pins), ADR-0012
> (experimental-surface register). Lessons: `docs/lessons-learned.md` **A12** (durable
> construct; the two "returns") and **A13** (restore is DEFAULT; doorbell-not-restore).
> Prose: `wiki/bridge-a2a-consumer.md` ("Wiring: why the graph…" + "Durable state restore").

---

## 0. Context the implementer must not re-derive (source-verified against installed ADK 2.7.0 / a2a-sdk 1.1.x)

These were checked against the installed packages; they resolve the two spike gates and pin the exact APIs.

### Spike gate 1 — CONFIRMED by source: `RemoteA2aAgent` *can* be a `Workflow` node.
`BaseAgent.__mro__ == [BaseAgent, BaseNode, BaseModel, ABC, object]` — **`BaseAgent` subclasses `BaseNode`**, and `RemoteA2aAgent`/`LlmAgent` are `BaseNode` subclasses. `workflow/utils/_workflow_graph_utils.build_node` accepts any `BaseNode`, so a `RemoteA2aAgent` and an `LlmAgent` presenter both drop into a graph as nodes. Gate 1 is therefore de-risked *before writing code*; the remaining risk is purely runtime behavior (does the node send/return correctly across a loop-back edge), which the spike test exercises. **Still record the outcome** (ADR-0012 lists gate 1 as "pending").

### Spike gate 2 — genuinely unknown, must be proven at runtime: does an `input-required` pause **propagate + resume inside a `Workflow`**?
Verified inside `LoopAgent`, not yet inside `Workflow`. This is the load-bearing spike. If it fails → **fallback to `LoopAgent`** (§8).

### Construct = `google.adk.workflow.Workflow` (NOT `LoopAgent`; `LoopAgent`/`SequentialAgent` are `@deprecated`).
- Constructor: `Workflow(name=..., edges=[<EdgeItem>, ...])`. `edges` is a list of either `Edge(from_node=, to_node=, route=)` objects **or** chain tuples `(START, node_a, node_b, ...)`. Nodes are inferred from edges; do **not** pass `nodes=`. `START` is `google.adk.workflow.START`.
- **Conditional edges (gate → collect vs. finish):** a node emits a *route value* by setting `ctx.route = "<value>"` (property setter on `google.adk.agents.context.Context`, backed by `EventActions.route`). Match it with `Edge(from_node=gate, to_node=collect, route="not_done")` and `Edge(from_node=gate, to_node=presenter, route="done")`. `google.adk.workflow.DEFAULT_ROUTE` is the fallthrough sentinel. Unmatched routes end the branch (a warning is logged).
- **Function nodes:** decorate with `from google.adk.workflow import node`; `@node` gives a `FunctionNode`. Signature may take `ctx: Context` and/or state-bound params. Default `parameter_binding='state'` binds non-`ctx`/`node_input` params from `ctx.state` — **and `Workflow._validate_state_schema` raises `StateSchemaError` if a bound param isn't declared in `state_schema`.** To avoid a `state_schema` requirement, write the gate as `def gate(ctx: Context)` (only `ctx`, no state-bound params) and read state via `ctx.state` / events via `ctx.session`.
- **Run a Workflow:** `Runner` accepts `app=`, `agent=`, **or** `node=` (exactly one). A `Workflow` is a `BaseNode`, so pass it as `node=` **or** wrap it in an `App(root_agent=workflow, ...)` and pass `app=`. **Use the `App` path** — it is the only way to attach `resumability_config` (below).
- Composition constraint (2.7.0): **"`Workflow` cannot be used as an `LlmAgent` sub-agent"** — so the LLM presenter is a *node inside* the graph; the graph sits on top. Do not try to make the Workflow a tool/sub-agent of an `LlmAgent`.

### Durability wiring APIs (exact).
- **Consumer session (DEFAULT swap):** `from google.adk.sessions import DatabaseSessionService`; `DatabaseSessionService(db_url="sqlite:///<tmp>.db")`. **Requires `sqlalchemy` — NOT installed** (`google-adk[db]`). Must be added (§1).
- **Resumability (EXPERIMENTAL):** `from google.adk.apps import App, ResumabilityConfig`; `App(name=..., root_agent=<Workflow>, resumability_config=ResumabilityConfig(is_resumable=True))`. `ResumabilityConfig.is_resumable: bool = False` default. `@experimental` — pin + seam-cover (ADR-0001 / ADR-0012).
- **Mock Bridge task store (DEFAULT swap):** `from a2a.server.tasks import DatabaseTaskStore`; `DatabaseTaskStore(engine=<AsyncEngine>, create_table=True)`. **Requires `a2a-sdk[sql]` — NOT installed.** Build the engine with `from sqlalchemy.ext.asyncio import create_async_engine; create_async_engine("sqlite+aiosqlite:///<tmp>.db")`. `aiosqlite` **is** already present; `sqlalchemy` is not.
- **Resume with no HTTP:** feed a `FunctionResponse` (matching the paused `function_call.id`) to `runner.run_async(new_message=Content(parts=[Part(function_response=...)]))`. The Runner auto-matches it to the paused call and rebuilds the invocation from persisted events (see existing `tests/test_native_consumer.py::_drive_remote_agent` for the exact resume shape). Peer `task_id`/`context_id` ride `event.custom_metadata` and are auto-repopulated — **assert this; do not thread them manually.**

### What exists today (the interim being migrated)
- `agents/src/agents/address/agent.py` — `LlmAgent` with two tools: `BridgeAgentTool(bridge, skip_summarization=False, result_state_key=COLLECTION_STATUS_STATE_KEY)` and `check_completeness`. The LLM routes the loop.
- `agents/src/bridge_client/bridge_tool.py` — `BridgeAgentTool(AgentTool)`: copies `AgentTool.run_async` boilerplate, runs the `RemoteA2aAgent` in a **fresh `InMemorySessionService`** per call, extracts the `ExchangeTurn` from `inline_data` via `wire.extract_exchange_turn`, writes it + the exchange `context_id` (`EXCHANGE_CONTEXT_STATE_KEY`) to parent state. **This is what S1-6 retires.**
- `agents/src/bridge_client/remote_consumer.py` — `build_bridge_remote_agent(card_url, collect_request=...)` returns a `RemoteA2aAgent` with a send-path `RequestInterceptor` that (a) injects the structured `CollectRequest` JSON DataPart on fresh sends, (b) passes resume requests (truthy `task_id`) through unchanged, (c) stamps the threaded `context_id` from state. Reused as-is by the collect node; the state-threading branch becomes redundant (native context reuse) but is harmless — leave it.
- `agents/src/agents/address/satisfaction.py` — `is_satisfied(status) -> SatisfactionResult` (pure) and `check_completeness(tool_context)` (reads `state[COLLECTION_STATUS_STATE_KEY]`). Keep `is_satisfied` as the deterministic core; the gate **node** calls it.
- `agents/src/agents/mock_bridge/{executor,app,scenarios}.py` — stateful-per-context executor; `park=True` path: WORKING → hold → `INPUT_REQUIRED` (non-empty `status.message`) → resume(same task) → COMPLETED artifact. `create_app(..., park=, scenario=, hold_seconds=)` builds a Starlette app with `InMemoryTaskStore()`.
- `agents/src/bridge_client/wire.py` — `extract_exchange_turn(events)`, `request_to_message(...)`. `agents/tests/support/live_server.py` — `LiveMockServer(hold_seconds=, park=, scenario=)`.

---

## 1. Dependencies (do first)

Edit `agents/pyproject.toml` `[project].dependencies`:
- Change `"google-adk>=2.7.0,<3"` → `"google-adk[db]>=2.7.0,<3"` (pulls `sqlalchemy`).
- Change `"a2a-sdk[http-server]"` → `"a2a-sdk[http-server,sql]"` (pulls `sqlalchemy`; `aiosqlite` already present).
- Add `"aiosqlite"` explicitly if the `[sql]`/`[db]` extras don't already pin an async sqlite driver (verify after `uv lock`).

Then: `cd agents && uv lock && uv sync`. Commit the updated `uv.lock`. **The `test_scaffold.py` SDK-pin guard must still pass** (it asserts the `google-adk` version range — adding the `[db]` extra keeps the same range, verify).

CI note: `google-adk[db]` + `a2a-sdk[sql]` add `sqlalchemy` to the agents env; the S0.1 agents job re-runs `uv sync --locked` so no workflow change is needed, but confirm the job still resolves.

---

## 2. New file: the durable graph consumer

Create `agents/src/agents/address/graph.py` (the `Workflow` form of the address agent). This is the headline deliverable.

**Nodes:**
1. **collect node** = the `RemoteA2aAgent` from `build_bridge_remote_agent(card_url, name="document_bridge", collect_request=CollectRequest(party=PARTY, skill=SKILL))`. Used directly as a node (no `BridgeAgentTool` wrapper — that is the retirement). The interceptor still injects the structured request.
2. **gate node** = a `@node def gate(ctx: Context)`:
   - Extract the latest `ExchangeTurn` from the **shared session** events: `turn = extract_exchange_turn(ctx.session.events)` (reuse the wire helper; it scans for the `inline_data` DataPart the collect node emitted). Handle "no turn yet" defensively (treat as not-done).
   - Write it to `ctx.state[COLLECTION_STATUS_STATE_KEY]` (keeps parity with `check_completeness`'s contract and makes state assertions in the restart test trivial).
   - `result = is_satisfied(_coerce_status(turn))` (import `is_satisfied`, `_coerce_status` from `satisfaction.py`).
   - `ctx.route = "done" if result.done else "not_done"`.
   - *LLM-routes-code-decides invariant:* the gate is this deterministic node; **no model may set the route.** Keep it a pure `FunctionNode`.
3. **presenter node** = an `LlmAgent` (as a node) that renders the deliverable from `ctx.state[COLLECTION_STATUS_STATE_KEY]` (the accepted doc id(s) + fields). Reuse the existing address `INSTRUCTION` prose trimmed to "present the result" (the routing/chase instructions move into the graph edges, not the prompt). Set `output_key="address_result"` for parity with today.

**Graph edges:**
```
Workflow(
  name="address_collect_flow",
  edges=[
    (START, collect_node),
    (collect_node, gate_node),
    Edge(from_node=gate_node, to_node=collect_node, route="not_done"),
    Edge(from_node=gate_node, to_node=presenter_node, route="done"),
  ],
)
```
- Verify the loop-back edge (`gate --not_done--> collect`) re-runs the collect node within the same invocation on the shared session (this is part of spike gate 2 — pause/resume + re-entry inside a Workflow). If re-entry needs `rerun_on_resume` on the collect node, set it via `node(remote_agent, rerun_on_resume=True)` — decide empirically and record.

**Builder + App:** provide `build_address_graph(bridge_card_url=None, *, model=DEFAULT_MODEL) -> Workflow` mirroring `build_address_agent`'s card-URL/model resolution (reuse `_default_card_url`, `PARTY`, `SKILL`, `DEFAULT_MODEL` from `agent.py` — import, don't duplicate). Provide `build_address_app(...) -> App` that wraps the workflow with `ResumabilityConfig(is_resumable=True)`.

**Do NOT delete `agent.py` (the `AgentTool` interim) in this task** unless the spike fully passes AND all its tests are migrated. Preferred: land `graph.py` alongside, migrate `root_agent`/run-doc to the graph only after §5 is green, and leave a deprecation note. If the spike **fails** (fallback to `LoopAgent`), `agent.py` stays as the shipping path. Record the decision in the ADR-0012 update (§6).

---

## 3. Mock Bridge: optional DatabaseTaskStore

Make the mock's task store swappable so the durability demo is faithful (ADR-0010 §4 DEFAULT swap) and so a future test can restart the mock too.

In `agents/src/agents/mock_bridge/app.py::create_app`, add a param `task_store: TaskStore | None = None` (default → `InMemoryTaskStore()` as today). When a `DatabaseTaskStore` is passed, `DefaultRequestHandler` uses it unchanged. Add a helper (in a new `agents/src/agents/mock_bridge/stores.py` or inline in the test support) that builds `DatabaseTaskStore(engine=create_async_engine("sqlite+aiosqlite:///<path>"), create_table=True)`.

Extend `tests/support/live_server.py::LiveMockServer.__init__` with `task_store=None`, passed through to `create_app`.

**Scope note:** the *consumer*-restart proof (§5) keeps the mock server running across the simulated restart, so the mock's task survives regardless of store. The DatabaseTaskStore swap is required by the task text and makes the demo honest; cover it in a seam test (§5.3) but do not over-invest in a mock-restart scenario (that is Phase-3 territory).

---

## 4. Seams touched

Two of the six seams (`docs/lessons-learned` seam list; `bridge/src/bridge/seams`): **Sessions** (`InMemorySessionService → DatabaseSessionService`) and **Task store** (`InMemoryTaskStore → DatabaseTaskStore`). Both are exercised here **local-only** via SQLite (the GCP adapters — `VertexAiSessionService`, managed task store — are Sprint 2; the parametrized `gcp` adapter stays `pytest.skip` when creds absent, per S0.3). The mock→real and local→GCP swaps must remain **no-ops for the graph** — the only change is the session-service/task-store construction + the card URL. Assert parity is **terminal-outcome** (terminal reason + accepted-issuer set), never ledger-identical.

---

## 5. Tests to add — `agents/tests/test_durable_graph.py`

Follow the existing live-seam idiom (`LiveMockServer` + real sockets + `asyncio.run`, as in `test_native_consumer.py` / `test_collect_loop.py`). Use `tmp_path` for the SQLite files.

### 5.1 Spike gate 1 (record the outcome): `RemoteA2aAgent`-as-`Workflow`-node runs
Build the graph against a live mock (`GOV_ID_INSTANT`, instant terminal, `hold_seconds≈0.1`), run it once under an `InMemoryRunner`/`App`, assert it reaches the presenter and `state[COLLECTION_STATUS_STATE_KEY]` holds the `gov-id-clean` ledger. Proves a non-`LlmAgent` `BaseAgent` executes as a node and the gate reads its output.

### 5.2 Spike gate 2 + loop iteration (in-memory, no restart yet): pause/resume *inside* a Workflow
Live mock with `scenario=TWO_BILLS` (round 1 not-done → round 2 terminal) **and/or** `park=True`. Drive the graph; assert:
- the collect→gate→(not_done)→collect→gate→(done)→presenter path executes (loop-back edge works);
- if `park=True`, the invocation **pauses** on the `INPUT_REQUIRED` long-running call (find the paused `function_call` exactly as `test_native_consumer._find_paused_call` does) and **resumes** to COMPLETED when fed a `FunctionResponse` — *inside the Workflow*. This is the gate-2 proof.
- terminal accepted-issuer set matches the eval expectation (terminal-outcome parity).

### 5.3 The headline: durable park/resume across a simulated restart — **no HTTP**
1. Live mock (`park=True`, or `TWO_BILLS` with a park on round 1), served with a `DatabaseTaskStore` on a `tmp_path` sqlite file. **Keep the mock server up** for the whole test.
2. **Runner #1:** `App(root_agent=graph, resumability_config=ResumabilityConfig(is_resumable=True))`; `DatabaseSessionService(db_url="sqlite:///<tmp>/consumer.db")`; fixed `user_id`/`session_id`. Run the first turn; assert the invocation parked (paused long-running call present). Capture the paused `function_call.id` and the `session_id`.
3. **Simulate restart:** drop all references to Runner #1 and its `DatabaseSessionService` (`await runner.close()`), and construct a **fresh** `DatabaseSessionService(db_url=<same file>)` + fresh `Runner`/`App` pointing at the same graph + same db.
4. **Assert restore (before resuming):** load the session from the fresh service; assert `session.state[COLLECTION_STATUS_STATE_KEY]` (the ledger collected so far) and the exchange `context_id` survived, and that the peer A2A `task_id`/`context_id` are present in the persisted events' `custom_metadata` (auto-restored — **no manual threading**).
5. **Resume with no HTTP:** feed a `FunctionResponse(id=<paused id>, name=<paused name>, response={...})` to the fresh `runner.run_async(...)`. Assert the workflow **continues where it paused** — the gate runs again, `is_satisfied` advances, and the run terminates at the presenter with the terminal `ExchangeTurn` (gov-id-clean or two-bills terminal set).
6. Assert **terminal-outcome parity** with the same scenario run without a restart (same terminal reason + accepted-issuer set).

### 5.4 Keep existing tests green
`test_collect_loop.py`, `test_control_return.py`, `test_native_consumer.py`, `test_round_trip.py`, `test_mock_multiturn.py` must still pass (the `AgentTool` interim stays until fully migrated). If `root_agent` is switched to the graph, update `test_round_trip.py` accordingly and note it in PLAN.

Run: `cd agents && uv run pytest` (all green) and `uv run ruff check`.

---

## 6. Docs / decision-record updates (required — this task closes two spike gates)

- **ADR-0012** (`docs/decisions/adr-0012-experimental-surface-register.md`): flip the two "pending" `Workflow` spike gates to their proven outcome (gate 1 confirmed at build-node level + runtime; gate 2 = the §5.2/§5.3 result), and record whether we shipped `Workflow` or fell back to `LoopAgent`. Confirm `ResumabilityConfig` is now exercised in the seam suite (satisfies its `@experimental` "pin + seam-cover" requirement).
- **PLAN.md**: check off S1-6 with `_(done <date>; Plan: /home/boris/working/.claude/plans/S1-6-durable-graph-consumer.md)_`; add a scope note recording the construct chosen (`Workflow` vs `LoopAgent` fallback) and whether `BridgeAgentTool`/`EXCHANGE_CONTEXT_STATE_KEY` were retired or kept.
- **`wiki/bridge-a2a-consumer.md`**: move S1-6 from "remaining" to landed pointers (per repo rule, keep the spec target-first; progress lives in PLAN/git). Update the "Status" list.
- **`docs/lessons-learned.md`**: if the spike surfaced a non-obvious gotcha (e.g. loop-back re-entry needs `rerun_on_resume`, or resume inside a Workflow needs `App`-not-bare-`node`), append it to A12/A13.
- **Do NOT** reintroduce "✅ built"/test-count claims into `wiki/` (CLAUDE.md rule).

---

## 7. Acceptance criteria

- [ ] `agents/pyproject.toml` adds `google-adk[db]` + `a2a-sdk[sql]`; `uv.lock` regenerated; `test_scaffold.py` pin-guard still green.
- [ ] `agents/src/agents/address/graph.py` builds the address agent as a native `Workflow` (collect `RemoteA2aAgent` node → deterministic `is_satisfied` gate node with conditional route → `LlmAgent` presenter node) on one shared session; **not** `LoopAgent` (unless a spike gate failed → fallback, recorded).
- [ ] The gate node is a deterministic `FunctionNode` calling `is_satisfied`; no model can set the route (LLM-routes-code-decides preserved).
- [ ] Spike gate 1 outcome recorded: `RemoteA2aAgent` runs as a `Workflow` node.
- [ ] Spike gate 2 outcome recorded: `input-required` pause propagates + resumes **inside** the `Workflow`.
- [ ] `test_durable_graph.py::5.3` proves: a parked leg survives a simulated process restart (fresh `Runner` + fresh `DatabaseSessionService` on the same sqlite db), the session state (ledger + exchange `context_id`) and peer `task_id`/`context_id` (from `event.custom_metadata`, auto-restored) are intact, and resume via `runner.run_async(FunctionResponse)` continues the `is_satisfied` gate to the terminal outcome — **no webhook, no `adk web`**.
- [ ] Mock Bridge `create_app`/`LiveMockServer` accept an optional `DatabaseTaskStore`; the Sessions + Task-store seam swaps are exercised local-only (gcp adapter skips without creds).
- [ ] Terminal-outcome parity asserted (terminal reason + accepted-issuer set), not ledger-identical.
- [ ] `uv run pytest` fully green (new + all existing) and `uv run ruff check` clean.
- [ ] ADR-0012 + PLAN + `wiki/bridge-a2a-consumer.md` updated per §6.

---

## 8. Fallback (if spike gate 2 fails inside `Workflow`)

If `input-required` does **not** pause/resume cleanly inside a `Workflow` (or the loop-back edge can't re-enter the collect node after resume), fall back to **`LoopAgent`** (verified: shared session, `escalate` termination, pause propagation), accepting the `@deprecated` risk tracked under ADR-0001 SDK-risk. Shape: `LoopAgent` with sub-agents `[collect RemoteA2aAgent, gate]` where the gate escalates (`ctx.actions.escalate = True` / raises the escalation) when `is_satisfied.done`. Keep the same DatabaseSessionService + ResumabilityConfig durability wiring and the same §5.3 restart test — only the loop construct changes. **Record the fallback explicitly** in ADR-0012 + PLAN; do not silently ship the deprecated construct.

---

## 9. Gotchas (do not rediscover the hard way)

- **`a2a-sdk` messages are protobuf** — build/read with kwargs/`.field`; never `.model_dump()` on A2A types (`task_id` has no field presence → use truthiness). See `remote_consumer.py`.
- **Empty `status.message` is silently dropped** by ADK — the mock already attaches non-empty progress/park messages; keep it that way (A11).
- **`FunctionNode` state-schema trap:** any non-`ctx` param bound from state forces a `state_schema`; keep the gate `def gate(ctx: Context)` only, read via `ctx.state`/`ctx.session`.
- **Resumability needs the `App` path**, not a bare `node=`/`agent=` Runner — `resumability_config` lives on `App`.
- **The mock stays up across the consumer "restart"** in §5.3; only the consumer's Runner + DatabaseSessionService are rebuilt. Do not tear down `LiveMockServer` between the two turns.
- **`await runner.close()`** between Runner #1 and #2 so the sqlite handles flush before the fresh service reopens the file.
- **The interceptor's context-threading branch** (`EXCHANGE_CONTEXT_STATE_KEY`) becomes redundant once the shared session gives native `context_id` reuse — it is harmless; leave it and note the redundancy rather than ripping it out mid-spike.
- **Don't import `agents/` from `bridge/`** — unchanged here (all work is in `agents/`), but the gate node reuses `is_satisfied` from `agents.address.satisfaction`, which is fine (it's agent-side).
