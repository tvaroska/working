---
type: atom
related:
  - "[[bridge]]"
  - "[[bridge-collect]]"
  - "[[bridge-party-memory]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# Aggregate Model

> The unit of work is not a document — it's an **exchange**: a durable, multi-turn interaction with a party about a set of documents, made of one-or-more tasks.

**Four levels.** A2A models three (context → task → message); the underlying agent runtime models two (session → invocation). The Bridge binds them so the runtime never has to model the exchange:

| Concept | Realized as | Owner |
|---|---|---|
| **Party** | a stable counterparty reference | Backend — *not* a Bridge aggregate |
| **Exchange** | the A2A context (an aggregate the Bridge stores) | Bridge — groups the tasks |
| **Requirement item** | one slot in a Collect exchange | Agent (what) + Bridge (state) |
| **Task / Artifact** | one runtime session, one per task | Bridge |

> **"Artifact" here is the A2A/task artifact** — a versioned *metadata* payload (a ledger entry, the Requirements list). The document *bytes* are a separate, same-named concept — the ADK document artifact — covered in [[bridge-artifacts|documents as artifacts]]. Both version; one carries meaning, the other bytes.

**Key invariants.** One task is one runtime session, keyed one-to-one; a task is scoped to the party's counterparty reference (falling back to the exchange context when none is supplied). Each task owns isolated, resumable state, so tasks in one exchange never clobber each other. One turn is one runtime invocation.

**Exchange = the A2A context (1:1).** There is no separate exchange ID. The Bridge mints the context at request time and returns it; both sides name the interaction identically. It may begin as a view over the tasks sharing that context and earns a standalone record once it holds exchange-only state (process-skill binding, Requirements artifact, program membership, reopen). The **Address** warm-up does *not* force this: its [[bridge-collect|bounded Collect]] keeps only a **classified ledger** of accepted docs, which can be derived as a view over the exchange's tasks (one doc per task). The standalone record is forced later — once an agent-owned **Requirements artifact**, program membership, or reopen state appears (emergent Collect, Phase 3).

**Party is not an aggregate.** The internal agent already knows its counterparties, so it supplies a stable counterparty reference. Cross-exchange memory keys on that reference, not a Bridge-owned entity — see [[bridge-party-memory|party memory]].

**Interrupt/resume is recovered from the persisted session**, not an in-memory map — so multi-day HITL resume is crash-safe.

## Related
- [[bridge|the Bridge]], [[bridge-collect|Collect]], [[bridge-party-memory|party memory]]
