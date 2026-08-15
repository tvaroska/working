# ADR-0001 — Languages & Frameworks

- **Status:** Accepted
- **Date:** 2026-08-06
- **Resolves:** `PLAN.md` → S0-docs-2
- **Context:** `wiki/bridge-gcp-substrate.md`, `wiki/bridge-seams.md`, `docs/architecture.md`

## Context

The Bridge is a showcase of the **Gemini Enterprise Agent Platform** and a candidate managed product. The platform, protocols, and delegated services are already fixed by the design spec: Agent Runtime, Skill Registry, Memory Bank, Agent Gateway, Agent Identity; A2A + A2UI; Gemini + Document AI extraction; Cloud Tasks; Terraform. What was open is the **application** stack — backend language/framework, frontend framework, data store, graph-durability approach.

## Decision

A two-language stack, chosen to run *with* the platform it showcases rather than against it.

| Layer | Choice |
|---|---|
| **Core + processing agents** | **Python 3.12+** |
| **Agent framework** | **Google ADK** (Agent Development Kit) — native to the Agent Runtime [ADK-ready, not yet ADK-hosted — see Implementation status] |
| **Edge / HTTP surface** | **FastAPI** (async) — A2A server, A2UI endpoints, HITL resume webhooks not covered by ADK |
| **Schemas / validation** | **Pydantic** — doctype schemas, Gemini constrained JSON, per-document validation, disposition signals |
| **Data store** | **Cloud SQL for PostgreSQL** — indexed relational keys + JSONB document column; one implementation local + GCP |
| **Frontend (3 surfaces + A2UI renderer)** | **React + TypeScript + Vite**, MUI (Material UI) [amended — see Implementation status] |
| **Fulfillment-graph durability** | **ADK / runtime session durability** — graph modelled as explicit persisted states on the session; suspend/resume for HITL recovered from the persisted session [Phase 1: HITL is app-owned task-parking (`INPUT_REQUIRED` + resume endpoint), not ADK `RequestInput` — see Implementation status] |
| **IaC** | **Terraform** |
| **Tests** | **pytest** (the shared seam suite, run against local + GCP adapters) · **Playwright** (frontend/e2e) |
| **Skills validation** | **`skills-ref validate`** on every skill folder (Agent Skills format) in CI |
| **Tooling** | **uv** (Python) · **pnpm** (frontend) |

## Rationale

- **Python + ADK** — Agent Runtime (Vertex Agent Engine), the A2A SDK, the Vertex/Gemini SDK, and the Document AI client are all Python-first. Using ADK makes the platform itself part of the demonstration.
- **PostgreSQL** matches the seams spec verbatim: queryable keys indexed, flexible aggregate parts in a document (JSONB) column — the same relational implementation serves the local and GCP adapters, with a managed-relational upgrade path and no rewrite.
- **React/TS/Vite** — the natural second language for the three actor surfaces and the A2UI reference renderer; nothing in the design pushes toward a heavier framework.
- **Runtime session durability over a graph engine** — consistent with the "no bespoke engine; delegate behind a seam only if ever needed" principle (`wiki/bridge-patterns.md`). Fewer dependencies, stays on-platform.

## Consequences / risks

- **A2UI maturity.** A2A has stable SDKs; **A2UI is newer** and may lack a mature Python/TS library. Budget for the reference renderer + a protocol shim being partly hand-rolled (the spec already treats the renderer as demo furniture, so this is consistent).
- **Graph-durability revisit trigger.** If the fulfillment graph outgrows explicit session-persisted states (deep branching, parallel legs), reconsider a checkpointing engine (e.g. LangGraph) *behind a seam* — do not hand-roll a workflow engine.
- **Two languages** means two toolchains (uv, pnpm) and a typed contract at the edge — acceptable and conventional for a backend/frontend split.

## Alternatives considered

- **TypeScript/Node backend** — one language across the stack, but weaker platform-SDK support (Agent Runtime, Document AI) means more glue and friction with the very platform being showcased. Rejected.
- **Python with raw SDKs, no ADK** — more control, but forgoes the native runtime integration that is part of the showcase. Rejected as the default; revisit only if ADK proves limiting.
- **Next.js frontend** — SSR/routing batteries included, heavier than needed for internal dashboards + one portal. Rejected.
- **LangGraph for the fulfillment graph** — capable, but an extra dependency/concept before it is needed. Deferred (see revisit trigger).

## Implementation status (2026-08-10)

This ADR records the *decision*; it does not assert the decision is fully realized. As of Phase 1:

- **Google ADK is a declared dependency, not the agent runtime — the "ADK showcase" framing is aspirational for Phase 1.** The Address Collect loop is a hand-rolled, framework-agnostic `async` loop (`agents/src/agents/address/agent.py`), decoupled behind a `BridgeClient` transport port — ADK-ready, but not hosted under ADK, and **no ADK graphs execute** (orchestration is deterministic `async` methods). **HITL is not ADK `RequestInput`:** it is app-owned task-parking — a suspended `TaskStatus.INPUT_REQUIRED` task (`bridge/src/bridge/aggregate/task.py`) resolved out-of-band by an A2A resume endpoint (`bridge/src/bridge/edges/a2a/edge.py` `resolve_suspended` → `DispositionService.resume`). The only live `google.adk` use is the GCP session-store seam (`bridge/src/bridge/seams/gcp/sessions.py`). This ADR's table cells are annotated "ADK-ready" to match. Wiring real ADK (host the loop as an ADK graph, adopt `RequestInput` for HITL) — or keeping the reframed pitch — is tracked in `docs/tech-debt.md` §1.
- **Fulfillment-graph durability** via runtime-session persistence is built for the local path; the Agent-Engine-backed variant is written but not yet applied on GCP.
- **Frontend UI library is MUI (Material UI), not the originally-decided Tailwind + shadcn/ui.** All four surfaces (`frontend/{provider-portal,ops-dashboard,timewarp,agent-console}`) depend on `@mui/material` + `@emotion`; none use Tailwind or shadcn. The original decision was recorded before the surfaces were built and was not revisited when the actual choice diverged. The table above is amended to reflect what is built; MUI's batteries-included component set (data grid, transport controls, badges) fit the dashboard-heavy surfaces with less setup than a Tailwind + shadcn assembly. Tracked in `docs/tech-debt.md` §8.

## Note — LangGraph in the Benefits demo (not the core)

LangGraph *is* used in the project, but only outside the Bridge core: the Benefits demo (Phase 2) builds one **simulated carrier counterparty agent** in LangGraph (alongside one in ADK) to prove **A2A framework interoperability** — the ADK-built Bridge negotiates multi-turn with a non-ADK agent. This is demo furniture in the external zone, has no bearing on the core's own framework choice above, and does not contradict the "LangGraph deferred for the fulfillment graph" decision. See `wiki/bridge-benefits-demo.md`, `docs/features/benefits-demo.md`.
