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
- [x] **M0.3 — `BridgeClient` port.** Transport-agnostic `collect(request) -> ExchangeTurn`, with an `a2a-sdk` impl doing `message/send` + `tasks/get` polling. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.3-bridge-client-port.md)_ **Superseded 2026-08-15:** port + `A2ABridgeClient` removed once the contract was validated — the address agent now consumes the Bridge as a native `RemoteA2aAgent` sub-agent (see adr-0009 amendment). Wire helpers survive in `bridge_client/wire.py`.
- [x] **M0.4 — Mock Document Bridge** (`agents/src/agents/mock_bridge/`). `a2a-sdk` server: on send, create in-memory task → `WORKING` → hold ~10s (configurable) → `COMPLETED` with a `CollectionStatus` whose `LedgerEntry` is loaded from the address evals. Serve a minimal Agent Card. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.4-mock-document-bridge.md)_
- [x] **M0.5 — Address `LlmAgent` scaffold** (`agents/src/agents/address/`). `google-adk` `LlmAgent`, `BridgeClient` wired as tool/port; one turn: request `address-proof` for `jordan-lee`, await result, render `id` + structured info. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.5-address-agent-scaffold.md)_ **Superseded 2026-08-15:** `build_address_agent(card_url)` now attaches the Bridge as a native `RemoteA2aAgent` **sub-agent** (delegated via `transfer_to_agent`); the `FunctionTool` consumer is gone (adr-0009 amendment).
- [x] **M0.6 — Round-trip test.** One pytest: agent→mock→agent; assert payload matches `expected.json` entry, and assert `WORKING` was observed before `COMPLETED` (async path exercised). 10s hold shrinkable for the test. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.6-round-trip-test.md)_ **Updated 2026-08-15:** `test_round_trip.py` now drives agent → transfer → native sub-agent → mock and asserts the relayed `ExchangeTurn`; the `WORKING`-before-`COMPLETED` wire ordering is locked by `test_native_consumer.py` Test A.
- [x] **M0.7 — Run doc** (`agents/README.md`). Start the mock, run the agent, run the test. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.7-run-doc.md)_

**Definition of done:** the async round-trip runs locally, mock holds ~10s, agent renders the eval-sourced `id` + structured info; green test asserts payload + async path; contract models + `BridgeClient` port + mock committed (mock persists as the Sprint-1 contract double); agent is a real ADK `LlmAgent` and the edge is canonical A2A.

**Validation gate:** contract sign-off with the design owner — are `CollectRequest` / `CollectionStatus` / `LedgerEntry` right, does the domain payload sit cleanly inside A2A parts, is `tasks/get` polling the async surface we want before push-notifications (Phase 3)? Sign-off de-risks Sprint 1. *(The M0 hand-rolled `BridgeClient` poll loop is superseded from Sprint 1 by the native `RemoteA2aAgent` consumer — `docs/decisions/adr-0009-native-a2a-consumer.md`.)*

---

## Next — Sprint 0 (scaffolding)

CI, dev-env setup, remaining project scaffolding, and stack + open-decision sign-off. Folds in whatever M0.1 didn't already cover. See `docs/roadmap.md`.

## Then — Sprint 1 (Phase 1 local, agent-first)

Grow the tracer bullet into the real thing — mock→real swap must be a no-op for the agent. **Consumer construct changed** here: per `adr-0009` (+ its 2026-08-15 amendment) the demos adopt the native `RemoteA2aAgent` and the M0 `BridgeClient` port was **removed** — grow the Collect loop against the native consumer, not behind a port.

- [x] **Native A2A consumer (`adr-0009`)** — adopt `RemoteA2aAgent` (card-configured) as the Bridge consumer; contract redesign so the Bridge emits `INPUT_REQUIRED` on park (→ native `LongRunningFunctionTool` pause/resume) and `TaskStatusUpdateEvent` with a **non-empty** `status.message` on progress; flip the consumer's `INPUT_REQUIRED`-is-failure guard (`agents/src/bridge_client/a2a_client.py`); pin the integration-extension mode (`use_legacy=True` until validated) and cover it in the seam suite (`RemoteA2aAgent` is `@a2a_experimental`). _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/s1-1-native-a2a-consumer.md)_ **Scope note:** the mock park is a **mechanism tracer** (`WORKING → INPUT_REQUIRED → resume → COMPLETED`, opt-in `park=True`); the multi-turn `is_satisfied` Collect loop and real requirements logic remain in the next bullet. **Consumer switch landed 2026-08-15:** the address agent now consumes the Bridge as a `RemoteA2aAgent` **sub-agent** and the M0 `BridgeClient` port was removed (adr-0009 amendment). Carrying a structured `CollectRequest` under the native consumer (transfer forwards conversation content today) is folded into the next bullet.

**Completeness-gated Collect flow** (grows the M0 one-shot into the loop where *the app decides done*; see [`wiki/bridge-a2a-consumer.md`](wiki/bridge-a2a-consumer.md) "transfer vs. call-and-return" and [`wiki/bridge-collect.md`](wiki/bridge-collect.md)):

- [x] **S1-2 — Control-return wiring (transfer → `AgentTool`).** Switch the Bridge consumer from a transfer `sub_agent` to `AgentTool` (call-and-return) so control returns to the address agent with the `ExchangeTurn`, and restore the structured `CollectRequest` as a JSON DataPart on the send path (transfer currently forwards conversation content — adr-0009 amendment open consequence). Card-URL swap unchanged; cover in the seam suite. *(Depends on S1-1.)* _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/S1-2-control-return-agenttool.md)_
- [ ] **S1-3 — `is_satisfied` completeness gate.** Deterministic pure function over the classified ledger implementing the Address rule (`gov-id` **OR** 2 bills from **distinct issuers**, distinct-issuer via issuer canonicalization), returning done + outstanding. Expose as an **authoritative tool** — *LLM routes, code decides*; a model may never mint "complete". Unit-tested against the eval fixtures. *(Pure; wired by S1-4.)*
- [ ] **S1-4 — Multi-turn Collect loop.** Wire the address agent to loop: call Bridge (`AgentTool`) → run `is_satisfied` → if not done, request the outstanding proof again; terminate on satisfied and present the result. One **durable A2A task + context** spans the loop's turns (no new task per round). *(Depends on S1-2, S1-3.)*
- [ ] **S1-5 — Mock Bridge multi-turn contract.** Grow the mock into the permanent multi-turn contract double: fixture document arrivals across turns, faked chase/timeout, distinct-issuer bill fixtures, plus the `INPUT_REQUIRED` park + non-empty `status.message` progress already tracered in S1-1. *(Parity is terminal-outcome, not ledger-identical.)*

> **Out of this flow (Phase 3):** push-notification **webhooks** (`PushNotificationConfig`) for fully-durable legs — `RemoteA2aAgent` has no push support today and `adk web` can't host the receiver; the loop above uses hold/stream + `INPUT_REQUIRED` pause/resume. See `PLAN.md` M0 validation gate and [`wiki/bridge-a2a-consumer.md`](wiki/bridge-a2a-consumer.md) "Timescales compose".
- Frontend v1 — three surfaces + time-warp.
- Real Bridge (local) — aggregate model, both edges, dual-path, fixture extraction graph, disposition + classification + issuer canonicalization, classified ledger, proactive (virtual clock), seam local adapters. Shared suite green across mock→real.

Full sequence and later releases: [`docs/roadmap.md`](docs/roadmap.md), [`wiki/bridge-implementation-plan.md`](wiki/bridge-implementation-plan.md).
