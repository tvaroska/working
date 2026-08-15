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
- [x] **M0.3 — `BridgeClient` port.** Transport-agnostic `collect(request) -> ExchangeTurn`, with an `a2a-sdk` impl doing `message/send` + `tasks/get` polling. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.3-bridge-client-port.md)_ **Superseded 2026-08-15:** port + `A2ABridgeClient` removed once the contract was validated — the address agent now consumes the Bridge as a native `RemoteA2aAgent` (wiring trajectory in adr-0010). Wire helpers survive in `bridge_client/wire.py`.
- [x] **M0.4 — Mock Document Bridge** (`agents/src/agents/mock_bridge/`). `a2a-sdk` server: on send, create in-memory task → `WORKING` → hold ~10s (configurable) → `COMPLETED` with a `CollectionStatus` whose `LedgerEntry` is loaded from the address evals. Serve a minimal Agent Card. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.4-mock-document-bridge.md)_
- [x] **M0.5 — Address `LlmAgent` scaffold** (`agents/src/agents/address/`). `google-adk` `LlmAgent`, `BridgeClient` wired as tool/port; one turn: request `address-proof` for `jordan-lee`, await result, render `id` + structured info. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.5-address-agent-scaffold.md)_ **Superseded 2026-08-15:** `build_address_agent(card_url)` now attaches the Bridge as a native `RemoteA2aAgent` **sub-agent** (delegated via `transfer_to_agent`); the `FunctionTool` consumer is gone (adr-0010, wiring trajectory).
- [x] **M0.6 — Round-trip test.** One pytest: agent→mock→agent; assert payload matches `expected.json` entry, and assert `WORKING` was observed before `COMPLETED` (async path exercised). 10s hold shrinkable for the test. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.6-round-trip-test.md)_ **Updated 2026-08-15:** `test_round_trip.py` now drives agent → transfer → native sub-agent → mock and asserts the relayed `ExchangeTurn`; the `WORKING`-before-`COMPLETED` wire ordering is locked by `test_native_consumer.py` Test A.
- [x] **M0.7 — Run doc** (`agents/README.md`). Start the mock, run the agent, run the test. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/M0.7-run-doc.md)_

**Definition of done:** the async round-trip runs locally, mock holds ~10s, agent renders the eval-sourced `id` + structured info; green test asserts payload + async path; contract models + `BridgeClient` port + mock committed (mock persists as the Sprint-1 contract double); agent is a real ADK `LlmAgent` and the edge is canonical A2A.

**Validation gate:** contract sign-off with the design owner — are `CollectRequest` / `CollectionStatus` / `LedgerEntry` right, does the domain payload sit cleanly inside A2A parts, is `tasks/get` polling the async surface we want before push-notifications (Phase 3)? Sign-off de-risks Sprint 1. *(The M0 hand-rolled `BridgeClient` poll loop is superseded from Sprint 1 by the native `RemoteA2aAgent` consumer — `docs/decisions/adr-0009-native-a2a-consumer.md`.)*

---

## Next — Sprint 0 (scaffolding)

**Goal:** stand up the **project-wide** toolchain, CI, dev-env, and cross-cutting skeletons that Sprint 1 slots into — everything the M0.1 *minimal agents-only slice* deferred (`docs/roadmap.md`). Sprint 0 is scaffolding + a sign-off gate; it ships **no domain behavior** (no Collect logic, no real Bridge, no GCP adapters — those are Sprint 1/2).

**Already done (M0.1, do not redo):** `agents/` uv project, `src/` layout (`contract` + `agents`), pinned `google-adk>=2.7.0,<3` / `a2a-sdk[http-server]` / `pydantic>=2`, `uv.lock` committed, pytest + ruff wired, `test_scaffold.py` pin-guard. Sprint 0 extends this to the **whole repo** (core, frontend, skills, IaC, CI).

