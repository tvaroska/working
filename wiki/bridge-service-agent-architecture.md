---
type: atom
related:
  - "[[bridge-a2a-consumer]]"
  - "[[bridge-adk]]"
  - "[[bridge-collect]]"
  - "[[bridge-long-running]]"
  - "[[bridge-aggregate-model]]"
tags: [bridge, reference-architecture]
status: draft
updated: 2026-08-15
---

# Service-Agent Reference Architecture

> The **reusable target shape for any agent that consumes the Bridge** — Address today, Benefits and RFP next, and any internal servicer agent later. This is the pattern to instantiate for a new use case; [[bridge-a2a-consumer]] covers the *consumer construct* (`RemoteA2aAgent`) in depth, and this atom is the *whole-agent* shape built around it. Decision records: `adr-0009` (native consumer + wire vocabulary), `adr-0010` (durable construct + state restore), `adr-0012` (resolved spike gates). Reference instance: `agents/src/agents/address/graph.py`.

> **Reusability thesis** ([[bridge|core vs demos]]): *the difference between demos is the agent, not the Bridge* — and one level deeper, **the difference between service agents is the nodes and the gate, not the graph *kind***. Every service agent is the same graph; only the collect target's skill, the gate function, and the presenter vary.

## The shape

A service agent is a **`google.adk.workflow.Workflow`** (native node/edge graph) running on **one shared, durable session**, with three nodes wired as a **conditional cycle**:

```
        START
          │
          ▼
   ┌──────────────┐        gate --[again]--> collect        (loop-back edge:
   │ collect node │ ◄─────────────────────────────┐         re-enters the
   │ RemoteA2aAgent│                               │         COMPLETED node)
   └──────┬───────┘                                │
          │ (ExchangeTurn artifact, last_chunk=True)
          ▼                                        │
   ┌──────────────┐   not done (route=again) ──────┘
   │  gate node   │
   │ deterministic│
   │ is_satisfied │
   └──────┬───────┘
          │ done (route=done)
          ▼
   ┌──────────────┐
   │ present node │  → graph output (code today; swap an LlmAgent in
   └──────────────┘    for a natural-language summary)
```

1. **Collect node — `RemoteA2aAgent`.** The platform-native Bridge consumer, run *directly* as a graph node (no `AgentTool` wrapper — `BaseAgent` subclasses the workflow `BaseNode`). It sends a structured `CollectRequest` over canonical A2A and relays the Bridge's `ExchangeTurn`. A parked collection surfaces as a `LongRunningFunctionTool` pause. Built by `bridge_client.build_bridge_remote_agent(card_url, ...)`; `rerun_on_resume=True` so a parked leg resumes mid-flight rather than being fast-forwarded.
2. **Gate node — deterministic, code decides.** A code-only `FunctionNode` (no model) that reads the latest collected `ExchangeTurn` back off the *shared* session, records it to state, runs the agent's authoritative **Sense-B "done" function**, and sets `ctx.route` to loop back (`again`) or advance (`done`). This is the *LLM routes, code decides* invariant ([[bridge-collect]]): **a model may never mint "done".** A round ceiling forces `done` after N rounds so a non-terminating scenario fails fast (replaces `LoopAgent.max_iterations`).
3. **Present node — the deliverable.** Exposes the terminal `ExchangeTurn` as the graph's output. **Pluggable:** the reference instance uses a deterministic *code* node (pass-through of the terminal turn); drop an **`LlmAgent` in here** for a natural-language summary. The routing decision has already happened in the gate, so the presenter never routes — this is why an LLM here is safe.

The cycle is `START → collect`, `collect → gate`, `gate --[again]--> collect` (the conditional loop-back), `gate --[done]--> present`.

## What is fixed, what varies

