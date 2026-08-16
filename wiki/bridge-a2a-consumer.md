---
type: atom
related:
  - "[[bridge-a2a-edge]]"
  - "[[bridge-adk]]"
  - "[[bridge-long-running]]"
  - "[[bridge-collect]]"
  - "[[bridge-collect-scenarios]]"
tags: [bridge]
status: draft
updated: 2026-08-15
---

# A2A Consumer (calling the Bridge)

> The other side of the [[bridge-a2a-edge|A2A edge]]: how a servicer's (or processing) agent **consumes** the Bridge over canonical A2A. The principle is the same as everywhere else — **prefer the platform-native construct** ([[bridge-adk]]). For an ADK agent that calls another A2A agent, that construct is **`RemoteA2aAgent`**, not a hand-rolled A2A client. Decisions: `adr-0009` (native consumer + wire vocabulary) and `adr-0010` (durable construct/wiring + state restore).

> **This is not the deferred outbound client.** "Bridge-as-client" (the Bridge *dialing out* to counterparties, Agent-Card discovery — Phase 4, [[bridge-a2a-edge]]) is a different direction. Here it is *our* agent calling the Bridge inbound — the pull spine the core is built around.

## The native construct

An agent consumes the Bridge by instantiating **`RemoteA2aAgent`** against the Bridge's [[bridge-a2a-edge|Agent Card]]. It resolves the card, manages the A2A client, converts `Message`/`Task`/`Part` to ADK events, and — crucially — maps the A2A task lifecycle onto ADK's own pause/resume. We hand-roll none of that.

| Concern (consumer side) | ADK-native construct | Not this |
|---|---|---|
| Calling another A2A agent | **`RemoteA2aAgent`** (card-configured) | a hand-rolled A2A client + `tasks/get` poll loop wrapped in a `FunctionTool` |
| Awaiting a long collection | native pause on `input-required` (→ `LongRunningFunctionTool`) | a blocking poll loop that holds the caller's turn |
| Learning of progress | streamed `TaskStatusUpdateEvent` (rendered as *thought*) | a bespoke status side-channel |

The reusability thesis is unchanged — *the difference between demos is the agent, not the Bridge* ([[bridge|core vs demos]]). Each demo points a `RemoteA2aAgent` at the same unchanged Bridge card; the mock→real and local→GCP swaps are a **different card URL**, not different agent code.

## Service-agent architecture (the general shape)

`RemoteA2aAgent` is *what* consumes the Bridge; the **target shape of the whole agent** is the same for every service agent — Address, Benefits, RFP, and any internal agent that calls the Bridge (`adr-0010`). The reusability thesis cuts one level deeper: the difference between demos is the **nodes and the gate**, not the graph *kind*. Every service agent is:

