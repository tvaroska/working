---
type: atom
related:
  - "[[bridge-patterns]]"
  - "[[bridge-fulfillment-graph]]"
  - "[[bridge-skills]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# Disposition

> Decide whether a submission is **acceptable** — right type, complete, legible, rule-valid — and route it: accept / clarify / reject / request-more. Not merely legible.

**The mediator boundary — two senses of "judgment."** Neither is forbidden to the Bridge outright; the split is *what authorizes the call*:

- **Sense A — evaluate one artifact against *declared* rules → flags.** Legible? Right type? Meets declared coverage? Unexpired? This *is* disposition. The rules are pack-declared (agent-overridable), never Bridge-invented; the Bridge **surfaces**. → **Bridge**.
- **Sense B — decide requirements, completeness of a *set*, or acceptance of a *deal*.** Is the casefile done? Do we bind this quote? → **the app decides; the Bridge best-efforts.** The Bridge is no longer completeness-blind: it interprets a satisfaction rule the skill carries **as prose** (the Address `OR`/count/distinct-issuer is exactly this — a description, not a formal language), *proposes* what's still outstanding, and chases it. But it has **no deterministic rule and no final word on enforcement** — the app makes the call and must always be ready to. Binding a *deal* is squarely the app's. → **app-decides, Bridge-best-effort.**

**Phase 1 — simple gates + classification.** The confidence-only special case: a quality gate (below the resubmit threshold → resubmit) and a confidence gate (at or above the auto-approve threshold with no flags → auto-approve; else HITL). Because the Address warm-up is a [[bridge-collect|bounded Collect]], Phase 1 also lands **doctype classification** — classify each arriving doc against the candidate-doctype **label space** (gov ID vs utility bill) or flag it wrong/unrequested, and extract **plus canonicalize** the bill's **issuer** (e.g. `PowerCo` / `Power Co.` / `PowerCo Ltd` → `power-co`) so the agent gets clean, comparable values. That split is the boundary in miniature: **per-document issuer normalization is the Bridge (sense A)**; the **cross-document distinct-issuer decision is sense B** — the **app decides** it, while the Bridge, reading the Address skill's prose rule, makes a **best-effort** assessment of it (the OR, count-to-two, distinct-issuer check over the classified ledger) and chases the gap. This is the `type match` signal arriving early in a bounded form; the Bridge classifies, dispositions, records each doc in a **classified ledger**, and best-efforts the set assessment — advisory, never enforced — and pre-allocates no typed slots. **Phase 2 adds declared-rule standard-gap** — flag each normalized quote against the program standard via rules declared in the pack (sense A), routing to negotiation.

**The target — a four-signal model** (deferred, post-golden), because one confidence scalar can't separate *unreadable* from *readable-but-wrong* from *readable-right-but-expired*:

| Signal | Question | Routes to |
|---|---|---|
| Legibility | Can we read it? | resubmission |
| Type match | Right kind? | reject / clarify |
| Extraction confidence + fields requiring review | Read correctly? | HITL vs auto-approve |
| Completeness + failed rules | Complete + rule-valid? | request-more / reject |

A pluggable signal provider (mock / model-reported / computed) and wrong-doc detection are the growth direction beyond the minimal cut. *[Aspirational]*

## Related
- [[bridge-patterns|patterns]], [[bridge-fulfillment-graph|extraction graph]], [[bridge-skills|skills]]
