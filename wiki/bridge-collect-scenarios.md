---
type: atom
related:
  - "[[bridge-collect]]"
  - "[[bridge-disposition]]"
  - "[[bridge-long-running]]"
  - "[[bridge-a2a-consumer]]"
  - "[[bridge-aggregate-model]]"
tags: [bridge]
status: draft
updated: 2026-08-15
---

# Collect scenarios (rejection · delays · keeping context)

> Concrete walkthroughs of the [[bridge-collect|Collect]] loop's three hard cases: **who rejects a document**, **how delays are handled**, and **how context is kept** across turns, restarts, and weeks. Each is a *turn* on the durable exchange, not an engine step. This note is the "what actually happens" companion to the [[bridge-a2a-consumer|consumer wiring]] and [[bridge-disposition|disposition]] atoms.

## The cast, and the two decisions (read this first)

Nothing below makes sense without the **two-decision split** — it is *the* invariant Collect turns on (`docs/lessons-learned.md` A3):

| Decision | Sense | Who owns it | Mechanism | Model may mint it? |
|---|---|---|---|---|
| Is *this document* valid / accepted? | **A — disposition** | the **Bridge** | `run_disposition_gate` (deterministic, per doc) | **never** |
| Is the *requirement set* complete ("done")? | **B — completeness** | the **app** (address agent) | `is_satisfied` (deterministic, over the ledger) | **never** |

"LLM routes, code decides" applies to **both** — the model may *route* (call the gate, chase the next proof) but can never *mint* an acceptance or a "done". Keep A and B distinct: **the app never rejects a document, and the Bridge never declares the set complete.**

Identifiers ([[bridge-aggregate-model]]): **`context_id`** = the exchange (durable, 1:1 with the casefile) · **`task_id`** = one leg/document collection · **`message_id`** = one turn. Keeping context = keeping the `context_id` alive.

---

## Scenario 1 — A document is rejected

**Who rejects: the Bridge, always (Sense A).** A rejection is a `disposition` on a ledger entry, not an act of the app. The address agent has *no reject verb*; its only lever is Sense B — keeping a requirement **outstanding**.

```
party → Bridge:  utility bill (blurry scan)
Bridge:          parse/classify → run_disposition_gate → REJECTED (illegible)
Bridge:          ledger entry {doctype: utility-bill, disposition: rejected, reason: illegible}
Bridge → app:    ExchangeTurn{ status: { ledger:[…rejected…], outstanding:[utility-bill], terminal:false } }
app  (is_satisfied): only ACCEPTED entries count → still not done → keep utility-bill outstanding
app  → Bridge:   chase the outstanding proof   (a resume turn, same context_id)
```

The app runs `is_satisfied`, which counts **only `ACCEPTED`** entries (`satisfaction.py`) — a rejected doc simply doesn't advance completeness, so the loop chases again. No app-side rejection logic exists or is needed.

Three sub-cases that are easy to conflate:

- **Rejected → resubmit** (a *fresh document* is awaited). `resubmit` is **deliberately non-resumable** — it does not park awaiting a *human decision*; it awaits a *new artifact* from the party. The leg's `task` stays open/outstanding; the next party arrival with a better scan is a new turn on the same `context_id`.
- **Escalation ≠ rejection.** An escalation (e.g. suspected fraud, ambiguous issuer) routes to a human/HITL path; it is **not** a terminal reject and must not be collapsed into one. The document is neither accepted nor discarded — it's parked for a decision (see Scenario 2, park).
- **Terminal reject of the *exchange*.** Distinct from a per-doc reject: the *app* may stop the whole exchange (give up) by declining to keep chasing — but that is a Sense-B "not done, stopping", still not a Sense-A document verdict. Parity is asserted on the **terminal reason + accepted-issuer set**, never a ledger-step match (mock↔real, `docs/lessons-learned.md`).

> **Trap:** "the address agent rejected the document." It didn't — it can't. Restate as *"the Bridge dispositioned the document REJECTED; the app kept the requirement outstanding."*

---

## Scenario 2 — Delays

A casefile fills over [[bridge-long-running|days or weeks]]. Which delay mechanism the caller gets is **selected by the Bridge's task status**, not chosen by the consumer:

| Timescale | Bridge emits | Consumer behavior | Wire |
|---|---|---|---|
| seconds–minutes (connected) | `working` + non-empty `status.message` | streamed **progress** (thought events); connection held (≤ client `timeout`, 600 s) | `message/stream`, `TaskStatusUpdateEvent` |
| hours–weeks (idle) | **`input-required`** (park) / `auth-required` | native **pause** — invocation *ends*, zero compute; resumes on a later turn | `input-required` → `LongRunningFunctionTool` pause |
| after disconnect | (unchanged) | **re-attach / snapshot** | `tasks/resubscribe`, `tasks/get` |
| weeks-scale wakeup | terminal or park transition | **callback** (Phase 3) | `PushNotificationConfig` |
| terminal | `completed` + artifact | deliverable returned | `ExchangeTurn` on `completed` |

**Fast path (mock ~10 s hold):**
```
app → Bridge:   message/send (CollectRequest)
Bridge:         Task{submitted} → working ("Collecting…") → hold → completed + ExchangeTurn
app:            is_satisfied → done → present
```

