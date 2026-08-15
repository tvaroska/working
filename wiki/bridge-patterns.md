---
type: concept
down:
  - "[[bridge-fulfillment-graph]]"
  - "[[bridge-disposition]]"
  - "[[bridge-collect]]"
related:
  - "[[bridge]]"
  - "[[bridge-skills]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# Exchange Patterns

> The pipeline is **not one fixed workflow**. Each demo runs one of a few **built-in patterns** — a closed set of flows the Bridge owns in code. The process skill *selects* the pattern; it does not define one.

The **core is the solicited spine** — the servicer always asks first:

| Pattern | Flow | Example |
|---|---|---|
| **Request (pull)** | agent asks → party supplies → normalize → deliver | Address, ID-only branch (CUJ-10) |
| **Negotiate** | agent requests → party responds → revise loop → finalize | Benefits, over a program (CUJ-11) |
| **Deliver** | agent sends → format per channel → confirm | outbound document (CUJ-3) |
| **Collect** | agent sets requirements → Bridge assembles a document *set*, looping until the agent judges it complete | [[bridge-collect\|Address]] bounded (CUJ-10) · [[bridge-collect\|RFP / casefile]] emergent (CUJ-13) |
| **Extract** | party pushes → normalize → deliver | *deferred cold-inbound edge* |

Whatever the pattern, a human-fulfilled step runs the same [[bridge-fulfillment-graph|extraction graph]], and every arriving artifact passes [[bridge-disposition|disposition]] before it counts.

**The pattern set is closed — there is no workflow DSL.** These few patterns are the domain primitives of document mediation; industries don't differ in *flow*, they differ in *which documents* and *what policy*. So `pattern` is a **selector over a closed set of built-in flows** (code the Bridge team owns), and industry-agnosticism comes from the [[bridge-skills|skills]] layered over them — doctype schemas, process policy, candidate doctypes — plus, for [[bridge-collect|Collect]] and Negotiate, the **agent's per-turn decisions** in the multi-turn exchange. A new industry is new *skills*, not new *flow*. The only real gap today is that just one flow is built so far; the others are built as the demos land (Negotiate in Phase 2, Collect in Phases 1/3). *Policy* already lives in the skill. If a future use-case ever needs author-defined flow, we delegate to an existing engine behind a [[bridge-seams|seam]] — we never build a bespoke one.

## Read next
- [[bridge-fulfillment-graph|extraction graph]] — the extract → gate → disposition pipeline (the spine)
- [[bridge-disposition|disposition]] — is this submission acceptable, and where does it route
- [[bridge-collect|Collect]] — assembling a document set the agent judges complete

## Related
- [[bridge|the Bridge]], [[bridge-skills|skills]]