- [x] **S0.1 — CI pipeline (GitHub Actions).** One workflow, path-filtered per project, green as the merge gate.
  1. `.github/workflows/ci.yml` — jobs: **agents** (`uv sync` → `uv run ruff check` → `uv run pytest`, cwd `agents/`), **core** (same, cwd `bridge/` once S0.2 lands), **skills** (`skills-ref validate` per skill folder — S0.6), **frontend** (`pnpm install` → lint → `pnpm test` — S0.4, allowed to no-op until the app exists).
  2. Pin `astral-sh/setup-uv` with cache keyed on `uv.lock`; pin Python 3.12 via `.python-version`.
  3. Path filters so a docs-only PR skips code jobs; `bridge/`-vs-`agents/` isolation guard test (S0.2) runs in the core job.
  4. Add a **SDK-pin drift** guard: `test_scaffold.py` already asserts the `google-adk` range — surface its failure clearly (ADR-0001 SDK risk). _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/S0.1-ci-pipeline.md)_

- [x] **S0.2 — `bridge/` core project scaffold.** The reusable core as a **separate** uv project (the showcase artifact; "the difference between demos is the agent, not the Bridge").
  1. `bridge/pyproject.toml` (src layout, own `uv.lock`), same pins as `agents/`; `bridge/src/bridge/__init__.py` placeholder + `bridge/tests/`.
  2. **Decide contract-type sharing** (open decision → sign-off, S0.8): recommended = a **shared `contract` package** both `agents/` and `bridge/` depend on (neither imports the other — the invariant `bridge/` never imports `agents/` is preserved; a shared *third* package is allowed). Alternative = duplicate-by-discipline. Record the choice in an ADR before moving `contract` out of `agents/src/`.
  3. **Isolation guard test** (`bridge/tests/test_no_agents_import.py`): assert `import bridge` pulls in **no** `agents.*` module (scan `sys.modules`), locking the invariant in CI.
  4. Note the parity discipline: canonicalization/disposition logic is kept in parity between `bridge/` and `agents/` **by the shared seam suite**, not by import.
  _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/S0.2-bridge-core-scaffold.md)_

- [x] **S0.3 — Seam test harness convention.** Establish the "**one shared suite, two adapters**" pattern before any seam is built (Sprint 1 designs interfaces; Sprint 2 adds GCP impls).
  1. `tests/support/seams.py` (or a `conftest.py` fixture): a parametrized `adapter` fixture yielding `local` always and `gcp` only when credentials are present (else `pytest.skip`) — so the *same* test asserts both.
  2. Enumerate the six seams as stub interfaces/markers so Sprint 1 has a home: **Sessions, Task store, Exchange store, Skill registry, Scheduler, Extraction**. Each gets a `@pytest.mark.seam("<name>")`.
  3. Document the rule in `docs/` (or extend `wiki/bridge-seams.md`): mock→real and local→GCP swaps must be **no-ops for the agent**; parity is **terminal-outcome, not ledger-identical**. _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/S0.3-seam-test-harness.md)_

- [ ] **S0.4 — Frontend scaffold.** React + TypeScript + Vite + MUI via **pnpm**; Playwright configured (empty suite ok).
  1. `frontend/` — `pnpm create vite` (react-ts), add MUI, ESLint + Prettier, `tsconfig` strict.
  2. Minimal app shell (routing placeholder for the three Sprint-1 surfaces); `pnpm lint` + `pnpm test` + `pnpm build` all green.
  3. `frontend/playwright.config.ts` + one smoke e2e (loads the shell). Wire the frontend CI job (S0.1).

- [ ] **S0.5 — IaC (Terraform) skeleton — layout + fmt/validate only.** Base infra itself is **Sprint 2**; Sprint 0 only lays the structure so it isn't retrofitted.
  1. `infra/` — module/`envs` directory convention, `versions.tf` (provider pins), remote-state backend stub (commented until the bucket exists).
  2. CI step: `terraform fmt -check` + `terraform validate` (no `plan`/`apply`, no credentials). Keep it minimal so it doesn't absorb Sprint 2's front-loaded Terraform work (roadmap cross-cutting risk).

- [ ] **S0.6 — Skills scaffold + `skills-ref validate` in CI.** Agent Skills format from the start (ADR-0001).
  1. `skills/address-proof/` in the Agent Skills folder format (skill manifest + the address satisfaction description the Bridge reasons over — `wiki/bridge-collect`), sourced from `docs/lessons-learned.md §C1` demo values (`gov-id` / `utility-bill`, party `jordan-lee`).
  2. CI job runs `skills-ref validate` on every folder under `skills/`; document the local command in the dev-env doc (S0.7).

