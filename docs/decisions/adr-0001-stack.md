# ADR-0001 — Languages, Frameworks & Platform Bets

- **Status:** Accepted
- **Date:** 2026-08-06 (platform-native runtime + canonical A2A folded in 2026-08-14)
- **Context:** `wiki/bridge-gcp-substrate.md`, `wiki/bridge-seams.md`, `wiki/bridge-adk.md`, `wiki/bridge-a2a-edge.md`, `docs/roadmap.md`

## Context

The Bridge is a showcase of the **Gemini Enterprise Agent Platform** and a candidate managed product. The platform, protocols, and delegated services are fixed by the design spec: Agent Runtime, Skill Registry, Memory Bank, Agent Gateway, Agent Identity; A2A + A2UI; Gemini + Document AI extraction; Cloud Tasks; Terraform. What was open is the **application** stack — backend language/framework, frontend framework, data store, graph-durability approach — and how firmly the platform bets are held.

Because **using the platform natively *is* the demonstration**, the platform bets are treated as **hard requirements from the first commit**, not stages a local prototype grows into. There is no "framework-agnostic interim" that converges later: the runtime is ADK, the agent edge speaks canonical A2A, and production is the GCP Agent Platform with a local PC as the dev environment.

## Decision

A two-language stack, chosen to run *with* the platform it showcases.

| Layer | Choice |
|---|---|
| **Core + processing agents** | **Python 3.12+** |
| **Agent runtime** | **Google ADK** (`google-adk >= 2.7.0, < 3`) — native to the Agent Runtime. The Bridge is an `LlmAgent` (`document_bridge`) with tools; extraction is an `AgentTool` subagent; HITL is a `LongRunningFunctionTool`; documents are versioned ADK artifacts; sessions/artifacts swap `InMemory…` (local) ↔ `Gcs`/Vertex (deploy). See `wiki/bridge-adk.md`. |
| **Agent protocol (A2A edge)** | **Canonical A2A on the standard `a2a-sdk`** — JSON-RPC 2.0, spec methods (`message/send`, `message/stream`, `tasks/get`/`list`/`cancel`/`resubscribe`), A2A `Message`/`Task`/`Artifact`/`Part`. The domain types (`CollectRequest`, `ExchangeTurn{CollectionStatus}`, `RequirementsList`, `LedgerEntry`) are the payload carried inside A2A parts/artifacts. No bespoke REST dialect. See `wiki/bridge-a2a-edge.md`. |
| **Edge / HTTP surface** | **FastAPI** (async) — A2UI endpoints and the scoped artifact-fetch endpoint not covered by the A2A SDK. |
| **Schemas / validation** | **Pydantic** — doctype schemas, Gemini constrained JSON, per-document validation, disposition signals. |
| **Data store** | **Cloud SQL for PostgreSQL** — indexed relational keys + JSONB document column; one implementation for the local and GCP adapters. |
| **Frontend (3 surfaces + A2UI renderer)** | **React + TypeScript + Vite**, **MUI (Material UI)**. |
| **HITL / graph durability** | **ADK runtime session durability** — HITL suspend/resume via `LongRunningFunctionTool` + id-matched `FunctionResponse`, recovered from the persisted `SessionService`. |
| **IaC** | **Terraform** |
| **Tests** | **pytest** (the shared seam suite, run against local + GCP adapters) · **Playwright** (frontend/e2e). |
| **Skills validation** | **`skills-ref validate`** on every skill folder (Agent Skills format) in CI. |
| **Tooling** | **uv** (Python) · **pnpm** (frontend). |

## Rationale

