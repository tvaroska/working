---
type: atom
related:
  - "[[bridge-edges]]"
  - "[[bridge-fulfillment-graph]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# A2UI Edge (humans)

> The human-facing front door — for parties without an agent. The Bridge emits declarative **A2UI** and ingests a structured response back.

**Content and protocol, not pixels.** The Bridge describes *what* to show (upload a file, paste free text, fill a form) and *what* it gets back (a structured response), but never *how it looks*. Any host frontend or portal renders the A2UI in its own design system. The project ships a reference renderer as demo furniture — it is not the product.

**What it powers.** The A2UI edge is how [[bridge-dual-path|Path B fulfillment]] works: a human uploads a PDF, pastes text, or fills a form; the Bridge feeds it into the [[bridge-fulfillment-graph|extraction graph]]. The same surface pattern renders the other human-facing views:

- **HITL review** — a reviewer works flagged extractions side-by-side with the source.
- **Party status** — "what you sent, what's accepted, what's still missing, what's next."
- **Internal dashboard** — grouped by actionable state, per **exchange**, not per raw task.
- **Program comparison** — N carrier legs side by side, one currency and schema, standard gaps flagged (the golden payoff). *[Aspirational — Phase 2]*

All surfaces are projections of the [[bridge-aggregate-model|read-model]] over the task/artifact layer, updated live. The concrete demo surfaces built on this edge — the three actor frontends, presentation modes, and time-warp — are detailed in [[bridge-frontend|frontend]].

## Related
- [[bridge-edges|two edges]], [[bridge-fulfillment-graph|extraction graph]], [[bridge-frontend|frontend]]
