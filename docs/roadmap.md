# Roadmap — A2A Document Bridge

> The build plan across releases. The design spec is in `wiki/` (start at `wiki/bridge.md`); this roadmap groups features into recommended sprints and flags where stakeholder validation is recommended.
>
> **Build sequence:** 4 phases × 2 sprints = 8 sprints. Each phase is **agent-first**: Sprint A proves behaviour locally; Sprint B adds GCP adapters + Terraform and deploys. Every managed-service boundary is a seam with a local adapter and a GCP adapter, verified by one shared test suite. See `wiki/bridge-implementation-plan.md`.
>
> **Status:** clean-slate build — **not yet started**. The three platform bets (ADK-native runtime, canonical A2A via `a2a-sdk`, GCP Agent Platform for prod / local PC for dev) are hard requirements from the first commit (`docs/decisions/adr-0001-stack.md`).

Status legend: ✅ complete · 🚧 in progress · 📋 planned

---

## Release 1 — Minimal Showcase (Address) 📋

**Goal:** Prove the thesis — a servicer's agent asks once and receives documentation gathered, chased, normalized, and ready to act on — running on the deployed platform inside the two-zone trust boundary.

**Feature areas** (detail in `docs/features/`):
- 📋 Bridge core — aggregate model, seams, both edges, dual-path, disposition, classified ledger, proactive follow-up (`docs/features/bridge-core.md`)
- 📋 Processing agents + mock Bridge contract double (`docs/features/processing-agents.md`)
- 📋 Frontend — three surfaces + time-warp (`docs/features/frontend.md`)
- 📋 GCP substrate + Terraform (`docs/features/gcp-infra.md`)
- 📋 Address demo + live doctype-add down-payment (`docs/features/address-demo.md`)

**Recommended sprints:**
- **Milestone 0 — Contract Tracer Bullet** — the thinnest end-to-end slice to validate the input/output design: an ADK `LlmAgent` sends one `CollectRequest`; a mock Bridge accepts it, holds ~10s (`message/send` → `Task{WORKING}` → `tasks/get` poll → `COMPLETED`), and returns an `id` + structured info drawn from `wiki/evals/address/`. No Collect loop, disposition, extraction, frontend, or GCP. The contract models + mock persist into Sprint 1 (`docs/milestone-0-contract-tracer.md`).
- **Sprint 0** — scaffolding, CI, dev env, stack + open-decision sign-off
- **Sprint 1** — Phase 1 local: Address agent, mock Bridge, real Bridge (local adapters), frontend v1, fixtures, shared suite. The Address agent runs as an `LlmAgent` on ADK; the A2A edge speaks canonical A2A via `a2a-sdk` from the start.
- **Sprint 2** — Phase 1 GCP: GCP adapters, Terraform base infra, Gemini extraction, live doctype-add, deploy + manual exit checklist on the deployed path

**User validation:**
- End of Milestone 0 — **contract sign-off**: review the `CollectRequest` / `CollectionStatus` / `LedgerEntry` shapes and the `tasks/get` async surface before Sprint 1 builds on them.
- End of Sprint 1 — internal walkthrough: Address runs locally, agent unchanged across mock→real swap.
- End of Sprint 2 — **exec demo** on the deployed path: two-run live doctype-add (config-only platform proof + separately-narrated agent-policy beat), time-warp escalation climax, clean-artifact delivery. This is the funding-gate moment.

---

## Release 2 — Depth + Breadth (Benefits, RFP) 📋

**Goal:** Turn the platform proof into the product story — one comparable view (depth) and industry-agnostic reuse added live (breadth, the headline).

**Feature areas:**
- 📋 Benefits demo — fan-out → normalize (FX + multilingual) → compare/standard-gap → negotiate/revise → bind → rollup; **framework-diverse simulated carrier agents (ADK + LangGraph) proving A2A interoperability** (`docs/features/benefits-demo.md`)
- 📋 RFP demo — emergent/agent-mutated Collect at N-supplier scale, added live with no redeploy (`docs/features/rfp-demo.md`)
- 📋 Showcase runner — one core, all demos loaded, concurrent exchanges, one card + one dashboard