- **Python + ADK** — Agent Runtime (Vertex Agent Engine), the `a2a-sdk`, the Vertex/Gemini SDK, and the Document AI client are all Python-first. Using ADK natively makes the platform itself part of the demonstration. The governing principle — *prefer the platform-native construct over bespoke plumbing, every time; a custom layer needs a specific, recorded justification* (`wiki/bridge-adk.md`) — is why the runtime is stock ADK and the edge is the stock A2A SDK rather than hand-rolled equivalents.
- **Canonical A2A** — the value of the edge is that *any* A2A-conformant agent can talk to the Bridge. A bespoke REST dialect would only interoperate with our own client and would hide the very protocol the showcase advertises. Spec conformance is what makes "one shared Bridge, many apps over A2A" real beyond our own fleet.
- **The one inversion we keep** — the KYC accept/reject of a genuine candidate document stays a **deterministic, auditable pure function**, exposed to the `LlmAgent` as an authoritative tool (`run_disposition_gate`). The model routes intent; the gate decides. A model may never mint a compliance acceptance. This is standard agent+tool shape, not a deviation from "as standard as possible."
- **PostgreSQL** matches the seams spec: queryable keys indexed, flexible aggregate parts in a JSONB column — the same relational implementation serves local and GCP adapters, with a managed-relational upgrade path and no rewrite.
- **React/TS/Vite + MUI** — the natural second language for the three actor surfaces and the A2UI reference renderer; MUI's batteries-included component set (data grid, transport controls, badges) fits the dashboard-heavy surfaces with less setup than a hand-assembled utility-CSS stack.
- **Runtime session durability over a bespoke graph engine** — consistent with the "no bespoke engine; delegate behind a seam only if ever needed" principle (`wiki/bridge-patterns.md`). Fewer dependencies, stays on-platform.

## Consequences / risks

- **SDK maturity / version pinning.** `google-adk` and `a2a-sdk` are load-bearing; their release cadence and any `[EXPERIMENTAL]` surfaces (e.g. ADK `ResumabilityConfig`, used by long-running pause/resume) must be tracked and pinned.
- **LLM non-determinism in routing.** The agent's *routing* is probabilistic, but the *compliance verdict* is not — it comes from the pure gate tool the model cannot overrule. Offline tests drive the agent with a scripted model double and assert terminal-disposition parity with the deterministic gate.
- **A2UI maturity.** A2A has stable SDKs; **A2UI is newer** and may lack a mature Python/TS library. Budget for the reference renderer + a protocol shim being partly hand-rolled (the spec already treats the renderer as demo furniture). The `a2a-sdk` decision governs the **A2A** edge only; the A2UI portal keeps its own transport until a comparable decision is made.
- **Cost/latency.** An LLM turn per disposition adds latency and token cost a pure function did not — justified by the off-script-intent capability (deletion requests, wrong/unrelated files); the gate tool keeps the expensive path off the deterministic core.
- **Two languages** means two toolchains (uv, pnpm) and a typed contract at the edge — acceptable and conventional for a backend/frontend split.
- **Graph-durability revisit trigger.** If the fulfillment graph outgrows explicit session-persisted states (deep branching, parallel legs), reconsider a checkpointing engine (e.g. LangGraph) *behind a seam* — do not hand-roll a workflow engine.

## Alternatives considered

- **Python with raw SDKs / a hand-rolled agent loop, no ADK.** Rejected: forgoes the native runtime integration that is the showcase, and hides the platform behind bespoke plumbing the principle forbids.
- **A bespoke plain-JSON REST mapping for the agent edge** (borrowing A2A concepts without the wire protocol). Rejected: defeats A2A interoperability — the whole reason to have an A2A edge — and hand-rolls the protocol the showcase advertises.
- **An `LlmAgent` that owns accept/reject itself.** Rejected: a model improvising KYC acceptance is not auditable; the gate stays authoritative.
- **TypeScript/Node backend** — weaker platform-SDK support (Agent Runtime, Document AI) means more glue and friction with the platform being showcased. Rejected.
- **Next.js frontend** — heavier than needed for internal dashboards + one portal. Rejected.
- **LangGraph for the fulfillment graph** — capable, but an extra dependency/concept before it is needed. Deferred (see revisit trigger).

## Note — LangGraph in the Benefits demo (not the core)

LangGraph *is* used in the project, but only outside the Bridge core: the Benefits demo (Phase 2) builds one **simulated carrier counterparty agent** in LangGraph (alongside one in ADK) to prove **A2A framework interoperability** — the ADK-built Bridge negotiates multi-turn with a non-ADK agent over canonical A2A. This is demo furniture in the external zone, has no bearing on the core's own framework choice, and does not contradict the "LangGraph deferred for the fulfillment graph" decision. See `wiki/bridge-benefits-demo.md`, `docs/features/benefits-demo.md`.