- [ ] **S0.7 — Dev-env + contributor workflow.** Make setup one command and lint automatic.
  1. Root `README`/`CONTRIBUTING` (or a `Makefile`/`justfile`): `setup` (`uv sync` in `agents/` + `bridge/`, `pnpm install` in `frontend/`), `test`, `lint`, `fmt` targets.
  2. `pre-commit` config: `ruff` (lint+format) on Python, Prettier on frontend, `terraform fmt` on `infra/`, `skills-ref validate` on `skills/`.
  3. `.env.example` conventions consolidated (Vertex vars for `agents/`, `BRIDGE_CARD_URL`/`BRIDGE_BASE_URL`); confirm `.env` gitignored, `.env.example` tracked.

- [ ] **S0.8 — Stack + open-decision sign-off (gate, not code).** Resolve and record the decisions Sprint 1 builds on, so they're designed in, not retrofitted.
  1. Walk `wiki/bridge-open-questions.md`; convert each resolved item to an ADR or a PLAN note, leave the rest explicitly deferred with an owner.
  2. Confirm the **contract-sharing** choice (S0.2), the **seam list** (S0.3), and the **experimental-surface register**: `RemoteA2aAgent` (`@a2a_experimental`), `ResumabilityConfig` (`@experimental`), and the **`Workflow` spike gates** for S1-6 (`RemoteA2aAgent`-as-node + in-`Workflow` pause/resume; `LoopAgent` deprecated fallback) — see `docs/decisions/adr-0010-durable-consumer-construct.md` and `wiki/bridge-a2a-consumer.md`.
  3. Re-affirm the ADR-0001 pins resolve on a clean machine (`uv lock` reproducibility).

- [x] **S0.9 — Architecture-doc consolidation** (done 2026-08-15). Reset the two churned consumer docs to a target-first statement so Sprint 1 builds against a clean architecture, and harvest the session's source-verified findings into the invariant record. Not a full-repo reset — the rest of `wiki/` was audited consistent.
  1. **Harvested lessons** into `docs/lessons-learned.md`: **A12** (durable consumer = `Workflow` graph; `AgentTool`'s fresh throwaway session is the root cause; the two distinct "returns"; `LoopAgent` deprecated; `Workflow`-can't-be-`LlmAgent`-subagent; the general service-agent shape; `AgentTool → Workflow` migration + spike gates) and **A13** (state restore is mostly DEFAULT; "the webhook is a doorbell, not a restore").
  2. **Split the ADR:** `adr-0009` stripped back to the stable **native-consumer principle + wire vocabulary** (its four same-day amendments removed); new **`adr-0010-durable-consumer-construct.md`** consolidates the construct/wiring trajectory (port removed → transfer → `AgentTool` interim → `Workflow` target), the general service-agent shape, and the durable state-restore breakdown.
  3. **Rewrote `wiki/bridge-a2a-consumer.md` target-first:** promoted "Service-agent architecture (the general shape)"; folded the wiring sections into one "why the graph, not transfer/`AgentTool`"; compressed the "Landed S1-x" build-log to pointers (per the repo rule: progress lives in `PLAN.md` + git, not the spec).
  4. **Repointed inbound links** (PLAN, `processing-agents.md`, `bridge-collect`, `bridge-collect-scenarios`) — construct/`Workflow` references now cite `adr-0010`; wire-vocabulary references stay on `adr-0009`; removed dangling "adr-0009 amendment" references and fixed the renamed section anchor.

**Definition of done:** CI is the green merge gate across agents/core/skills/frontend/IaC; `bridge/` exists with the `no-agents-import` guard passing; the seam harness pattern is documented and exercised by at least one parametrized test; frontend shell builds + one Playwright smoke passes; `skills-ref validate` passes on `address-proof`; `terraform fmt -check`/`validate` pass on the skeleton; one-command dev setup + pre-commit work; open decisions are recorded (ADR or deferred-with-owner).