| Fixed across every service agent | Varies per use case |
|---|---|
| Graph *kind*: `Workflow` conditional cycle | The **gate function** (Address `is_satisfied` vs. RFP's emergent-requirements policy) |
| Collect node: `RemoteA2aAgent` against the Bridge card | The **skill / `CollectRequest`** the collect node sends |
| Sense-A/Sense-B split ([[bridge-collect]]): Bridge dispositions, the agent's gate decides "done" | How much the skill pins up front (bounded Address → emergent RFP) |
| One shared, durable session; `context_id` reused across rounds | The **presenter** (code pass-through vs. `LlmAgent` summary) |
| Park/resume via `input-required`; the mock→real / local→GCP swap | The mock→real / local→GCP swap is **only a different card URL** |

## The invariants that make this a *shape*, not a suggestion

- **LLM routes, code decides.** The gate is a deterministic pure function; a model never mints the completeness verdict ([[bridge-collect]], `is_satisfied`).
- **The graph sits *on top* of the LLM.** `Workflow` cannot yet be an `LlmAgent` sub-agent (`google-adk` 2.7.0), so the LLM appears **as a node** (the presenter), never as a front the graph hides behind.
- **One shared, durable session.** Every node runs on the parent `InvocationContext`; the collected ledger, exchange `context_id`, and peer A2A `task_id`/`context_id` (carried in `event.custom_metadata`) all live in the durable session store. This is what makes park/resume-across-restart possible — and it is exactly what the retired `AgentTool` wiring could not provide (its fresh throwaway child session per call structurally blocked native park/resume — [[bridge-a2a-consumer]], lessons A12).
- **`bridge/` never imports `agents/`.** The gate's canonicalization/disposition parity with the core Bridge holds by the shared seam suite, not by import.

## Durability: park, restart, resume — no HTTP

A collection runs for [[bridge-long-running|days or weeks]]. When the Bridge parks awaiting an external event its task returns **`input-required`**, which `RemoteA2aAgent` turns into a `LongRunningFunctionTool` pause: the invocation *ends* (zero compute), and a later `FunctionResponse` resumes the *same* task. Because the whole graph is on one durable session, a parked leg **survives a process restart** and resumes to the same state with **no webhook and no `adk web`**:

- **Sessions seam** → `DatabaseSessionService` (session state + event history).
- **Task store seam** → `DatabaseTaskStore` (task + artifacts + `context_id`).
- **`ResumabilityConfig(is_resumable=True)`** on the `App` — the switch that makes a park survive a restart. (`@experimental` in 2.7.0 — pin + seam-cover, `adr-0012`.)

Resume is proven by feeding the matching `FunctionResponse` to `runner.run_async` on a *fresh* `Runner` pointed at the same database — no HTTP. This de-risks the Phase-3 webhook, which adds only the *wake path* (a receiver + a `task_id`→session index); restore is already delivered here (`adr-0010` §4, lessons A13).

## Gotchas when you instantiate this (source-verified, `google-adk` 2.7.0)

- **Emit the collected artifact `last_chunk=True`.** `RemoteA2aAgent` marks an artifact event `partial = not last_chunk`; a *partial* event streams to the live caller but is **never persisted** to the shared session — so the gate reading `ctx.session.events` won't see it. The Bridge must flag even a partial (collected-so-far) ledger terminal (lessons A12).
- **The `Workflow` resume-detection wrinkle.** `RemoteA2aAgent` detects a resume only when the resolved `FunctionResponse` is the *last* session event — but the graph orchestrator appends a workflow event after it, so the remote agent misses the resume, re-parks, and opens a new task. Fix: a send-path `RequestInterceptor` re-detects the pending resume (latest user `FunctionResponse` with **no consumer-authored event after it**) and stamps the parked `task_id`/`context_id` from the matching function-call event's `custom_metadata` (`bridge_client/remote_consumer.py::_pending_resume_target`).
- **A conditional loop-back edge *does* re-run a completed node.** The graph validator *requires* loop-back edges to be conditional (routed); the scheduler re-runs a re-triggered COMPLETED node with a fresh `NodeState`. (The earlier "`Workflow` can't re-enter a completed node" claim was a refuted misdiagnosis — Case 1 fast-forward is scoped to *dynamic* `ctx.run_node()` nodes, not static-graph loop-backs. `adr-0012`, lessons A12.)
- **`DatabaseSessionService` needs the async driver**: `sqlite+aiosqlite:///…`, not bare `sqlite:///…`. And `ResumabilityConfig` lives on `App`, not on a bare `agent=`/`node=` Runner — a durable run must go through the `App` path (lessons A12/A13).
- **Thread the exchange `context_id`** so every round continues the *same* A2A exchange rather than opening a fresh one (the gate writes it to state; the interceptor stamps it outbound).

## Conformance — the Address reference instance

`agents/src/agents/address/graph.py` is the canonical instance and conforms to this shape: `Workflow` conditional cycle; collect = `RemoteA2aAgent`; gate = deterministic `is_satisfied` (`agents/address/satisfaction.py`) setting `ctx.route`; present = **code node today** (`_present`), with `LlmAgent` as the documented drop-in. Durability is split by construct: `build_address_app` carries only the resumability *switch* (`ResumabilityConfig(is_resumable=True)` on the `App`); the durable *stores* — `DatabaseSessionService` (Sessions seam) + the Bridge's `DatabaseTaskStore` (Task-store seam) — are wired at `Runner` construction by the caller (the default `__main__` driver runs `InMemory*` for a single-process demo). With both in place the leg is proven to park at `input-required` and resume to the same terminal outcome across a simulated process restart — `agents/tests/test_durable_graph.py`. Build history lives in `PLAN.md` (S1-6), not here.

To add a new service agent (e.g. Benefits, RFP): reuse `build_bridge_remote_agent` for the collect node, write the use case's deterministic gate, choose a presenter (code or `LlmAgent`), and wire the same four edges. The mock→real / local→GCP swap is only the card URL.

## Related
- [[bridge-a2a-consumer|A2A consumer]] — the `RemoteA2aAgent` construct, the transfer/`AgentTool`/graph wiring trajectory, and the two long-running mechanisms
- [[bridge-collect|Collect]] — the Sense-A/Sense-B split and the "done" decision the gate owns
- [[bridge-long-running|Long-running collection]] · [[bridge-adk|Running on ADK]] · [[bridge-aggregate-model|Aggregate model]]
- [[bridge-deploy-resume|Deploying the resumable Collect loop]] — restore vs. wake on the GCP substrate
- **Decision records:** `docs/decisions/adr-0010-durable-consumer-construct.md` · `docs/decisions/adr-0012-experimental-surface-register.md` · `docs/decisions/adr-0009-native-a2a-consumer.md`
