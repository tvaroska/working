---
type: atom
related:
  - "[[bridge-gcp-substrate]]"
  - "[[bridge-skills]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# Managed-Service Seams

> Every managed-service boundary is a **seam** with **two adapters**, selected by config: a **local adapter** (fast dev/test) and a **GCP adapter** (deployed). Built together, not local-first-then-swap.

| Seam | Local adapter | GCP adapter |
|---|---|---|
| **Sessions** | local embedded store | Agent Platform Sessions |
| **Task store** | local embedded store | a managed relational store *[now]* → the platform's managed task store *[future — when it ships]* |
| **Exchange store** | local embedded store | a managed relational store |
| **Skill registry** | directory of [[bridge-skills\|Agent Skills]] folders | GCP Skill Registry (same [[bridge-skills\|Agent Skills format]]) |
| **Memory bank** | local event log | Agent Platform Memory Bank |
| **Scheduler/Timer** | in-process, virtual clock | Cloud Tasks |
| **A2A client (outbound)** | injected fake transport | authenticated transport with Agent Identity |
| **Extraction** | fixture extractor (deterministic) | Gemini *or* Document AI — engine-selectable |

**The config knob** selects a global seam mode (local or deployed) with per-seam overrides, so you can move one boundary onto a managed service at a time. The **same test suite runs against both** adapters — that parity is what lets the Bridge develop at local speed while genuinely running on the managed platform it showcases.

**Why seams outlast the demo.** The Agent Platform and the A2A protocol are still moving — capabilities that need a self-owned store today become managed services tomorrow. The A2A **task store** is the live example: today it's backed by a store we run, but as the platform matures into a managed task store, adopting it is a **one-adapter swap** with the shared test suite proving behavior didn't change. The seam is how the Bridge rides platform evolution without a rewrite — a property a real product needs, not just a demo. The same holds per boundary, so the Bridge can move onto each new managed service the day it lands.

**Why the exchange store is a store we own.** The Exchange is a Bridge-invented aggregate with no managed GCP equivalent, so its GCP adapter is a store we own. It uses a relational store on both sides, so one implementation serves both local and deployed — queryable keys are indexed, flexible aggregate parts live in a document column. A managed relational upgrade path exists with no rewrite.

**Why the skill registry format is the same on both sides.** Both adapters store the identical unit — an [[bridge-skills|Agent Skills]] folder (`SKILL.md` + `assets/`, agentskills.io). The local adapter is a directory of those folders; the GCP adapter is the managed GCP **Skill Registry** holding the same folders. Because the *format* is the seam contract (not a store-specific schema), a skill authored once installs unchanged locally and deployed, the Agent Card is generated from the same `name`/`description` either way, and `skills-ref validate` gates both. Moving to the managed registry is a storage swap, not a re-authoring.

**Why extraction is a seam — and why two engines.** Extraction is [[bridge|covered by dedicated services]], so the Bridge refuses to marry one engine. The extraction service returns normalized fields plus per-field and overall confidence, legibility, and flagged fields; [[bridge-disposition|disposition]] reads those signals **engine-agnostically**. Phase 1 ships the **Gemini** adapter (schema-driven JSON, multimodal, ~$0.10 / 1k pages) plus a deterministic **fixture** adapter for fast tests. The **Document AI** adapter (a processor per doctype, native per-field confidence, the data-residency / compliance posture some servicers require) lands in a later phase as the one-adapter-swap proof. Note the axis differs from the storage seams: the real engines are deployed either way, selected by config and per-doctype capability, not local-vs-GCP. Adding the second engine later is the thesis made literal — mediation is the focus, extraction is delegated: swap the engine, the mediation around it never moves. **Caveat:** unlike the relational stores, Document AI is not a free swap — Gemini takes an arbitrary schema and prompt, Document AI needs a processor bound per doctype (see [[bridge-skills|doctype engine binding]]).

Some GCP *write* paths (event publish, timer enqueue, memory write) are scoped as client-wiring first, with request assembly landing on the deployed edge — *[Aspirational]*, not part of the [[bridge-open-questions|minimal cut]].

## Related
- [[bridge-gcp-substrate|GCP substrate]], [[bridge-skills|skills]]
