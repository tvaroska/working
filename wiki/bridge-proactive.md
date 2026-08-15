---
type: atom
related:
  - "[[bridge-gcp-substrate]]"
  - "[[bridge-skills]]"
  - "[[bridge-a2ui-edge]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# Proactive Follow-Up

> *"Remind them"* has **no inbound event to react to** — it needs a clock. That single requirement is the deepest structural change the vision implies, and it is **core — in the [[bridge-open-questions|minimal cut]], from Phase 1**: it is the concrete proof of "mediation, not extraction."

The current design is otherwise entirely **reactive** — something arrives, we react. Follow-up is behavior with no trigger, so it introduces a new runtime pillar:

- **A durable Scheduler/Timer seam** — a clock behind a [[bridge-seams|seam]] like every other managed service: local adapter (in-process, with an **injectable virtual clock** for tests) + GCP adapter (**Cloud Tasks**). Idempotent, crash-safe — timer state persists and recovers on restart.
- **An SLA / policy engine** — cadence, deadlines, max nudges, escalation ladder — read from the [[bridge-skills|process-skill policy]]. So "policy lives in the skill" is proven in Phase 1; `pattern` stays a [[bridge-patterns|selector over built-in flows]], not skill-defined.
- **Egress via the visibility read-model** — a stalled request stamps internal overdue / escalated events and party status on the [[bridge-a2ui-edge|dashboard]], so **no A2A client / no outbound** is needed yet. The real party-channel nudge (the actual send) is fakeable / Phase 4.

**The demo beat.** Let a request go unfulfilled past its SLA window (virtual clock) and watch it move `overdue` → `escalated` with a reminder fired — never silently stalling.

## Related
- [[bridge-gcp-substrate|GCP substrate]], [[bridge-skills|skills]], [[bridge-a2ui-edge|A2UI edge]]
