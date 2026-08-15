---
type: atom
related:
  - "[[bridge-demo-suite]]"
  - "[[bridge-open-questions]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# Build Phases

> Four phases, each ending on a runnable, demoable beat. **Phase 1 is the [[bridge-open-questions|minimal showcase]]**; Phases 2–4 are the aspirational build-out. The phases below map 1:1 onto the minimal-vs-aspirational split — that scope note is authoritative.

- **Phase 1 — Minimal showcase (Address).** The pull spine end to end on the deployed Agent Platform, carrying a **bounded [[bridge-collect|Collect]]**: prove an address with either **one government ID** (driver license, passport, national ID) or **two bills from different companies**. Dual-path fulfillment, both [[bridge-edges|edges]], the [[bridge-fulfillment-graph|extraction graph]] behind an engine-swappable [[bridge-seams|extraction seam]] (fixture + Gemini), simple-gate [[bridge-disposition|disposition]] **plus doctype classification** (classify each arriving doc against the candidate-doctype **label space** — gov ID vs utility bill — and extract the issuer), a **classified ledger** of accepted docs over which the **agent owns the satisfaction *decision*** (the OR, the count-to-two, and the distinct-issuer check are the agent's — sense B; the Bridge classifies, dispositions, best-efforts an advisory assessment of completeness from the skill's prose satisfaction description, and chases the delta, but pre-allocates **no typed slots**), [[bridge-proactive|proactive follow-up]] (Scheduler seam + SLA policy — the chase now has real content: the missing second bill), the managed-service [[bridge-seams|seams]] and [[bridge-zones|two-zone network model]], doctype + process [[bridge-skills|skills]]. Builds the **Bridge core** plus its first demo, Address ([[bridge-address-demo|scenario & build checklist]]) — and lands a *bounded* slice of the Collect pattern (a static, known-up-front satisfaction rule) that Phase 3 generalizes. Mediation on the platform, one demo — the committed core. *[Minimal]*
- **Phase 2 — Depth (Benefits).** The Benefits implementation ([[bridge-benefits-demo|scenario & build checklist]]) carried end to end: program context over N isolated legs, multilingual extraction + FX normalization, the benefits-quote pack, program-view comparison + declared-rule standard-gap, the negotiate + versioned revise loop, per-leg bind → program rollup → audit. Proves "one comparable view." A single live doctype-add here is the early down-payment on Phase 3. *[Aspirational]*
- **Phase 3 — Breadth (RFP / Collect).** The RFP implementation ([[bridge-rfp-demo|scenario & build checklist]]) — a different industry that **generalizes** the [[bridge-collect|Collect]] pattern Address introduced bounded: emergent, conditional, N-supplier requirements, added **live** to the running core with no redeploy — the reusability headline. Extends the Phase-1 Collect slice from a fixed satisfaction rule to **agent-mutated Requirements** at runtime (the same multi-turn loop, a smarter per-turn reply) and adds RFP doctype/process skills — **no new pattern, no code change**, since Collect is a built-in flow. Also lands the **showcase runner** — one core, all demos loaded, concurrent exchanges — the proof of multi-use-case coexistence. *[Aspirational]*
- **Phase 4 — Platform maturity & hardening.** Core-only, no new demo — the growth surface: four-signal [[bridge-disposition|disposition]] (a pluggable signal provider, wrong-doc detection), [[bridge-party-memory|party memory]] consumers, the cold-inbound Extract edge, Bridge-as-client + outbound + real SLA nudges, true dual-path Path B → Path A migration, managed A2A task-store adoption as it ships, the **Document AI extraction adapter** (the extraction-seam swap proof), per-customer multi-tenancy, and hardening (VPC Service Controls, customer-managed encryption keys, Security Command Center, observability + eval). *[Aspirational]*

**How each phase gets built.** Each phase splits into **two sprints** — an agent-first local sprint and a GCP + Terraform sprint — with a mock Document Bridge and a three-surface frontend from Sprint 1. See [[bridge-implementation-plan|the implementation plan]] and [[bridge-frontend|frontend]].

## Related
- [[bridge-demo-suite|demo implementations]], [[bridge-implementation-plan|implementation plan]], [[bridge-frontend|frontend]], [[bridge-open-questions|scope — minimal vs aspirational]]
