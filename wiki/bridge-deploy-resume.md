---
type: atom
related:
  - "[[bridge-a2a-consumer]]"
  - "[[bridge-long-running]]"
  - "[[bridge-gcp-substrate]]"
  - "[[bridge-service-agent-architecture]]"
  - "[[bridge-seams]]"
tags: [bridge, deploy]
status: draft
updated: 2026-08-15
---

# Deploying the resumable Collect loop

> How the durable park/resume path ([[bridge-a2a-consumer]], [[bridge-service-agent-architecture]]) runs on GCP. The governing move is to keep **restore** (come back to the same paused state) separate from **wake** (the trigger that re-enters the loop): restore is stock-ADK config that is deployment-agnostic and already proven headless (S1-6); wake is a small custom piece whose home depends on the runtime and is deferred to Phase 3. Decisions: `adr-0010` (durable construct + state restore), `adr-0012` (experimental surfaces), `adr-0001` (stack / platform bets). Substrate: [[bridge-gcp-substrate]], `docs/features/gcp-infra.md`.

## The one distinction that decides everything: restore ≠ wake

A parked leg is `input-required` → a `LongRunningFunctionTool` pause → **the invocation ends, zero compute** ([[bridge-long-running]], lessons A11/A13). Resuming it is two independent problems, and only one of them is deployment-sensitive:

| | **Restore** — return to the identical paused state | **Wake** — the inbound trigger that calls `run_async` again |
|---|---|---|
| What it needs | Persistent Session store (state + events) + persistent Task store (task + artifacts + `context_id`) + `ResumabilityConfig(is_resumable=True)` | A webhook **receiver** for the `PushNotificationConfig` doorbell + a `task_id`→session index, which then calls `run_async` |
| Stock vs custom | **Stock ADK** — plain `google.adk.runners.Runner` + `run_async`; no custom Runner subclass (grep the tree). The only custom bit is the send-path `RequestInterceptor` on `RemoteA2aAgent` (resume re-detection under `Workflow` event ordering) | **Custom** — `a2a-sdk` is sender-only; neither SDK ships a receiver; `adk web` can't host one (lessons A13) |
| Built? | **Yes (S1-6)** — proven across a simulated process restart with **no HTTP**, resuming via `run_async` (`agents/tests/test_durable_graph.py`) | **No** — Phase 3 (`adr-0010` §4) |
| Deployment-sensitive? | **No** — a config/seam swap, a no-op for the agent | **Yes** — this is where Cloud Run vs Agent Engine actually differ |

Because restore is proven with **no HTTP**, the deployment target is not load-bearing for it; the target choice only shapes **where the wake receiver lives**. S1-6 deliberately de-risked the Phase-3 webhook this way (`adr-0010` §4).

## The committed substrate

`docs/features/gcp-infra.md` pins the concrete substrate; the resume path maps onto it as a set of seam swaps ([[bridge-seams]]), each a no-op for the agent:

| Seam | Local (dev) | GCP (deploy) | Role in resume |
|---|---|---|---|
| **Compute / runtime** | local process | **Cloud Run v2** (Terraform `runtime` module) | hosts the stock `Runner`; scale-to-zero = **zero cost across a weeks-long park** |
| **Sessions** | `InMemorySessionService` → `DatabaseSessionService` (SQLite) | **`VertexAiSessionService`** (Vertex/Agent Engine) *or* `DatabaseSessionService` → Cloud SQL | **restore**: reloads state + event history by `(app, user, session_id)`; peer `task_id`/`context_id` ride `event.custom_metadata`, auto-repopulated |
| **Task store** | `InMemoryTaskStore` → `DatabaseTaskStore` (SQLite) | Cloud SQL Postgres now; **managed A2A task-store swap** later (R3) | **restore**: task + artifacts + `context_id` survive restart |
| **Resumability** | `ResumabilityConfig(is_resumable=True)` on the `App` | same (`@experimental`, `adr-0012`) | **restore**: the switch that makes a park survive a restart |
| **Scheduler** | virtual clock | **Cloud Tasks** (`bridge-followups` queue) | the clock alarm that can *wake* a leg (SLA/escalation), alongside the party-turn webhook |