**Validation gate:** stack + open-decision sign-off (S0.8) with the design owner before Sprint 1 — contract-sharing strategy, seam list, and the experimental-surface register are agreed and pinned.

## Then — Sprint 1 (Phase 1 local, agent-first)

Grow the tracer bullet into the real thing — mock→real swap must be a no-op for the agent. **Consumer construct changed** here: per `adr-0009` the demos adopt the native `RemoteA2aAgent` and the M0 `BridgeClient` port was **removed** (wiring trajectory in `adr-0010`) — grow the Collect loop against the native consumer, not behind a port.

- [x] **Native A2A consumer (`adr-0009`)** — adopt `RemoteA2aAgent` (card-configured) as the Bridge consumer; contract redesign so the Bridge emits `INPUT_REQUIRED` on park (→ native `LongRunningFunctionTool` pause/resume) and `TaskStatusUpdateEvent` with a **non-empty** `status.message` on progress; flip the consumer's `INPUT_REQUIRED`-is-failure guard (`agents/src/bridge_client/a2a_client.py`); pin the integration-extension mode (`use_legacy=True` until validated) and cover it in the seam suite (`RemoteA2aAgent` is `@a2a_experimental`). _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/s1-1-native-a2a-consumer.md)_ **Scope note:** the mock park is a **mechanism tracer** (`WORKING → INPUT_REQUIRED → resume → COMPLETED`, opt-in `park=True`); the multi-turn `is_satisfied` Collect loop and real requirements logic remain in the next bullet. **Consumer switch landed 2026-08-15:** the address agent now consumes the Bridge as a `RemoteA2aAgent` **sub-agent** and the M0 `BridgeClient` port was removed (adr-0010, wiring trajectory). Carrying a structured `CollectRequest` under the native consumer (transfer forwards conversation content today) is folded into the next bullet.

**Completeness-gated Collect flow** (grows the M0 one-shot into the loop where *the app decides done*; see [`wiki/bridge-a2a-consumer.md`](wiki/bridge-a2a-consumer.md) "transfer vs. call-and-return" and [`wiki/bridge-collect.md`](wiki/bridge-collect.md)):