**Recommended sprints:**
- **Sprint 3** — Phase 2 local: Benefits agent (negotiate/bind), frontend v2 (comparison view), real Bridge delta (programs, Negotiate flow, FX/multilingual, bind→rollup); **simulated carrier agents — one Google ADK, one LangGraph — as Path-A A2A counterparties (interoperability proof)**
- **Sprint 4** — Phase 2 GCP: program-scale Gateway addressing, multilingual Gemini on real docs, Terraform delta; manual test (4 carriers, 3 currencies/languages, live negotiate, bind→rollup) + one live doctype-add
- **Sprint 5** — Phase 3 local: RFP agent (emergent, mutating Requirements), frontend v3 (Requirements mutation, casefile view), emergent Collect + open-set classification + showcase runner
- **Sprint 6** — Phase 3 GCP: **full** live skill-add to the running deployed core (Terraform delta ≈ none — the reusability proof); showcase runner on GCP; add RFP live while Address/Benefits exchanges are in flight

**User validation:**
- End of Sprint 4 — "one comparable view" arc on the deployed path, including the **ADK ↔ LangGraph A2A interoperability** beat (a non-ADK carrier agent negotiating multi-turn with the Bridge).
- End of Sprint 6 — **the reusability headline**: new industry = skills, not infra; one card + one dashboard serve all three demos concurrently. Primary sales/demo asset.

---

## Release 3 — Maturity & Hardening 📋

**Goal:** Production-grade, multi-tenant, engine-swappable, observable. Core-only, no new demo.

**Feature areas:**
- 📋 Four-signal disposition (pluggable signal provider, wrong-doc detection)
- 📋 Party memory (Memory Bank consumers)
- 📋 Cold-inbound Extract edge (email adapters, open-set classification, correlation-miss triage)
- 📋 Bridge-as-client + outbound + real SLA nudges; true Path B → Path A migration preserving history
- 📋 Document AI extraction adapter (the extraction-seam swap proof: Gemini ↔ Document AI parity)
- 📋 Per-customer multi-tenancy; managed A2A task-store adoption
- 📋 Hardening — VPC Service Controls, CMEK, Security Command Center, BigQuery observability + eval

**Recommended sprints:**
- **Sprint 7** — Phase 4 local: disposition signals, party-memory consumers, cold-inbound edge, Document AI adapter, frontend v4 (Architecture X-Ray), B→A migration
- **Sprint 8** — Phase 4 GCP: Memory Bank, managed A2A task-store swap, Document AI processors, multi-tenancy, real outbound channels; hardening Terraform; security/tenancy/observability manual pass

**User validation:**
- End of Sprint 8 — security posture review, tenancy isolation, engine swap on GCP, observability dashboards.

---

## Cross-cutting risks

- **Phase 1 is front-loaded** — Sprint 2 carries all base infra; Sprints 4/6 are deliberately light on infra, and that lightness *is* the reusability proof.
- **Sprints 5–6 (RFP) are the most cuttable yet bear the headline** — if schedule slips, protect the live-add beat (Sprint 6) even if emergent-Collect depth (Sprint 5) is trimmed.
- **The mock Bridge is a maintained artifact, not throwaway** — it is the permanent agent-side test double.
- **Live-add pulled forward** — a minimal live doctype-add lands in Sprint 2 (Release 1) as the down-payment on the Sprint-6 headline; keep it minimal so it doesn't absorb the front-loaded Terraform sprint.
- **SDK version risk** — `google-adk` and `a2a-sdk` are load-bearing from day one; pin versions and track `[EXPERIMENTAL]` surfaces (`docs/decisions/adr-0001-stack.md`).