> **Naming reconciliation.** `adr-0001` calls the runtime pillar "Agent Runtime (Vertex Agent Engine)"; the Terraform (`gcp-infra.md`) provisions the compute as **Cloud Run v2** and uses Vertex/Agent Engine for the **Sessions** seam. So the ADK agent runs as a **Cloud Run container** and consumes Agent-Engine-managed sessions — "Agent Runtime" is the platform pillar, not a separate compute host. Keep this straight when reading the two docs together.

## Restore — works on the target as a config swap

Nothing in restore is bespoke. Deployed, it is the S1-6 test with the stores swapped:

```python
from google.adk.runners import Runner              # stock ADK, no subclass
runner = Runner(
    app=build_address_app(card_url),               # carries ResumabilityConfig
    session_service=VertexAiSessionService(...),    # or DatabaseSessionService → Cloud SQL
    artifact_service=GcsArtifactService(...),
)
await runner.run_async(user_id, session_id, new_message=<FunctionResponse content>)
```

**Asterisk (`adr-0012`):** `ResumabilityConfig(is_resumable=True)` is `@experimental`. On Cloud Run you own the `App`/`Runner` wiring, so you can guarantee it is set and honored. If the ADK agent is instead deployed *into* Agent Engine's managed runtime (rather than as a Cloud Run container), whether that runtime lets you set `ResumabilityConfig` on the `App` and honors a `LongRunningFunctionTool` pause **across separate invocations** is a **verify-against-current-docs** item — cover it in the Sprint-B deployed-path parity run (`BRIDGE_TEST_GCP=1`), don't assume it.

## Wake — the differentiator, and it's Phase 3

Wake needs two **custom** pieces (`adr-0010` §4): a receiver for the A2A push doorbell, and a `task_id`→session index; the receiver builds the `FunctionResponse` and calls the stock `run_async`. **The doorbell delivers only "task X changed" — it neither carries state nor re-enters the loop; restore does that.**

- **Cloud Run — the natural home.** You own the FastAPI container, so the receiver is just another route. Scale-to-zero means zero compute while parked; the inbound doorbell HTTP cold-starts the container → look up session by `task_id` → `run_async` → resume. A weeks-idle resumable park is what Cloud Run's request-driven, scale-to-zero model is *for*. This is the assumed target.
- **Vertex Agent Engine — restore-in, wake-out.** Agent Engine's surface is its own query/stream-query API plus managed sessions, not an arbitrary inbound HTTP route you own. So a webhook receiver most likely **cannot live inside Agent Engine**: put it on the Cloud Run service (or a Cloud Function) that receives the push, resolves `task_id`→session, and invokes the session's run. Restore lives inside AE; the wake trigger is orchestrated outside it. *(This reflects Agent Engine's general shape, not a capability verified against a live project — confirm before committing the Phase-3 design.)*

Either way the two custom pieces are the whole of the Phase-3 delta; everything downstream of the receiver is stock (`adr-0010` §4).

## Sequencing

1. **Now (landed):** restore proven headless via `run_async` — no HTTP, no deploy dependency (S1-6).
2. **Sprint B (per phase):** swap the Sessions/Task/Artifact seams to their GCP adapters, deploy on Cloud Run v2, and re-run the shared suite (`BRIDGE_TEST_GCP=1`) — including a **restore-across-restart** assertion on the managed stores and an explicit check that `ResumabilityConfig` is honored on the chosen runtime.
3. **Phase 3:** add the webhook receiver + `task_id`→session index (the only custom deploy surface) so a leg can be woken by an external event, not just resumed by a hand-fed `FunctionResponse`.

## Related
- [[bridge-a2a-consumer|A2A consumer]] — the `RemoteA2aAgent` construct, park/resume, and the state-restore breakdown
- [[bridge-long-running|long-running collection]] — the idle-driven, weeks-scale lifecycle the park serves
- [[bridge-service-agent-architecture|service-agent reference architecture]] — the durable `Workflow` graph being deployed
- [[bridge-gcp-substrate|GCP substrate]] · [[bridge-seams|seams]] — the managed adapters and the local↔GCP swap discipline
- **Decision records:** `docs/decisions/adr-0010-durable-consumer-construct.md` · `docs/decisions/adr-0012-experimental-surface-register.md` · `docs/decisions/adr-0001-stack.md` · **Feature:** `docs/features/gcp-infra.md`
