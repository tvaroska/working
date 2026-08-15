# PLAN — Active Development Tracker

> The **working build plan**: what we're doing now, what's next, and the checklist we execute against. This is the execution surface; the design spec is in [`wiki/`](wiki/bridge.md) and the release-level view is [`docs/roadmap.md`](docs/roadmap.md). Keep this file current as work lands.

**Now:** Milestone 0 — Contract Tracer Bullet
**Legend:** `[ ]` todo · `[~]` in progress · `[x]` done

---

## Milestone 0 — Contract Tracer Bullet 🎯 current

**Goal:** validate the agent↔Bridge **input/output design** on the thinnest end-to-end slice — an ADK `LlmAgent` sends one `CollectRequest`; a mock Bridge accepts it, holds ~10s over the canonical long-running path (`message/send` → `Task{WORKING}` → `tasks/get` poll → `COMPLETED`), and returns an `id` + structured info from `wiki/evals/address/`. Full spec: [`docs/milestone-0-contract-tracer.md`](docs/milestone-0-contract-tracer.md).

**Out of scope (deferred to Sprint 1+):** Collect loop, `is_satisfied` gate, disposition/classification/canonicalization, real Gemini extraction, chase/scheduler/HITL, frontend, GCP/Terraform, skills registry, persistence.

- [x] **M0.1 — Scaffold.** `uv` project, Python 3.12+, `agents/` package; pin `google-adk >= 2.7.0,<3` and `a2a-sdk`; add pytest + ruff. (Minimal slice of Sprint-0 scaffolding — only what M0 needs.) _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.1-scaffold.md)_
- [x] **M0.2 — Contract models** (`agents/src/contract/`). Pydantic `CollectRequest`, `ExchangeTurn`, `CollectionStatus`, `LedgerEntry`, extraction `fields`; field names mirror `wiki/evals/address/expected.json`. *(The artifact under validation.)* _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.2-contract-models.md)_
- [x] **M0.3 — `BridgeClient` port.** Transport-agnostic `collect(request) -> ExchangeTurn`, with an `a2a-sdk` impl doing `message/send` + `tasks/get` polling. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.3-bridge-client-port.md)_
- [x] **M0.4 — Mock Document Bridge** (`agents/src/agents/mock_bridge/`). `a2a-sdk` server: on send, create in-memory task → `WORKING` → hold ~10s (configurable) → `COMPLETED` with a `CollectionStatus` whose `LedgerEntry` is loaded from the address evals. Serve a minimal Agent Card. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.4-mock-document-bridge.md)_
- [x] **M0.5 — Address `LlmAgent` scaffold** (`agents/src/agents/address/`). `google-adk` `LlmAgent`, `BridgeClient` wired as tool/port; one turn: request `address-proof` for `jordan-lee`, await result, render `id` + structured info. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.5-address-agent-scaffold.md)_
- [x] **M0.6 — Round-trip test.** One pytest: agent→mock→agent; assert payload matches `expected.json` entry, and assert `WORKING` was observed before `COMPLETED` (async path exercised). 10s hold shrinkable for the test. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.6-round-trip-test.md)_
- [ ] **M0.7 — Run doc** (`agents/README.md`). Start the mock, run the agent, run the test.

**Definition of done:** the async round-trip runs locally, mock holds ~10s, agent renders the eval-sourced `id` + structured info; green test asserts payload + async path; contract models + `BridgeClient` port + mock committed (mock persists as the Sprint-1 contract double); agent is a real ADK `LlmAgent` and the edge is canonical A2A.

**Validation gate:** contract sign-off with the design owner — are `CollectRequest` / `CollectionStatus` / `LedgerEntry` right, does the domain payload sit cleanly inside A2A parts, is `tasks/get` polling the async surface we want before push-notifications (Phase 3)? Sign-off de-risks Sprint 1.

---

## Next — Sprint 0 (scaffolding)

CI, dev-env setup, remaining project scaffolding, and stack + open-decision sign-off. Folds in whatever M0.1 didn't already cover. See `docs/roadmap.md`.

## Then — Sprint 1 (Phase 1 local, agent-first)

Grow the tracer bullet into the real thing behind the *same* `BridgeClient` port — mock→real swap must be a no-op for the agent:

- Address processing agent — multi-turn Collect loop + `is_satisfied` gate (`gov-id OR 2 distinct bills`).
- Mock Bridge — multi-turn contract + fixture document arrivals + faked chase/timeout (the permanent contract double).
- Frontend v1 — three surfaces + time-warp.
- Real Bridge (local) — aggregate model, both edges, dual-path, fixture extraction graph, disposition + classification + issuer canonicalization, classified ledger, proactive (virtual clock), seam local adapters. Shared suite green across mock→real.

Full sequence and later releases: [`docs/roadmap.md`](docs/roadmap.md), [`wiki/bridge-implementation-plan.md`](wiki/bridge-implementation-plan.md).
