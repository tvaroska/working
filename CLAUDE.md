# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status — read this first

This is a **documentation-first** repository. As of this writing there is **no application code and no build tooling** — only the design spec (`wiki/`, `docs/`) and the active build plan. Implementation is *starting*, not started. Do not go looking for source, a `pyproject.toml`, or tests; they don't exist yet. The first executable work is **Milestone 0** (`PLAN.md`).

Orientation order:
1. `README.md` — the front door and the three platform bets.
2. `PLAN.md` — the **active development tracker**: current milestone + checklist. Keep it current as work lands.
3. `docs/roadmap.md` — release-level sequence (4 phases × 2 sprints).
4. `wiki/bridge.md` — the **root of the design spec**; every topic links out from there.
5. `docs/decisions/` — the ADRs (binding decisions).
6. `docs/lessons-learned.md` — non-obvious invariants and concrete config values to honor during the build.

## What this system is (the big picture)

The **A2A Document Bridge** is a mediation layer: a servicer's agent "asks once" and receives documents already **gathered, chased, normalized, and ready to act on** from external parties. The durable value is **mediation** (owning the multi-turn, multi-party, multi-format relationship), **not extraction** (PDF→JSON), which is delegated to swappable engines behind a seam.

Three architectural spines that only make sense read together:

- **Core vs. demos.** The **Bridge core** (`bridge/`, intended) is an independent, reusable project — the showcase itself. Each demo (Address → Benefits → RFP) is a **self-contained implementation = skills + a thin driver** that consumes the core *without changing it*. That separation is the reusability claim. "The difference between demos is the agent, not the Bridge."
- **Seams.** Every managed-service boundary (Sessions, Task store, Exchange store, Skill registry, Scheduler, Extraction) is a **seam with a local adapter and a GCP adapter, verified by one shared test suite**. Local PC is the dev environment; GCP Agent Platform is prod. The interface is designed once (Sprint A); only the GCP-backed impl + its Terraform land later (Sprint B). The mock→real and local→GCP swaps must be **no-ops for the agent**.
- **Aggregate model.** exchange = the A2A context · each leg's work = an **A2A task** (durable, no TTL, woken by a party turn / clock alarm / HITL resume) · task ≈ ADK session · a stable counterparty (party) reference. Two edges: **A2A** (agents, canonical `a2a-sdk`) and **A2UI** (humans, content-not-pixels). Read `wiki/bridge-aggregate-model.md` first.

## Three hard platform bets (day one, non-negotiable — ADR-0001)

Using the platform natively *is* the demonstration, so these are requirements from the first commit, not stages to grow into:
1. **ADK-native runtime** — the Bridge is an `LlmAgent` with tools; extraction is an `AgentTool` subagent; HITL is a `LongRunningFunctionTool`; documents are versioned ADK artifacts; `InMemory…` (local) ↔ `Gcs`/Vertex (deploy) backends swap with no agent-code change.
2. **Canonical A2A** via the standard `a2a-sdk` — JSON-RPC 2.0, spec methods (`message/send`, `message/stream`, `tasks/get`/`list`/`cancel`/`resubscribe`). Domain types (`CollectRequest`, `ExchangeTurn{CollectionStatus}`, `RequirementsList`, `LedgerEntry`) travel **inside** A2A parts/artifacts. No bespoke REST dialect.
3. **GCP Agent Platform for prod / local PC for dev.**

Governing principle: **prefer the platform-native construct over bespoke plumbing, every time**; a custom layer needs a specific, recorded justification (`wiki/bridge-adk.md`).

## Invariants that will bite you (see `docs/lessons-learned.md` for the full list)

- **LLM routes, code decides.** The KYC accept/reject verdict and the completeness ("done") decision are **deterministic pure functions** exposed as authoritative tools (`run_disposition_gate`, `is_satisfied`). **A model may never mint a KYC acceptance.** Preserve this split.
- **Mock↔real parity is terminal-outcome, not ledger-identical.** The mock Bridge and real Bridge legitimately diverge turn-by-turn; parity tests assert the same *destination* (terminal reason + accepted-issuer set), never a step-by-step ledger match. The **mock is a permanent contract double, not throwaway.**
- **The classified ledger has no timestamp** — in-memory ordering rides on dict insertion order. Any relational/GCP backend returns rows unordered, so the persistent adapter **needs a deterministic sort key**.
- **`bridge/` never imports `agents/`.** Canonicalization/parity between them holds *by discipline*, enforced by the shared test suite.
- **Issuer canonicalization:** `"Power Co."` → `power-co` ("co" is not a suffix; only `Ltd/Inc/LLC/GmbH/…` are stripped).
- **Escalation ≠ rejection**; `resubmit` is deliberately non-resumable (it awaits a fresh document, not a human decision).
- **Trust boundary is permissive-by-default** (per-party scoping enforced only under `strict=True`) — a known footgun; change it only knowingly.

## Intended stack & commands (ADR-0001)

No toolchain is scaffolded yet — establishing it is task **M0.1** in `PLAN.md`. When you scaffold, use:

- **Backend/core/agents:** Python 3.12+, **uv**. `google-adk >= 2.7.0, < 3`, `a2a-sdk`, FastAPI, Pydantic. `uv run pytest` for the shared seam suite (run against local *and* GCP adapters); `uv run pytest path::test_name` for a single test; **ruff** for lint.
- **Frontend:** React + TypeScript + Vite + MUI, **pnpm**. Playwright for e2e.
- **Data:** Cloud SQL for PostgreSQL (one relational impl serving local + GCP adapters). **IaC:** Terraform.
- **Skills:** `skills-ref validate` on every skill folder (Agent Skills format) in CI.
- **SDK version risk:** `google-adk` and `a2a-sdk` are load-bearing; pin them and track `[EXPERIMENTAL]` surfaces (e.g. ADK `ResumabilityConfig`).

Build sequence is **agent-first**: each phase's processing agent (which defines the A2A contract) is built before the Bridge code for that phase.

## Working conventions for the docs

- `wiki/` uses Obsidian-style `[[wiki-links]]`. Front-matter `status: review` denotes **doc-review** status, **not** build status — don't treat it as "shipped."
- The design was deliberately reset to a clean slate: **no build-status claims** (test counts, "✅ Built", "code complete", sign-offs-as-done). Everything is `📋 Planned`. Do not reintroduce premature "done" claims into the spec; track real progress in `PLAN.md` and commit history instead.
- Binding decisions live in `docs/decisions/` (ADRs). If you change a decision, update the ADR — don't contradict it elsewhere.
- Concrete demo values (party `jordan-lee`, doctypes `gov-id` / `utility-bill`, canonical issuers) and eval fixtures live in `docs/lessons-learned.md §C1` and `wiki/evals/address/`.
