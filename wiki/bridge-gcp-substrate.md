---
type: concept
down:
  - "[[bridge-seams]]"
  - "[[bridge-zones]]"
  - "[[bridge-proactive]]"
  - "[[bridge-party-memory]]"
related:
  - "[[bridge]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# GCP Substrate

> The half that makes the Bridge a **showcase of the Gemini Enterprise Agent Platform**, not a local prototype: the managed services, the trust boundary, and the deploy path are part of what's demonstrated — and part of what a servicer would actually run in production.

The Bridge showcases the Gemini Enterprise Agent Platform — Agent Runtime, Skill Registry, Memory Bank, Agent Gateway, Agent Identity, A2A, A2UI — as its substrate. Three ideas keep development fast while everything still runs on the real managed platform it showcases:

- **[[bridge-seams|Managed-service seams]]** — every managed boundary has a **local adapter** (fast dev/test) and a **GCP adapter** (deployed), built together and tested against the same suite — develop locally at speed, run deployed on managed services unchanged.
- **[[bridge-zones|Two-zone network model]]** — external provider agents ↔ Bridge (DMZ) ↔ internal backend agents, isolated network-only via Agent Gateway + Agent Identity. A production-grade trust boundary, shown end to end.
- **[[bridge-proactive|Proactive follow-up]]** — a durable Scheduler/Timer seam (Cloud Tasks) drives reminders / SLA / escalation, the concrete proof of "mediation, not extraction."
- **[[bridge-party-memory|Party memory]]** — cross-exchange counterparty memory in Memory Bank, advisory-only (a seam, built in Phase 4).

**Deploy.** A single deploy step packages the Bridge, provisions the Agent Runtime, and builds validated Gateway/Identity deploy specs. Every demo — including the Address warm-up — runs on this deployed path.

## Read next
- [[bridge-seams|seams]] — the local + GCP adapter table
- [[bridge-zones|network zones]] — Gateway ingress + Agent Identity
- [[bridge-proactive|proactive follow-up]] — the Scheduler/Timer pillar
- [[bridge-party-memory|party memory]] — Memory Bank, advisory-only

## Related
- [[bridge|the Bridge]]
