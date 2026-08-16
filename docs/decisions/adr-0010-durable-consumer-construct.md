# ADR-0010 — Durable consumer construct: native graph (`Workflow`)

- **Status:** Accepted
- **Date:** 2026-08-15
- **Supersedes (construct/wiring side):** the consumer *wiring* trajectory that accreted as same-day amendments on `docs/decisions/adr-0009-native-a2a-consumer.md` (M0 port removal → `transfer` sub-agent → `AgentTool` interim). ADR-0009 keeps the **native-consumer principle + wire vocabulary** (`RemoteA2aAgent`, `input-required` pause, `status.message` progress); **this ADR owns *how the consumer hangs off the caller* and *how state is restored*.**
- **Context:** `docs/decisions/adr-0009-native-a2a-consumer.md`, `docs/decisions/adr-0001-stack.md`, `docs/decisions/adr-0008-long-running-collection-lifecycle.md`, `wiki/bridge-a2a-consumer.md`, `wiki/bridge-collect.md`; installed `google-adk == 2.7.0` (`google/adk/agents/remote_a2a_agent.py`, `google/adk/agents/loop_agent.py`, `google/adk/workflow/…`), `a2a-sdk` 1.1.x.

## Context

ADR-0009 §1 settled *what* consumes the Bridge: the native `RemoteA2aAgent`. It deliberately left open *how* that agent hangs off the caller — a second, consequential choice, because it decides whether **reasoning control** returns to run the app's Sense-B "done" gate (`is_satisfied`, `wiki/bridge-collect.md`) after the Bridge returns its ledger.

That choice thrashed during M0→S1 (recorded, before consolidation, as four same-day amendments on ADR-0009): the M0 port was removed and the Bridge attached as a `transfer` sub-agent; S1-2 switched to a `BridgeAgentTool` (an `AgentTool`) so control returns as a tool result; S1-4 grew the multi-turn Collect loop on that `AgentTool`, threading the exchange `context_id` through session state. Reading the three installed ADK wirings settles the **durable** answer and makes the interim explicit.

The forcing fact: **`AgentTool` runs the wrapped `RemoteA2aAgent` in a fresh throwaway child session** (new `Runner` + `InMemorySessionService` per call). It gets control-return right, but only *in-turn*. That one fact is the root of every current workaround — `BridgeAgentTool`'s copied Runner boilerplate, the hand-threaded `context_id` (state is the only channel surviving an `AgentTool` call), the `skip_summarization=False` loop dependency — and it **structurally blocks native park/resume** (no durable session for a `LongRunningFunctionTool` pause to resume against). The fix is not a different call/return choice but a different **place for control to return to**: a graph whose nodes share one durable session.

## Decision

### 1. The durable consumer construct is `google.adk.workflow.Workflow` (native graph)

Service agents consume the Bridge as a node in a **native `Workflow` graph**, not via `AgentTool`, `transfer`, or `LoopAgent`. The three wirings, in order of durability (verified against installed ADK 2.7.0):

| Wiring | Control returns to run the gate? | Session across rounds | Native park/resume | Verdict |
|---|---|---|---|---|
| `sub_agents` + `transfer_to_agent` | **No** — one-way handoff; the sub-agent's output is the turn's final output (`transfer_to_agent` is a control-flow primitive, not a tool; a `RemoteA2aAgent` issues no transfer-back) | n/a | n/a | **rejected** for the loop |
| **`AgentTool`** | **Yes**, as a tool result | **fresh throwaway** per call | **impossible** | **interim** (M0/S1) |
| **native graph (`Workflow`)** | **Yes** — the graph *is* the control flow; the gate is a node | **shared, durable** — nodes get the parent `InvocationContext`; `RemoteA2aAgent` reuses its own `context_id` natively | **works** — `input-required` hits `ctx.should_pause_invocation`; the graph suspends and resumes from saved node state | **durable target** |

### 2. `Workflow`, not `LoopAgent`

`Workflow` (node/edge graph, `google.adk.workflow`) is public and **not** `@experimental`. `LoopAgent`/`SequentialAgent` are `@deprecated` **in favor of `Workflow`** (`loop_agent.py`) — building the durable path on the deprecated construct is day-one debt. `LoopAgent` is verified to do exactly what we need (shared session, `escalate` termination, pause propagation) and is retained as a **known-good fallback** only if the spike gates fail.

