# ADR-0003 — Exchange is a view over its tasks; it earns a standalone stored record only on exchange-only state

- **Status:** Accepted
- **Date:** 2026-08-06
- **Resolves:** `PLAN.md` → S0-docs-1 (decision 2 of 4)
- **Context:** `wiki/bridge-open-questions.md` → Open decisions, `wiki/bridge-aggregate-model.md`, `docs/architecture.md` §3, `wiki/bridge-seams.md`

## Context

The Exchange is the Bridge's unit of work — the A2A context (1:1, no separate ID) grouping the tasks of a multi-turn interaction. The open question (`wiki/bridge-open-questions.md`): when does an Exchange earn a **standalone stored record** versus stay a **derived view** over the tasks sharing its context?

The aggregate model already leans view for the Phase-1 Address demo: "The **Address** warm-up does *not* force this: its bounded Collect keeps only a **classified ledger** of accepted docs, which can be derived as a view over the exchange's tasks (one doc per task)." The standalone record is forced only "once an agent-owned **Requirements artifact**, program membership, or reopen state appears (emergent Collect, Phase 3)." (`wiki/bridge-aggregate-model.md`.)

## Decision

**The Exchange is realized as a derived view over the tasks sharing its A2A context by default.** For Phase 1 (Address), there is **no standalone stored Exchange row**: the classified ledger and all exchange-level state are computed from the exchange's tasks (one document per task). The A2A context token is the identity; task rows carry it as the grouping key.

The Exchange **materializes into a standalone stored record** only when genuine **exchange-only state** appears that cannot be derived from the tasks:

- an agent-owned **Requirements artifact** (emergent / agent-mutated Collect, Phase 3),
- a **process-skill binding** stored on the exchange,
- **program membership** (e.g. Benefits program rollup, Phase 2),
- **reopen** state (an exchange resurrected after closure).

The **Exchange store seam** is still defined and built in Sprint 1 (`PLAN.md` S1-core-2; `wiki/bridge-seams.md`) — the interface and the local + GCP relational adapters exist. What this ADR settles is that in Phase 1 the store is **not written for Address exchanges**: the seam is present for parity and future materialization, and the read path returns a view assembled from tasks. Materialization is a one-way transition triggered by first appearance of exchange-only state; once materialized, the record is the source of truth for that exchange and the view derives from record + tasks.

## Rationale

- **The wiki already leans view.** `wiki/bridge-aggregate-model.md` and `docs/architecture.md` §3 both state Address stays a view; this ADR records that lean as the decision.
- **No premature aggregate.** Address has no exchange-only state — everything (accepted docs, outstanding, rejections) is a fold over the per-task states. Storing a redundant row would create a second source of truth to keep consistent, for no Phase-1 benefit.
- **Minimal and reversible.** Keeping the store seam but not writing it means enabling standalone records later is a code change on one path, not a schema migration or a re-architecture. The trigger conditions are already enumerated.
- **Consistent with "task = session" invariant.** The durable, resumable state already lives at the task/session level; the exchange is a grouping, so a view is the natural default.

## Consequences

- Phase-1 classified ledger (`PLAN.md` S1-core-7) is implemented as an **append-only view over exchange tasks**, matching its plan description ("append-only view over exchange tasks: doctype, key fields, disposition").
- The Exchange store seam + adapters are built (S1-core-2) but exercised by tests via the future-materialization path, not by Address happy-path runs; the shared seam suite must cover both "view-only" and "materialized" reads.
- A single, explicit **materialization trigger** must be implemented at the point exchange-only state is first written (deferred to whichever phase introduces it — Phase 2 program membership or Phase 3 Requirements). Phase 1 only needs the view path.
- Exchange identity remains the A2A context token throughout; materialization must not mint a new id.

## Alternatives considered

- **Always store a standalone Exchange record from day one.** Uniform model, but adds a redundant source of truth and consistency burden with zero Phase-1 payoff, and pre-commits schema before requirements are known. Rejected.
- **Never store; always derive.** Impossible once agent-owned Requirements or reopen state exists (not derivable from tasks). Rejected — the view is a default, not an absolute.
- **Store lazily but keyed on a new exchange id.** Breaks the "Exchange = A2A context, no separate ID" invariant (`wiki/bridge-aggregate-model.md`). Rejected.