> a **`Workflow`** (native graph) whose nodes are **(1) a `RemoteA2aAgent` collect node** (calls the Bridge over canonical A2A), **(2) a deterministic gate node** (the agent's Sense-B "done" function — `is_satisfied` for Address; the mutating-requirements decision for RFP), branching back to collect or forward, and **(3) an `LlmAgent` presenter node** (routes/chases and renders the deliverable) — all on **one shared, durable session**.

What varies per demo, and what doesn't:

| Fixed across all service agents | Varies per demo |
|---|---|
| Graph kind: `Workflow` (LLM as a *node*, not a front) | The gate function (Address `is_satisfied` vs. RFP emergent policy) |
| Collect node: `RemoteA2aAgent` against the Bridge card | The chase/route prose in the presenter node's instruction |
| Sense-A/Sense-B split ([[bridge-collect]]): Bridge dispositions, the agent gate decides "done" | How much the skill pins up front (bounded Address → emergent RFP) |
| One durable session; `context_id` reused natively; park/resume via `input-required` | The mock→real / local→GCP swap is *only* a different card URL |

Two invariants make this a *shape*, not a suggestion: the gate node is a **deterministic pure function** (a model may never mint "done" — Sense B, [[bridge-collect]]), and the graph sits **on top** of the LLM (the presenter is a node) because "`Workflow` cannot yet be used as an `LlmAgent` sub-agent" (`google-adk` 2.7.0).

## Wiring: why the graph, and not transfer or `AgentTool`

`RemoteA2aAgent` is *what* consumes the Bridge; **how it hangs off the caller** is a second, consequential choice, because it decides whether **reasoning control** comes back to run the gate. The [[bridge-collect|Collect]] loop's completeness decision (**`is_satisfied` — the app owns "done"**, Sense B) has to run *in the caller, after the Bridge returns its ledger*, then chase the next proof or stop. Three wirings, in order of durability (verified against installed ADK 2.7.0):

| Wiring | Control returns to run the gate? | Session across rounds | Native park/resume | Status |
|---|---|---|---|---|
| `sub_agents` + `transfer_to_agent` | **No** — one-way handoff; the sub-agent's output is the turn's final output (`transfer_to_agent` is a control-flow primitive, not a tool; a `RemoteA2aAgent` issues no transfer-back) | n/a | n/a | rejected for the loop |
| **`AgentTool`** (today) | **Yes**, as a tool result | **fresh throwaway** per call | **impossible** | interim (M0/S1) |
| **native graph** (`Workflow`) | **Yes** — the graph *is* the control flow; the gate is a node | **shared, durable** — nodes get the parent `InvocationContext`; `RemoteA2aAgent` sees its own prior event and reuses the `context_id` natively | **works** — an `input-required` pause hits `ctx.should_pause_invocation`, the loop suspends and resumes from saved state | **landed (S1-6)** — `agents/address/graph.py` |

**The root problem is the session, not control-return.** `AgentTool` gets control-return right but runs the Bridge in a **fresh throwaway child session** (new `Runner` + `InMemorySessionService` per call). That single fact forces every current workaround — `BridgeAgentTool`'s copied Runner boilerplate, the hand-threaded `context_id`, the `skip_summarization=False` loop dependency — and structurally blocks native park/resume (no durable session for a `LongRunningFunctionTool` pause to resume against). The fix is not a different call/return choice but a different **place for control to return to**: a graph whose nodes run on one shared, durable session.

Two ADK facts fix the construct (`adr-0010`):

- **`Workflow` (node/edge graph, `google.adk.workflow`) is the go-forward API and is *not* `@experimental`.** `LoopAgent`/`SequentialAgent` are now `@deprecated` **in favor of `Workflow`** (`loop_agent.py`), so the durable design *targeted* `Workflow` — **and shipped on it (S1-6).** The Collect loop is a `Workflow` conditional cycle (`collect → gate`, `gate --[again]--> collect`, `gate --[done]--> present`); a routed loop-back edge **does** re-enter and re-run the completed collect node (the graph validator *requires* loop-back edges to be conditional; `_workflow._process_triggers` re-runs a re-triggered COMPLETED node with a fresh `NodeState`). An earlier attempt fell back to `LoopAgent` on a *misdiagnosis* — that the scheduler fast-forwards any COMPLETED node (`check_interception` Case 1), so the loop never iterates — which was **empirically refuted** (Case 1 is scoped to **dynamic** `ctx.run_node()` nodes, not static-graph loop-backs). `LoopAgent` was **not** taken; no deprecation risk on this path.
- **The two S1-6 spike gates, resolved:** (1) a `RemoteA2aAgent` (a non-`LlmAgent` `BaseAgent`) runs correctly as a `Workflow` node (`BaseAgent` subclasses the workflow `BaseNode`) — **confirmed** (load-bearing detail: its `ExchangeTurn` artifact must be emitted `last_chunk=True` or the *partial* event streams but is never persisted to the shared session, so the gate can't read it — [[bridge-adk|lessons A12]]); (2) an `input-required` pause propagates/resumes cleanly, iterates the conditional loop, **and survives a process restart** — confirmed **inside a `Workflow`**. The one `Workflow`-specific wrinkle: `RemoteA2aAgent`'s resume detection assumes the resolved `FunctionResponse` is the *last* session event, which the graph orchestrator breaks by appending a workflow event after it — so the send-path `RequestInterceptor` re-detects the pending resume and stamps the parked A2A `task_id`/`context_id` to resume the same task. The composition constraint still holds: **"`Workflow` cannot yet be used as an `LlmAgent` sub-agent"** — so a graph sits **on top** (LLM as a *node*, e.g. a presenter), not behind an LLM "front".

Only `ResumabilityConfig` (the persistent-checkpoint half) is `@experimental` — see [[#Durable state restore — what ships vs. what we build]]; S1-6 now seam-covers it. The migration path was **`AgentTool` → graph**; this is the concrete shape of **S1-6** in `PLAN.md`.

**Current state.** S1-6 landed the durable graph (`agents/address/graph.py`) as a `Workflow` conditional cycle on one shared, durable session (`DatabaseSessionService` + `DatabaseTaskStore` + `ResumabilityConfig`), proven to park at `input-required` and resume to the same state across a process restart with no HTTP. It lands **alongside** — not replacing — the interim `AgentTool` wiring in `agent.py`: the Bridge is still also available as a `BridgeAgentTool` (an `AgentTool` over `RemoteA2aAgent`) where control returns with the `ExchangeTurn` as a tool result, the structured `CollectRequest` is restored on the send path by a `task_id`-guarded `RequestInterceptor`, and the multi-turn loop threads one durable exchange `context_id` through session state (each `AgentTool` call runs a fresh child session). `BridgeAgentTool` + the hand-threaded `context_id` state key are **kept**, not retired. Build history: `PLAN.md` (M0.x superseded; S1-2/S1-4/S1-6 landed); rationale: `adr-0010`.

## Two mechanisms for long-running work

A collection runs for [[bridge-long-running|days or weeks]]. `RemoteA2aAgent` supports that through two standard mechanisms, and the **Bridge's task status is what selects which one the caller gets**:

1. **Hold and wait (seconds → minutes).** While connected, the caller consumes the task's update stream; `submitted`/`working` states surface as ADK *thought* events (progress), never the final answer. Bounded by the client timeout (ADK default 600s). Fine for the M0 ~10s hold; **cannot** span weeks.
2. **Pause and resume (hours → weeks, zero compute).** When the Bridge parks awaiting an external event, its task returns **`input-required`** (or `auth-required` for a credential blocker). `RemoteA2aAgent` turns that into a **`LongRunningFunctionTool` pause**: the caller's invocation *ends* (zero compute), the peer `task_id` + `context_id` persist on the [[bridge-aggregate-model|session]], and a later `FunctionResponse` resumes to the *same* task. This is the **same** native durability the Bridge already uses for [[bridge-adk|HITL]] — now reused across the caller↔Bridge edge for free. (A real park/resume needs the graph wiring above; `AgentTool`'s throwaway session cannot host it.)

## Waiting is `input-required` — and the edge already emits it

Mechanism 2 needs the Bridge to express "parked, resume later" as **`input-required`**, not a prolonged `WORKING`. The [[bridge-a2a-edge|A2A edge]] **already does this**: disposition maps a not-yet-complete collection to task status the ordinary way (`_status_for`: a `PENDING` item → `INPUT_REQUIRED`, otherwise `COMPLETED`). So the consumer change is small — **treat `INPUT_REQUIRED` as a resumable pause, not a failure.** (The M0 tracer-bullet client deliberately treats it as terminal-failure because M0 is single-turn; that inverts at adoption — see M0 note.)

## Progress is `TaskStatusUpdateEvent.status.message`

Live progress rides the standard streaming event: a **`TaskStatusUpdateEvent` carrying a non-empty `status.message`** over `message/stream`. `RemoteA2aAgent` renders it as a thought event.

- **`a2a-sdk` 1.x gotcha:** the SDK carries an always-present *empty* proto `Message`; ADK collapses it to `None` and only surfaces a status update when a **real, non-empty** `Message` is attached. **An empty `status.message` is silently dropped** — mock and real Bridge must attach real parts.

## Timescales compose

| Timescale | Mechanism | Wire |
|---|---|---|
| seconds–minutes, connected | hold + streamed status | `message/stream`, `TaskStatusUpdateEvent` |
| hours–weeks, idle | pause + resume | `input-required` → `LongRunningFunctionTool`; woken by push |
| after disconnect | re-attach / snapshot | `tasks/resubscribe`, `tasks/get` |
| weeks-scale wakeup | callback | `PushNotificationConfig` (Phase 3, `adr-0008`) |
| terminal | deliverable | `ExchangeTurn` artifact on `COMPLETED` |

## Durable state restore — what ships vs. what we build

A weeks-scale pause (mechanism 2) only pays off if the caller can **come back to the same state** after its process has died and restarted. That restore is mostly **already in the platform** — the custom surface is small and well-bounded (full breakdown + rationale in `adr-0010` §4; source-verified against `google-adk` 2.7.0 + `a2a-sdk`).

The webhook is a **doorbell, not a restore**: `PushNotificationConfig` delivers only "task X changed" — it neither carries the caller's state nor puts the agent back where it paused. Restore is a *separate* mechanism (persistent stores + resumability); the wake signal is *necessary but not sufficient*.

- **DEFAULT (config swap):** `DatabaseSessionService`/`VertexAiSessionService` (session state + event history); `DatabaseTaskStore` (task + artifacts + `context_id`); `tasks/get`/`tasks/resubscribe`; peer ids ride `event.custom_metadata`, auto-repopulated on resume; the Runner auto-matches a `FunctionResponse` to the paused call; push-notification **sender** on the Bridge.
- **EXPERIMENTAL:** `ResumabilityConfig(is_resumable=True)` — the switch that makes a park survive a restart (`@experimental`, 2.7.0; pin + seam-cover, [[bridge-adk]] SDK-risk).
- **CUSTOM (Phase 3):** a **webhook receiver** (a2a-sdk is sender-only; `adk web` can't host one) + a **`task_id`→session index**; the receiver then calls `runner.run_async(...)` and everything downstream is DEFAULT.

**Consequence for sequencing:** durable park/resume across a restart needs only the DEFAULT stores + the EXPERIMENTAL switch — **no HTTP, testable by resuming via `run_async` manually.** That work (S1-6) de-risks the webhook path, which adds only the two CUSTOM pieces and only when a leg must outlive the process.

## M0 note — the port was removed; the consumer is now native

The [[bridge-collect|Collect]] tracer bullet (M0) originally consumed the Bridge through a hand-rolled `BridgeClient` port + `A2ABridgeClient` (a blocking `message/send` → `tasks/get` poll loop) wrapped in a `FunctionTool`. Once the wire contract was validated the port was **removed** (not merely tracer-bullet-only); the pure A2A wire helpers survive in `bridge_client/wire.py`. Sprint 1 grows the Collect loop against the native consumer. The full wiring trajectory (port removal → transfer → `AgentTool` interim → `Workflow` target) is recorded in `adr-0010`.

## Status

- **Decided (`adr-0009`):** `RemoteA2aAgent` is the canonical consumer; waits are `input-required` (native pause), progress is `TaskStatusUpdateEvent.status.message`, integration-extension mode pinned (`use_legacy=True` until validated).
- **Decided (`adr-0010`):** the durable construct is a native graph (service-agent shape above); `AgentTool` is the interim; state restore is mostly DEFAULT. Migration `AgentTool → graph` = **S1-6**, which was behind two spike gates — **now resolved: both pass on `Workflow`, so the graph shipped as a `Workflow` conditional cycle** (the `LoopAgent` fallback was not taken; the "cannot re-enter a completed node" claim was a refuted misdiagnosis) (`adr-0012`).
- **Committed / already in the edge:** `_status_for` maps a pending collection → `INPUT_REQUIRED` ([[bridge-a2a-edge]]); native HITL pause/resume ([[bridge-adk]]).
- **Landed (S1-2/S1-3/S1-4/S1-5):** native consumer as a `BridgeAgentTool` call-and-return; `CollectRequest` restored via a `task_id`-guarded interceptor; the authoritative `check_completeness` gate; the multi-turn Collect loop threading one durable exchange `context_id` across rounds; the mock grown into the multi-turn contract double. Details in `PLAN.md` + `adr-0010`.
- **Landed (S1-6):** the durable graph consumer (`agents/address/graph.py`) — a `Workflow` conditional cycle (`RemoteA2aAgent` collect node → deterministic `is_satisfied` gate → present, with a routed `gate --[again]--> collect` loop-back) on one shared, durable session; proven to park at `input-required` and resume to the same state across a process restart with no HTTP, via `DatabaseSessionService` + `DatabaseTaskStore` + `ResumabilityConfig`. A send-path interceptor re-detects the resume under the graph's event ordering (`RemoteA2aAgent`'s own last-event heuristic misses it). Lands alongside the `AgentTool` wiring (both kept). Details in `PLAN.md` + `adr-0012`.
- **Risk:** `RemoteA2aAgent` is `@a2a_experimental` and `ResumabilityConfig` is `@experimental` in `google-adk` 2.7.0 — pin and cover in the shared seam suite (`docs/decisions/adr-0001-stack.md`).

## Related
- [[bridge-a2a-edge|A2A edge]] (server side), [[bridge-adk|running on ADK]], [[bridge-long-running|long-running collection]], [[bridge-collect|Collect]], [[bridge-collect-scenarios|Collect scenarios]] (rejection · delays · keeping context)
- **Decision records:** `docs/decisions/adr-0009-native-a2a-consumer.md` (native consumer + wire vocabulary) · `docs/decisions/adr-0010-durable-consumer-construct.md` (durable construct + state restore)
