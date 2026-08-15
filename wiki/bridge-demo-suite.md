---
type: concept
down:
  - "[[bridge-address-demo]]"
  - "[[bridge-benefits-demo]]"
  - "[[bridge-rfp-demo]]"
  - "[[bridge-stages]]"
  - "[[bridge-collect]]"
  - "[[bridge-open-questions]]"
related:
  - "[[bridge]]"
  - "[[bridge-patterns]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# Demo Implementations

> **Three demo implementations, one core.** The [[bridge|Bridge core]] is the independent project; each demo is a **self-contained implementation** — skills plus a thin driver — running against the single deployed core. The showcase narrative **leads with breadth — the reusability thesis**: the same core serves two *different* industries, with a whole demo added live and no redeploy. That breadth is the clearest single proof of what the Agent Platform enables. Benefits is the depth example, not the sole headline.

**Separation of concerns.** The core is independent; the demos are peers to each other and never edit the core — if a demo needs a core change, that change is generic and lives in the core. A **showcase runner** boots one core with all demos loaded. Adding a demo is adding configuration, not forking the platform.

| Demo | Role | Pattern | Scale |
|---|---|---|---|
| **[[bridge-rfp-demo\|RFP / procurement]]** | **Breadth proof — the headline**; ⚠ last-built (Phase 3), most cuttable, protect from cut | [[bridge-collect\|Collect]] (emergent) | N suppliers · added *live*, no redeploy |
| **[[bridge-benefits-demo\|Benefits]]** | **Depth** — the full arc "one comparable view" | Negotiate | N carriers · 3 formats/languages/currencies |
| **[[bridge-address-demo\|Address]]** | **Warm-up** — proves the pull spine, two edges + [[bridge-proactive\|proactive follow-up]], and a *bounded* [[bridge-collect\|Collect]] | Request (pull) + Collect (bounded) | 1 party · gov ID **or** 2 bills from different companies · chase the missing bill → reminder → escalation |

- **Benefits** carries one demo end to end: fan-out → normalize → compare/standard-gap → negotiate → bind. This is where "one comparable view" earns its keep.
- **RFP** proves industry-agnostic reuse — a different industry that generalizes the Collect pattern from bounded (Address) to emergent/agent-mutated at N-supplier scale, config-only. It bears the headline but is built last (Phase 3); the Phase-2 live doctype-add is its early down-payment.
- **Address** is the objection-handler at small scale — dual-mode fulfillment on the pull spine, a *bounded* Collect (alternative satisfaction: one gov ID **or** two bills from different companies, with agent-owned completeness — the Bridge best-efforts an advisory assessment), plus the proactive chase→escalate beat end to end. It introduces classification and a classified ledger in bounded form (no typed slots — the completeness *decision* is the agent's, with the Bridge best-efforting an advisory assessment over the ledger), so Phase 3 only has to *generalize* to agent-mutated Requirements, not invent the pattern.

## One core, many demos at once

> Separate demo implementations risk reading as three apps. They aren't: the separation is at **packaging** time, coexistence is at **runtime**. Three proofs that one deployed core handles every use-case *together*:

- **One Agent Card, all demos.** The [[bridge-a2a-edge|Agent Card]] is generated from *installed* skills — load Address + Benefits + RFP into one core and the card advertises every doctype/process at once: a single agent that speaks all three use-cases.
- **One dashboard, mixed exchanges.** The [[bridge-a2ui-edge|dashboard]] groups by *exchange*, not by demo — an Address request, a Benefits program, and an RFP casefile run **concurrently** on one view, over one shared exchange/task store. One query returns all three types.
- **Live-add without disturbing what's running.** Add RFP *while Address and Benefits exchanges are already in flight* — the new use-case joins the same card and dashboard, no redeploy, no interruption.

The artifact that drives this is the **showcase runner** — not a fourth demo, but the harness that boots one core with all demos loaded and exercises them together. It lands in **Phase 3**, when the third demo makes "many" meaningful.

**Narrative order only.** The **build order**: Address (Phase 1) → Benefits (Phase 2) → RFP (Phase 3) → maturity (Phase 4). Every demo runs on the **deployed GCP path** inside the [[bridge-zones|network zones]] — the managed services and trust boundary are part of what's demonstrated.

## Read next
- [[bridge-address-demo|Address demo]] — the Phase-1 scenario, beat by beat, plus the build checklist
- [[bridge-benefits-demo|Benefits demo]] — the Phase-2 depth scenario: fan-out → normalize → compare → negotiate → bind
- [[bridge-rfp-demo|RFP demo]] — the Phase-3 breadth scenario: emergent Collect, added live, no redeploy
- [[bridge-stages|build phases]] — the four-phase sequence and what each delivers
- [[bridge-collect|Collect]] — the RFP demo's pattern (the breadth proof)
- [[bridge-open-questions|scope — minimal vs aspirational]] — the committed core, the vision beyond it, open decisions

## Related
- [[bridge|the Bridge]], [[bridge-patterns|patterns]]
