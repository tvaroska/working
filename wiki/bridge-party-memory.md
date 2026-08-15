---
type: atom
related:
  - "[[bridge-gcp-substrate]]"
  - "[[bridge-aggregate-model]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# Party Memory

> The same partner recurs across many exchanges. How they usually send things, what they got wrong last time, their preferred channel — this persists in **Memory Bank**, keyed by the counterparty reference. But the Bridge does **not** own the party as an aggregate.

The internal agent already knows its counterparties, so it supplies a stable [[bridge-aggregate-model|counterparty reference]] (falling back to the exchange context). Memory is a [[bridge-seams|seam]] — local store for dev ↔ Agent Platform Memory Bank deployed — holding an append-only **event log** (corrections, disposition outcomes, channel/format/latency observations) plus a derived **profile** rollup (preferred channel, average response latency, recurring issues, correction hotspots).

**Advisory only** — never silently changes thresholds, auto-routes disposition, or sends outbound outside the normal path. Four intended consumers:

- **Disposition pre-arming** — recurring issues pre-flag matching rules and raise scrutiny; never auto-rejects.
- **Extraction hints** — correction hotspots injected as few-shot examples to lift accuracy on a party's quirks.
- **Outbound defaults** — preferred channel/format/language pre-select the outbound template, overridable.

**Scoped to Phase 4, not Phase 2.** It is advisory, ~3 of its 4 consumers depend on deferred features, and its first *visible* consumer — outbound defaults — lands with the first real outbound in Phase 4. In a one-shot demo its value shows thinly via the growing event log. The seam still ships (local + GCP); just later.

## Related
- [[bridge-gcp-substrate|GCP substrate]], [[bridge-aggregate-model|aggregate model]]
