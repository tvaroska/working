---
type: atom
related:
  - "[[bridge-patterns]]"
  - "[[bridge-disposition]]"
  - "[[bridge-a2ui-edge]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# Extraction (Fulfillment) Graph

> The Path-B pipeline the Bridge runs when a **human** party supplies an upload / free-text / form via the A2UI portal: extract → gate → disposition, as a durable graph.

```
START → receive_document → extract_with_quality_gate ─┬─ pass ─→ confidence_gate ─┬─ auto_approve → finalize
                                   │                  ├─ escalated → escalate      └─ hitl_review → hitl_review → finalize
                                   │                  └─ error ─→ extraction_error
                                   └── resubmission loop (≤ 3 attempts) ──┘
```

- **Quality gate first.** Confidence below the resubmit threshold (or critical fields unreadable) → request an image **resubmission** (actionable message, capped at 3 retries, then escalation) — re-enters extraction on the **same** task as a new artifact version.
- **Confidence gate.** At or above the auto-approve threshold with no flagged fields → auto-approve; else route to **HITL review**.
- **HITL suspends the workflow** with **zero compute** for minutes/hours/days and resumes on a webhook — recovered from the persisted session, so it survives a restart.

**Extraction is a [[bridge-seams|seam]], not a hardcoded engine.** The graph calls one extraction service that returns normalized fields plus per-field and overall confidence, legibility, and flagged fields; the gates below read those signals no matter which engine ran. Phase 1 ships **Gemini** (schema-driven constrained JSON per the [[bridge-skills|doctype skill]], multimodal, no OCR pipeline, ~$0.10 / 1k pages) plus a deterministic **fixture** adapter for tests; **Document AI** (a processor per doctype, native per-field confidence, residency / compliance posture) is a later-phase swap. Engine is chosen by config and per-doctype capability. Schema validation remains a layer on top of whichever engine produced the result. This is the [[bridge|thesis]] made literal: mediation is the focus, extraction is covered by dedicated services, so it lives behind a swap.

**Path A skips this graph** — a structured response is validate-only (see [[bridge-dual-path|dual-path]]). Multilingual translate + FX normalization is *[Aspirational — Phase 2]*.

## Related
- [[bridge-patterns|patterns]], [[bridge-disposition|disposition]], [[bridge-a2ui-edge|A2UI edge]]