### 3. The general service-agent shape

Every service agent — Address, Benefits, RFP, any internal Bridge caller — is the same construct: a `Workflow` whose nodes are **(1) a `RemoteA2aAgent` collect node**, **(2) a deterministic Sense-B gate node** (`is_satisfied` for Address; the emergent-requirements decision for RFP) that branches back to collect or forward, and **(3) an `LlmAgent` presenter node** (routes/chases and renders the deliverable) — on one shared durable session. *The difference between demos is the nodes and the gate, not the graph kind.* Two invariants make this a shape, not a suggestion: the gate is a **deterministic pure function** (a model may never mint "done" — Sense B, `docs/lessons-learned.md` A3), and the graph sits **on top** of the LLM (presenter as a node) because **"`Workflow` cannot yet be used as an `LlmAgent` sub-agent"** (2.7.0).

### 4. Durable state restore: the webhook is a doorbell, not a restore

A weeks-scale park (ADR-0009 §2) only pays off if the consumer returns to the **same state** after a process death/restart. Source audit establishes that restore is **mostly platform-DEFAULT**; keep *restore* and *wake* separable:

- **DEFAULT (config swap, no custom code):** `DatabaseSessionService`/`VertexAiSessionService` (session state + event history, reloadable by `(app, user, session_id)`); `DatabaseTaskStore` (task + artifacts + `context_id` survive restart); `tasks/get`/`tasks/resubscribe`; peer `task_id`/`context_id` ride `event.custom_metadata`, auto-repopulated on resume; the Runner **auto-matches** a `FunctionResponse` to the paused `function_call_id` and rebuilds the invocation from persisted events; push-notification **sender** on the Bridge.
- **EXPERIMENTAL:** `ResumabilityConfig(is_resumable=True)` — the switch that makes a park survive a restart (`@experimental`, 2.7.0). Pin + seam-cover (ADR-0001 SDK-risk).
- **CUSTOM (small, mechanical — Phase 3):** a **webhook receiver** (a2a-sdk is sender-only; neither SDK ships a receiver; `adk web` can't host one) and a **`task_id`→session index** (no schema indexes a session by A2A `context_id`/`task_id`). The receiver builds the `FunctionResponse` and calls `runner.run_async(...)` — everything downstream is DEFAULT.

The webhook (`PushNotificationConfig`, ADR-0008) delivers only "task X changed" — neither the caller's state nor a resume. It is **necessary but not sufficient**; restore is the separate DEFAULT+EXPERIMENTAL mechanism above.

### 5. Migration and spike gates (S1-6)

Migration path is **`AgentTool` → `Workflow`**, never → `transfer`/`LoopAgent`. Two unknowns gate the commit to `Workflow` (S1-6 spike; `LoopAgent` fallback if either fails):

1. **`RemoteA2aAgent` (a non-`LlmAgent` `BaseAgent`) usable as a `Workflow` node** — only `@node`/`FunctionNode`/`LlmAgent`-as-node are confirmed in 2.7.0.
2. **`input-required` pause propagates + resumes *inside* a `Workflow`** — verified inside `LoopAgent`, not yet inside `Workflow`.

Durable park/resume across a restart (§4) needs only the DEFAULT stores + the EXPERIMENTAL switch and is testable with **no HTTP** (resume via `runner.run_async` manually) — that is S1-6. The webhook receiver + index (§4 CUSTOM) is Phase 3, only for legs that must outlive the process.

**Resolution (S1-6, realized — shipped on `Workflow`, not `LoopAgent`).** Both spike gates pass on `Workflow`: (1) a `RemoteA2aAgent` (non-`LlmAgent` `BaseAgent`) runs directly as a graph node — `BaseAgent` subclasses the workflow `BaseNode`; (2) an `input-required` pause propagates, resumes, and survives a process restart *inside* a `Workflow`. The Collect loop is a `Workflow` **conditional cycle** (`collect → gate`, `gate --[again]--> collect`, `gate --[done]--> present`): a conditional loop-back edge **does** re-enter and re-run the completed collect node — the graph validator *requires* loop-back edges to be routed, and the scheduler re-runs a re-triggered COMPLETED node with a fresh `NodeState` (`_workflow.py::_process_triggers`). The one `Workflow`-specific wrinkle: `RemoteA2aAgent`'s built-in resume detection assumes the resolved `FunctionResponse` is the *last* session event (`_create_a2a_request_for_user_function_response`), which the graph orchestrator breaks by appending a workflow event after it — so the send-path `RequestInterceptor` (`bridge_client.remote_consumer`) re-detects the pending resume and stamps the parked A2A `task_id`/`context_id` on the outbound message so the peer resumes the *same* task. `LoopAgent` was **not** taken; its deprecation risk does not apply to this path. Shipped: `agents/address/graph.py`, proven by `agents/tests/test_durable_graph.py` (incl. the headline restart-resume). See ADR-0012 and `docs/lessons-learned.md` A12.

## Rationale

- **The root problem is the session, not control-return.** `AgentTool`'s fresh throwaway session is what forces the workarounds and blocks park/resume; a shared durable session removes all of them at once. `Workflow` is the ADK-native form of "the loop + gate move to host orchestration" (Option B).
- **Deprecation is a hard signal.** `LoopAgent` deprecated-in-favor-of-`Workflow` means new durable code on `LoopAgent` is debt from commit one; `Workflow` is the supported surface.
- **The shape generalizes the reusability thesis.** ADR-0009 said "the difference between demos is the agent, not the Bridge"; this ADR sharpens it — the difference is the *nodes and the gate*, not the graph kind, so all service agents share one construct.
- **Restore is bought, not built.** Bounding the custom surface to a receiver + an index (everything else DEFAULT/EXPERIMENTAL) keeps ADR-0001's "prefer the platform-native construct" intact for durability too.

## Consequences / risks

- **The spike gates resolved in `Workflow`'s favor (S1-6, realized).** Both passed on `Workflow` (see §5 Resolution); the `LoopAgent` fallback was not taken, so its deprecation risk does not burden this path. The remaining `Workflow`-specific dependency is on the send-path interceptor re-detecting a resume under the graph's event ordering (a small, seam-covered adapter, not an SDK experimental surface).
- **`Workflow` cannot yet front an LLM.** The graph must sit on top (LLM as a node). If a future demo needs an LLM to *own* the loop with the graph behind it, revisit.
- **Interim debt is real but bounded.** Until S1-6, service agents run on `AgentTool` with the hand-threaded `context_id` and `skip_summarization=False`; these are known and are retired by the migration, not patched.
- **`ResumabilityConfig` is `@experimental`** — the one experimental surface the durable path leans on; pin and seam-cover (ADR-0001, `docs/lessons-learned.md` C5).

## Alternatives considered

- **Stay on `AgentTool` (in-turn loop).** Rejected as the target: fresh throwaway session blocks park/resume and forces the `context_id`/`skip_summarization` workarounds. Correct interim only.
- **`transfer` sub-agent.** Rejected for the loop: one-way; no post-Bridge reasoning step for the gate.
- **`LoopAgent` as the durable construct.** Rejected as the target (deprecated in favor of `Workflow`); retained as a known-good fallback behind the spike gates.
- **Build a custom durable session/pause layer.** Rejected: re-implements what persistent stores + `ResumabilityConfig` + the Runner's auto-match already provide (ADR-0001 forbids bespoke plumbing without a recorded justification; there is none here).

## Note

This ADR governs the **consumer construct/wiring and state restore**. It does not change ADR-0009's native-consumer principle or wire vocabulary (`RemoteA2aAgent`, `input-required`, `status.message`) — it *builds on* them. Lessons: `docs/lessons-learned.md` A12 (durable construct + the two "returns") and A13 (restore is DEFAULT; doorbell-not-restore). Build task: `PLAN.md` S1-6. Prose: `wiki/bridge-a2a-consumer.md`; deployment of the resume path (restore vs. wake on Cloud Run / Agent Engine) is `wiki/bridge-deploy-resume.md`.
