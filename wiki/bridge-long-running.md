---
type: atom
related:
  - "[[bridge-a2a-edge]]"
  - "[[bridge-collect]]"
  - "[[bridge-proactive]]"
  - "[[bridge-aggregate-model]]"
tags: [bridge]
status: review
updated: 2026-08-15
---

# Long-running collection (the durable A2A task)

> A real collection is **human-paced** — a party takes days or **weeks** to send what's asked. Over that horizon the exchange cannot be *a thing that is running*: not a held-open connection, not an in-process loop, not in-memory state. It is a **durable A2A task that mostly sits idle**, woken only by two events — a document arriving, or a clock firing. Canonical A2A ([[bridge-a2a-edge|A2A edge]], `adr-0007`) and the ADK-native runtime (`adr-0006`) give exactly the primitives for that.

## The A2A task *is* the long-running unit

The exchange is the [[bridge-aggregate-model|A2A context]]; each leg's work is an **A2A task** with a lifecycle (`SUBMITTED → WORKING → INPUT_REQUIRED → COMPLETED/FAILED/CANCELED`). A task is a **server-side resource with no built-in TTL** — it may legitimately stay `WORKING` or `INPUT_REQUIRED` for weeks. Nobody holds it open; it is persisted and rehydrated on demand. This is why we speak canonical A2A rather than a bespoke request/response: A2A already models a task as a long-lived, resumable, independently-addressable resource, and gives us the reconnection verbs a weeks-long window needs.

**The mediation runs on wake, not in a loop.** Between a party's turns the Bridge does *nothing* and costs nothing. Work happens only when woken:

| Wake source | Trigger | Bridge does |
|---|---|---|
| **Party turn** | a document/response arrives inbound on the [[bridge-a2a-edge|A2A]]/A2UI edge | one [[bridge-collect|Collect]] turn — classify, disposition, update ledger, re-propose outstanding |
| **Clock** | a [[bridge-proactive|Scheduler]] alarm fires (SLA cadence/deadline) | advance the ladder `on_track → overdue → reminder → escalated`, record the event, re-arm the next alarm |
| **HITL resume** | a human review completes | resume the parked task from its persisted session |

## Three things must survive weeks (and restarts)

Each has a durable home behind a [[bridge-seams|seam]] — the catch is that the durable home is **Phase 3**, so today's local path tolerates "days, if nobody restarts", not "weeks":

| State | Durable home (committed) | Today (Phase 1 local) |
|---|---|---|
| Conversation / turn state, HITL suspension | persisted `SessionService` (Vertex) — resume recovered from the session, not an in-memory map | `InMemorySessionService` — **lost on restart** (`adr-0006` consequences) |
| Documents (versioned per resubmission) | `GcsArtifactService` | `InMemoryArtifactService` — lost on restart |
| SLA timers + follow-up read-model | **Cloud Tasks** alarms + Bridge-owned relational store | in-process `VirtualClock` + in-memory dict ([[bridge-proactive]], S1-core-8) |

The design intent is already recorded — "interrupt/resume is recovered from the **persisted session**, so multi-day HITL resume is crash-safe" ([[bridge-aggregate-model]]) — but **weeks is the horizon that makes the Phase-3 durable substrate non-optional**, where the demo path only ever needed "long enough to fast-forward the virtual clock".

## Time is driven by the clock, not by anyone waiting

Chasing a silent party is the [[bridge-proactive|proactive follow-up]] ladder read from the process-skill SLA policy (cadence, deadline, max nudges, escalation). At weeks scale this is the right mechanism precisely because **a reminder is a scheduled callback, not a held connection**: on GCP a Cloud Tasks alarm fires days apart, does one turn of work, and re-arms — zero compute in between. HITL suspends the same way (`LongRunningFunctionTool`, zero compute).

## How the client learns of progress over weeks

Nobody keeps a stream open for weeks. Canonical A2A decouples "learning of progress" from "holding a connection" via three surfaces:

- **`tasks/get`** — poll status at any point, days later, no live stream needed.
- **`tasks/resubscribe`** — re-attach to the event stream after the inevitable disconnect (the current hand-rolled SSE cannot reconnect — `tech-debt` §9).
- **Push-notification config (webhooks)** — the *correct* long-running answer: the Bridge calls the servicer back on state change instead of anyone polling or streaming. **Deferred to Phase 4** today ([[bridge-a2a-edge]]); **weeks is the argument for pulling it forward**, since polling for weeks is wasteful and streams don't survive that long.

## The servicer loop is event-driven, not process-bound

The Phase-1 agent-side `run_collect` is an in-process `async` loop with a `max_turns` cap — fine for a demo that finishes in seconds, but it **cannot span weeks** (the servicer process would have to stay alive throughout). Because `next_requirements` is a pure function of `(status, ledger)`, the servicer does not need to *sit* in the loop. The continuation lives in the **durable exchange**, not a process stack:

```
open exchange (persist context) → go idle
  ↑                                   │
  └── woken by push / tasks/get ──────┘  recompute next_requirements → post turn → go idle
```

Same [[bridge-collect|Collect]] contract, same `next_requirements` logic — only the loop's *continuation* moves from the process into the persisted task.

## Lifecycle policy (decided — `adr-0008`)

Weeks-scale forced four lifecycle decisions, recorded in `docs/decisions/adr-0008-long-running-collection-lifecycle.md`:

- **No TTL, no auto-abandon — the app closes.** No wall-clock cap on a task (weeks are legal), and the Bridge never auto-closes. The [[bridge-proactive|escalation ladder]] runs and then **holds at `escalated`**, making the stall visible; **terminal close is the app's explicit `cancel_task`** (sense-B ownership). Trade-off: stalled legs remain open until the app acts — the safeguard is visibility (escalation queue), not auto-expiry.
- **Context is durable; the credential is short-lived.** The A2A context has no expiry; access is re-authorized **per inbound turn** at the Gateway ([[bridge-zones]]), and the out-of-band link is renewable **without orphaning the context**. No long-TTL bearer token may be the sole key to a weeks-long exchange.
- **Artifact retention** = backend object-lifecycle policy (no bespoke GC), at least the exchange life; the concrete post-terminal window is **deferred to deploy-time policy**, not fixed in the architecture.
- **Push pulled forward to Phase 3.** Inbound-triggered A2A `PushNotificationConfig` (servicer opts in to callbacks about its own exchange) is separated from the still-Phase-4 outbound *client*.

## Status

- **Committed / correct in shape:** idle durable task + clock-driven chase + zero-compute HITL suspend; canonical A2A `tasks/get` / `tasks/resubscribe` (`adr-0007`).
- **Decided (policy, `adr-0008`):** no TTL / no auto-abandon (app closes via `cancel_task`), durable-context/short-credential, backend-enforced retention (window TBD at deploy), push pull-forward to Phase 3.
- **Phase 3 (implementation):** the durable substrate (Vertex sessions, GCS artifacts, Cloud Tasks timers, persisted SLA read-model) plus the `adr-0008` mechanisms — none built yet.

## Related
- [[bridge-a2a-edge|A2A edge]], [[bridge-collect|Collect]], [[bridge-proactive|proactive follow-up]], [[bridge-aggregate-model|aggregate model]]
