# Feature — Bridge Core

**Status:** ✅ Built (Release 1; local path, GCP adapters written + plan-tested, not yet deployed) · **Release:** 1 (Minimal Showcase) · **Spec:** `wiki/bridge.md`, `wiki/bridge-aggregate-model.md`, `wiki/bridge-seams.md`, `wiki/bridge-edges.md`, `wiki/bridge-dual-path.md`, `wiki/bridge-disposition.md`, `wiki/bridge-proactive.md`

The independent, reusable core — the platform showcase itself. Demos consume it without editing it; if a demo needs a core change, that change is generic and lives here (`wiki/bridge-demo-suite.md`).

## Scope (Release 1)
- Aggregate model — Exchange / task / session / party invariants (task = session, Exchange = A2A context, stable party reference)
- Seams + local and GCP adapters — Sessions, Task store, Exchange store, Skill registry, Scheduler
- Two edges — A2A inbound (Path A) + A2UI portal (Path B)
- Dual-path fulfillment — Path A validate-only, Path B extract
- Extraction seam — fixture + Gemini adapters; extraction graph with quality/confidence gates
- Disposition — simple gates, capped resubmission, HITL suspend/resume; classification + issuer canonicalization
- Classified ledger — append-only view over exchange tasks
- Proactive follow-up — Scheduler seam + SLA policy + virtual clock
- Skills loader — installs [Agent Skills format](https://agentskills.io) folders (`SKILL.md` + `assets/`); doctype vs process via `metadata.bridge-kind`; pattern as selector (no DSL); Agent-Card regeneration from installed skills

## Later releases
- Four-signal disposition, party memory, cold-inbound edge, Bridge-as-client/outbound, Document AI adapter, multi-tenancy, hardening (Release 3)

## Completed Work

All Release-1 core tasks delivered (`bridge/src/bridge/`), green on the local path (480 tests):

- **S1-core-1** Aggregate model — Exchange / task / session / party invariants (`aggregate/`).
- **S1-core-2** Seam interfaces + local adapters (Sessions, Task/Exchange store, Skill registry, Scheduler) + shared parity suite (`seams/`, `tests/seams/`).
- **S1-core-3** A2A edge (Path A inbound) + A2UI portal edge (Path B) + reference renderer (`edges/`).
- **S1-core-4** Dual-path fulfillment — Path A validate-only, Path B extract (`dual_path/`).
- **S1-core-5** Extraction seam + fixture adapter + extraction graph (quality/confidence gates) (`extraction/`).
- **S1-core-6** Disposition (gates, capped resubmission, HITL suspend/resume) + classification + issuer canonicalization (`disposition/`, `classification/`).
- **S1-core-7** Classified ledger — append-only view over exchange tasks (`ledger/`).
- **S1-core-8** Proactive follow-up — Scheduler seam + SLA policy + virtual clock (`proactive/`).
- **S1-core-9** Skills loader — Agent Skills format folders, doctype vs process via `metadata.bridge-kind`, pattern as selector (`skills/`).
- **S1-core-10** Mock → real Bridge swap behind the same A2A contract — agent core unchanged.
- **S2-infra-1..3** GCP seam adapters (Postgres task/exchange, Cloud Tasks, Agent Engine sessions, GCS skills), Gemini extraction adapter, authenticated A2A + Agent Identity (`seams/gcp/`, `extraction/gemini/`) — plan-tested, not yet run against a live project.
- **S2-core-1..2** Agent-Card regeneration from installed skills + live skill upload (no restart).

**Known gaps** (see `docs/tech-debt.md`): Google ADK is a declared dependency, not the runtime — the Phase-1 Collect loop is hand-rolled and framework-agnostic (ADK-ready). Document AI extraction and the Gemini classifier are `NotImplementedError` slots (Phase 4 / later). Gemini extraction is off by default (`fixture`) and unproven against the live API in CI.
