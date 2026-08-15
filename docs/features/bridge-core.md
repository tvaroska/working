# Feature — Bridge Core

**Status:** 📋 Planned (0%) · **Release:** 1 (Minimal Showcase) · **Spec:** `wiki/bridge.md`, `wiki/bridge-aggregate-model.md`, `wiki/bridge-seams.md`, `wiki/bridge-edges.md`, `wiki/bridge-dual-path.md`, `wiki/bridge-disposition.md`, `wiki/bridge-proactive.md`

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

## Platform-native from day one
The core runs on ADK natively — the Bridge is an `LlmAgent` (`document_bridge`) with tools (extraction as an `AgentTool` subagent, `run_disposition_gate` as the authoritative KYC gate, `request_human_review` as a `LongRunningFunctionTool`), documents as versioned ADK artifacts, and sessions/artifacts swapping `InMemory…` ↔ `Gcs`/Vertex across the seam. The A2A edge speaks canonical A2A via `a2a-sdk`. These are hard requirements, not later hardening. See `wiki/bridge-adk.md`, `wiki/bridge-a2a-edge.md`, `docs/decisions/adr-0001-stack.md`.

## Intended layout
Release-1 core lives under `bridge/src/bridge/`: `aggregate/` (Exchange/task/session/party invariants), `seams/` + `tests/seams/` (interfaces, local + GCP adapters, shared parity suite), `edges/` (A2A + A2UI portal + reference renderer), `dual_path/` (Path A validate-only, Path B extract), `extraction/` (seam + fixture + Gemini adapters, quality/confidence gates), `disposition/` + `classification/` (gates, capped resubmission, HITL suspend/resume, issuer canonicalization), `ledger/` (classified ledger view), `proactive/` (Scheduler seam + SLA policy + virtual clock), `skills/` (Agent Skills loader, Agent-Card regeneration, live skill upload). The mock→real Bridge swap holds behind the same A2A contract with the agent core unchanged. See `docs/features/processing-agents.md`.

**Deferred:** Document AI extraction and the Gemini classifier (Release 3); Gemini extraction defaults to the `fixture` engine locally, with a gated live-API parity run for CI (`docs/lessons-learned.md §C3`).
