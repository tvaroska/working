# A2A Document Bridge

> A servicer's agent asks once and receives documentation already **gathered, chased, normalized, and ready to act on** — collected from the outside world so the internal agent never touches it. The durable value is **mediation**, not extraction: the Bridge owns the multi-turn, multi-party, multi-format relationship end to end, and delegates PDF → JSON to dedicated services behind a swappable seam.

This repository is the **design source of truth** for the Bridge. It is documentation-first: the code is built against this spec.

- **Start here:** [`wiki/bridge.md`](wiki/bridge.md) — the root of the spec; every topic links out from there.
- **Decisions:** [`docs/decisions/`](docs/decisions) — the ADRs (stack, thresholds, exchange model, signals, extraction binding, long-running lifecycle).
- **Active build plan:** [`PLAN.md`](PLAN.md) — the working execution tracker (current milestone + checklist).
- **Roadmap:** [`docs/roadmap.md`](docs/roadmap.md) — the four-phase release sequence and where stakeholder validation is recommended.
- **Carry-forward knowledge:** [`docs/lessons-learned.md`](docs/lessons-learned.md) — the non-obvious invariants and config values to honor during the build.
- **Feature briefs:** [`docs/features/`](docs/features) — one page per feature area.

## What it is

A **platform showcase** for the Gemini Enterprise Agent Platform, and a candidate managed mediation product. It runs on the platform natively — **using the platform natively *is* the demonstration**:

- **Google ADK** is the agent runtime (`LlmAgent` + tools, artifacts, long-running HITL).
- **A2A** is the agent-facing protocol, spoken canonically via the standard `a2a-sdk`.
- **A2UI** is the human-facing edge (content, not pixels).
- **GCP Agent Platform** (Agent Runtime, Skill Registry, Memory Bank, Agent Gateway, Agent Identity) is the production environment; a **local PC** is the development environment. Every managed-service boundary is a **seam** with a local adapter and a GCP adapter, verified by one shared test suite.

These three platform bets — **ADK-native runtime, canonical A2A, GCP Agent Platform for prod / local for dev** — are hard requirements of the design, not aspirational stages. See [`docs/decisions/adr-0001-stack.md`](docs/decisions/adr-0001-stack.md).

## Core vs. demos

The **Bridge core** is an independent, reusable project — the showcase itself. Each demo (Address, Benefits, RFP) is a self-contained implementation — skills plus a thin driver — that consumes the core **without changing it**. That separation is the reusability claim. See [`wiki/bridge-demo-suite.md`](wiki/bridge-demo-suite.md).

## Stack

Python 3.12+ · Google ADK · FastAPI · Pydantic (core + agents) · React + TypeScript + Vite + MUI (three surfaces + A2UI renderer) · Cloud SQL for PostgreSQL · Terraform · pytest + Playwright · uv + pnpm · `a2a-sdk`.

## Status

Design consolidated; **implementation starting** at Milestone 0 (contract tracer bullet) — see [`PLAN.md`](PLAN.md). The four-phase roadmap (Address → Benefits → RFP → Maturity) is in [`docs/roadmap.md`](docs/roadmap.md).

**Contributing / dev setup:** see [`CONTRIBUTING.md`](CONTRIBUTING.md) — `make setup` then `make test`.