**Slow path (party is slow — chase then park):**
```
app → Bridge:   collect proof of address
Bridge:         working ("Follow-up sent: statement overdue.")     ← faked chase (mock) / real chase
Bridge:         working ("Reminder sent — awaiting a 2nd issuer.")
Bridge → app:   input-required  ("Awaiting additional proof")       ← PARK: invocation ends, 0 compute
                … hours/days pass; no process sits in the loop …
party → Bridge: second utility bill arrives                         ← the WAKE is a party turn
Bridge:         disposition ACCEPTED → completed + ExchangeTurn
app (resumed):  is_satisfied → done → present
```

Key points:
- **What wakes a parked leg is a *party turn to the Bridge*** (or a [[bridge-proactive|clock alarm]] / HITL resume), **not** the app polling. The app's resume is often an empty ack ("keep going"), not new data — the deliberate overload of `input-required` (`adr-0009` §2 risk).
- **Progress must carry a non-empty `status.message`** — an empty status update is silently dropped by ADK (`a2a-sdk` 1.x gotcha, [[bridge-a2a-consumer]]).
- **Timeout is a chase, not a failure.** A party missing a deadline produces another chase turn / a park, never a Sense-A reject.

---

## Scenario 3 — Keeping context

"Keeping context" = every turn continues the **same `context_id`** so the ledger accumulates. The Bridge is the stateful aggregate (keyed on `context_id`, cumulative ledger); the *consumer* must re-send under that same id. There are three levels, in increasing durability:

**Level A — across rounds, same invocation (today, `AgentTool`).**
Each `AgentTool` call runs the Bridge in a **fresh child session**, wiping `RemoteA2aAgent`'s own `context_id` history. So the id is **hand-threaded through parent session state**: the tool writes the returned turn's `context_id` under `bridge_exchange_context_id`; the send-path interceptor stamps it on the next `message/send`. Every round continues one exchange. The `task_id` is *not* reused in the `park=false` completing path — each round opens a new task under the same context (re-sending to a *completed* task is invalid A2A). *This is the in-turn tracer.*

**Level B — natively, on one shared session (the durable target, `Workflow`).**
A native graph ([[bridge-a2a-consumer]] "Wiring: why the graph") runs the Bridge as a node on the **shared, durable `InvocationContext`**. `RemoteA2aAgent` then sees its own prior event and **reuses the `context_id` natively** — the hand-threading in Level A disappears. This is also the only place a real `input-required` **park/resume** works (the pause suspends the graph and resumes from saved node state).

**Level C — across a process restart (weeks-scale).**
Restore is *mostly platform-default* — see [[bridge-a2a-consumer]] "Durable state restore":
- **DEFAULT:** persistent `DatabaseSessionService` (session state + events) + `DatabaseTaskStore` (task + artifacts + `context_id`); the Runner auto-matches a `FunctionResponse` to the paused call and rebuilds the invocation.
- **EXPERIMENTAL:** `ResumabilityConfig(is_resumable=True)` — the switch that makes a park survive a restart.
- **CUSTOM (Phase 3 only):** the **wake** — a webhook receiver + a `task_id`→session index; the webhook is a *doorbell, not a restore*.

```
[week 1] app parks the leg   → session + task persisted; context_id on both
[process dies / redeploys]
[week 3] party submits doc   → Bridge task → completed  (push doorbell, Phase 3)
          receiver: task_id → (user, session) → build FunctionResponse → run_async(...)
          Runner: reload session, re-match paused call, resume → is_satisfied → done
```

> **Contract trap (accumulation).** `is_satisfied` reads the ledger the Bridge returns and assumes it is the **full accumulated set**, not a per-turn delta. The mock accumulates (TWO_BILLS round 2 = both bills), so overwrite-not-append is correct *today*. A real Bridge that ever returned a delta would make the gate under-count. Keep the "ledger is cumulative per `context_id`" contract explicit.

---

## Invariants these scenarios must never violate

- The **app never rejects a document** (Sense A is the Bridge's); the **Bridge never declares the set done** (Sense B is the app's).
- A **model may never mint** an acceptance or a "done".
- **Escalation ≠ rejection**; **`resubmit` is non-resumable** (awaits a fresh artifact, not a human decision).
- **Only `ACCEPTED` entries** count toward completeness; issuers are compared **already-canonical** (`"Power Co."` → `power-co`).
- **Parity is terminal-outcome** (terminal reason + accepted-issuer set), never a ledger-step match — the mock is a permanent contract double, not a throwaway.
- **The classified ledger has no timestamp** — persistent adapters need a deterministic sort key ([[bridge-aggregate-model]]).

## Related
- [[bridge-collect|Collect (casefiles)]] · [[bridge-disposition|disposition (Sense A)]] · [[bridge-long-running|long-running collection]]
- [[bridge-a2a-consumer|A2A consumer]] (wiring, durable state restore, the three wirings) · [[bridge-aggregate-model|aggregate model]]
- `docs/decisions/adr-0009-native-a2a-consumer.md` (native consumer + wire vocabulary) · `docs/decisions/adr-0010-durable-consumer-construct.md` (durable `Workflow` construct + state restore — Level B/C) · `docs/lessons-learned.md` (A3 two-decision split, A12–A13 durable construct/restore, C1 demo values)