- [x] **S1-2 — Control-return wiring (transfer → `AgentTool`).** Switch the Bridge consumer from a transfer `sub_agent` to `AgentTool` (call-and-return) so control returns to the address agent with the `ExchangeTurn`, and restore the structured `CollectRequest` as a JSON DataPart on the send path (transfer currently forwards conversation content — adr-0010 open consequence). Card-URL swap unchanged; cover in the seam suite. *(Depends on S1-1.)* _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/S1-2-control-return-agenttool.md)_
- [x] **S1-3 — `is_satisfied` completeness gate.** Deterministic pure function over the classified ledger implementing the Address rule (`gov-id` **OR** 2 bills from **distinct issuers**, distinct-issuer via issuer canonicalization), returning done + outstanding. Expose as an **authoritative tool** — *LLM routes, code decides*; a model may never mint "complete". Unit-tested against the eval fixtures. *(Pure; wired by S1-4.)* _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/S1-3-is-satisfied-gate.md)_
- [x] **S1-4 — Multi-turn Collect loop.** Wire the address agent to loop: call Bridge (`AgentTool`) → run `is_satisfied` → if not done, request the outstanding proof again; terminate on satisfied and present the result. One **durable A2A task + context** spans the loop's turns (no new task per round). *(Depends on S1-2, S1-3.)* _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/S1-4-multi-turn-collect-loop.md)_ **Scope note:** the durable unit threaded across rounds is the exchange **`context_id`** (via session state; the `AgentTool`'s fresh child session wipes native context/task history), not a reused `task_id` — each round of the `park=False` completing path opens a new task under the same context (adr-0010 §1, `AgentTool` interim).
- [x] **S1-5 — Mock Bridge multi-turn contract.** Grow the mock into the permanent multi-turn contract double: fixture document arrivals across turns, faked chase/timeout, distinct-issuer bill fixtures, plus the `INPUT_REQUIRED` park + non-empty `status.message` progress already tracered in S1-1. *(Parity is terminal-outcome, not ledger-identical.)* _(done 2026-08-15; Plan: /home/boris/working/.claude/plans/S1-5-mock-multiturn-contract.md)_
- [ ] **S1-6 — Durable graph consumer + park/resume spike (no HTTP).** Move the Collect loop off the in-turn `AgentTool` (fresh throwaway session — blocks native park/resume) onto a **native graph on one shared, durable session** — the ADK-native form of host-orchestrated Collect (the "Option B" target). Prove a parked address-agent leg survives a process restart and resumes to the *same* state, using only platform-native machinery — **no webhook, no `adk web`.**
  - **Construct = `google.adk.workflow.Workflow`** (node/edge graph, *not* `@experimental`), **not `LoopAgent`** — `LoopAgent`/`SequentialAgent` are `@deprecated` in favor of `Workflow` (`loop_agent.py`); new durable code must not build on the deprecated construct. Graph shape: `collect` node (`RemoteA2aAgent`) → `gate` node (deterministic `is_satisfied`, branch back to `collect` if not done, else finish) → presenter (`LlmAgent` **as a node** — `Workflow` cannot yet be an `LlmAgent` sub-agent, so the graph sits on top).
  - **Two spike gates (de-risk before committing):** (1) can a `RemoteA2aAgent` (non-`LlmAgent` `BaseAgent`) be a `Workflow` **node** — only `@node`/`FunctionNode`/`LlmAgent`-as-node are confirmed; (2) does an `INPUT_REQUIRED` pause propagate + resume cleanly **inside a `Workflow`** (verified inside `LoopAgent`, not yet inside `Workflow`). **Fallback if either fails: `LoopAgent`** (verified: shared session, `escalate` termination, pause propagation), accepting the deprecation risk.
  - **Durability wiring:** swap `InMemorySessionService`→`DatabaseSessionService` (consumer) and `InMemoryTaskStore`→`DatabaseTaskStore` (mock Bridge), enable `ResumabilityConfig(is_resumable=True)` (`[EXPERIMENTAL]` — pin + seam-cover), park via `INPUT_REQUIRED`, then resume across a fresh `Runner` by feeding a `FunctionResponse` to `runner.run_async(...)`. Assert `session.state` (ledger + exchange `context_id`) and the Bridge `task_id`/`context_id` (auto-restored from `event.custom_metadata` on the **shared** session — no manual threading) are intact and the `is_satisfied` gate continues where it paused.
  - **Payoff:** the shared durable session gives native `context_id` continuity (retires the hand-threaded state key) and lets `RemoteA2aAgent` run as a normal node (retires `BridgeAgentTool`'s copied Runner boilerplate). Proves *restore* independently of *wake*, de-risking the Phase-3 webhook. See `docs/decisions/adr-0010-durable-consumer-construct.md` and `wiki/bridge-a2a-consumer.md` ("Wiring: why the graph…" + "Durable state restore").

> **Out of this flow (Phase 3):** push-notification **webhooks** (`PushNotificationConfig`) for fully-durable legs. The webhook is a **doorbell, not a restore** — S1-6 already delivers the restore; Phase 3 adds only the *wake path*, which is the **CUSTOM** surface: (1) a **webhook receiver** endpoint (neither `a2a-sdk` — sender-only — nor ADK ships one, and `adk web` can't host it) and (2) a **`task_id`→session index** so the receiver knows which session to resume (no ADK/A2A schema indexes a session by A2A `context_id`/`task_id`); the receiver then builds the `FunctionResponse` and calls `runner.run_async(...)` (everything downstream is DEFAULT). The Sprint-1 loop uses hold/stream + `INPUT_REQUIRED` pause/resume. See `PLAN.md` M0 validation gate and [`wiki/bridge-a2a-consumer.md`](wiki/bridge-a2a-consumer.md) "Durable state restore" / "Timescales compose".
- Frontend v1 — three surfaces + time-warp.
- Real Bridge (local) — aggregate model, both edges, dual-path, fixture extraction graph, disposition + classification + issuer canonicalization, classified ledger, proactive (virtual clock), seam local adapters. Shared suite green across mock→real.

Full sequence and later releases: [`docs/roadmap.md`](docs/roadmap.md), [`wiki/bridge-implementation-plan.md`](wiki/bridge-implementation-plan.md).
