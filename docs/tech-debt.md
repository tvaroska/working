# Tech-Debt Audit — A2A Document Bridge

> **Audience:** an incoming tech lead who has to trust this codebase.
> **Stance:** candid. This document names the gaps between what the README / `PLAN.md` / ADRs
> *advertise* and what the code actually *does*, with file:line evidence for each. It is the
> counterweight to the roadmap: the roadmap says where we're going; this says where we actually are.
>
> **Last audited:** 2026-08-10 · **Suite at audit time:** `uv run pytest` collects **480** tests.

The Bridge core (aggregate model, seams, edges, dual-path, classified ledger, proactive follow-up)
is genuinely well built and well tested — the seam-parity discipline is real. The debt is
concentrated in three places: the **framework claim** (ADK), the **delivery surfaces** (the FastAPI
servers and the React frontends), and **CI that is structurally biased toward passing**. None of
these are hidden in the code — most are honestly labeled in docstrings — but they are *not* surfaced
in the outward-facing docs, and a reader of the README would reasonably over-estimate what is done.

Severity legend: 🔴 high · 🟠 medium-high · 🟡 medium · ⚪ low.

---

## 🟢 1. "Google ADK" is a declared dependency, not the agent runtime — SUPERSEDED (2026-08-14)

> **UPDATE 2026-08-14 — this verdict is now stale.** After this item was audited (2026-08-10), the
> repo adopted the ADK-showcase mandate and **built real ADK**: a genuine `LlmAgent` under a `Runner`
> with an ADK `SessionService`, `BridgeClient.advance` exposed as the `request_proof` function tool,
> an offline `ScriptedLlm` double for CI, and a passing parity suite proving the LlmAgent path reaches
> the same terminal outcome as the frozen deterministic `run_collect` across all six golden branches.
> This is formalized in **`docs/decisions/adr-0006-adk-native-runtime.md`** (Accepted) and captured in
> `docs/lessons-learned.md §A3, §D`. The "ADK is aspirational" conclusion below is **retained for the
> historical record only** — it no longer describes the code. Target runtime is `google-adk >= 2.7.0`.

**Advertised.** README (`README.md:32`) and `docs/decisions/adr-0001-stack.md:19,32,46` name **Google
ADK** as the agent framework — "native to the Agent Runtime," explicitly rejecting "raw SDKs, no ADK."

**Actual.** The agent loop is a hand-rolled deterministic `async while` loop with **no ADK
involvement**:

- `agents/src/agents/address/agent.py:69-116` — `run_collect` is a plain loop. Its own docstring is
  honest about it: "deterministic (no LLM) and framework-agnostic so it can be hosted under ADK
  **later** without change" (`agent.py:5-6`).
- `grep -rn "adk" agents/src --include=*.py` returns nothing. The agent package never imports ADK.
- The **only** real `google.adk` import in the whole repo is a lazy import inside a GCP *session
  store* seam — not the runtime: `bridge/src/bridge/seams/gcp/sessions.py:49`
  (`from google.adk.sessions import VertexAiSessionService`).
- `google-adk>=1.0` is declared in `bridge/pyproject.toml:8` and `agents/pyproject.toml:8`, and mypy
  is told to ignore its missing stubs (`pyproject.toml:44`).
- **No ADK graphs run.** Orchestration is deterministic `async` methods (the Collect loop +
  `DispositionService`), not an ADK graph/agent-runtime execution.
- **HITL is manual task-parking, not ADK `RequestInput`.** `grep -rn "request_input\|RequestInput"`
  returns nothing. Human-in-the-loop is a parked task state (`TaskStatus.INPUT_REQUIRED`,
  `aggregate/task.py:36,94`) resolved by an out-of-band A2A resume endpoint
  (`edges/a2a/edge.py:222` `resolve_suspended` → `DispositionService.resume`), i.e. the app owns the
  suspend/resume itself rather than using ADK's interactive `RequestInput` primitive.

**Why it matters.** "A showcase of Google ADK / the Agent Runtime" is the pitch; today ADK is a
dependency touched in one non-runtime adapter, no ADK graphs execute, and HITL is hand-rolled
task-parking rather than ADK `RequestInput`. The loop *is* cleanly decoupled (transport behind
`BridgeClient`, policy behind `next_requirements`), so hosting under ADK is plausible — but it has
not been done, so the "ADK showcase" framing is **aspirational**. **Fix:** either wire real ADK
(host `run_collect` as an ADK graph and use `RequestInput` for HITL), or reframe the README/ADR pitch
to "ADK-ready" and state plainly that Phase-1 orchestration + HITL are hand-rolled. **Reframe applied
below** (README + ADR); wiring real ADK remains open roadmap.

---

## 🟢 2. All four frontend surfaces now have browser e2e (was: three had none) — RESOLVED

**Advertised.** README (`README.md:53`) and CI advertise `pnpm test:e2e` / Playwright as a general
frontend capability.

**History.** At the original audit the *only* frontend tests were the provider-portal Playwright
specs; the two SSE surfaces (`agent-console`, `ops-dashboard`) and the `timewarp` presenter control
had no automated tests, because SSE (`EventSource`) needed a streaming route stub that had been
deliberately deferred rather than shipped as a brittle mock.

**Now.** `playwright.config.ts` is one project + one Vite dev server per surface, and all four are
covered (**17 tests, all green**):

- `e2e/provider-portal.spec.ts`, `e2e/ops-dashboard.spec.ts`, `e2e/agent-console.spec.ts`,
  `e2e/timewarp.spec.ts` — each drives the real built SPA + its real domain logic and stubs the
  backend at the network boundary.
- The `EventSource` blocker is solved by `e2e/sse.ts`, which fulfills the stream one-shot with the
  full scripted `text/event-stream` (the client closes on `done`, so no reconnect). timewarp uses a
  stateful REST stub (`timewarp-mock.ts`).

**Remaining caveat (unchanged).** These are still **network-boundary** stubs — they exercise the real
SPA + real domain logic, not the real Python / real-Bridge path end to end. There is still **no
Vitest / component-unit layer** in the frontend; the pyramid is browser-e2e-only. Both are acceptable
for a demo but worth naming.

---

## 🟠 3. mock → real Bridge swap is marked done, but two surfaces still hard-wire the mock

**Advertised.** `PLAN.md:102` marks **S1-core-10** ("Swap mock → real Bridge … agent unchanged") as
`[x]` done (2026-08-06).

**Actual.** The swap holds for the agent *core* (the loop is unchanged across mock/real — the
decoupling in finding 1 is what buys that). But at the *surface* level it is half done:

- **Real Bridge:** `portal_server.py:172` (`A2AEdge(seams=build_seams())`, real `DualPathFulfillment`),
  `timewarp_server.py` (real `bridge.proactive`), `two_run.py` (real core via `build_seams`).
- **Still the mock:** `console_server.py:34,109` (`MockBridge(...)`) and `ops_server.py:43,158`
  (`MockBridge(...)`). `ops_server.py:9-12` admits it depends on the mock's off-contract event log and
  only *aspirationally* notes "Sprint 2 can repoint this at a real Bridge read-model edge."

**Why it matters.** "Swap done" is true of the invariant that mattered most (agent unchanged), but
overstated as a whole-system claim: the agent-console and ops-dashboard demos are still mock-driven.
This is defensible per the roadmap ("the mock Bridge is a maintained artifact, not throwaway",
`docs/roadmap.md:88`) — but the PLAN checkbox reads as more complete than reality.

---

## 🟡 4. Gemini extraction is real code, but off by default and never exercised live in CI

**Actual.** The Gemini engine is genuinely implemented — it builds a Vertex `genai` client and calls
`generate_content` with constrained-JSON output (`bridge/src/bridge/extraction/gemini/engine.py:181-206`).
The honest caveats:

- The **default engine is `fixture`**, not Gemini (`.env.example:23` `BRIDGE_EXTRACTION_ENGINE=fixture`;
  `factory.py:68-69`). Out of the box nothing calls the API.
- The Gemini unit tests use a **fake client stub**, not the API (`tests/bridge/extraction/test_gemini.py`).
  The live-API parity run is **opt-in and gated off in CI** (needs ADC + `BRIDGE_TEST_GEMINI=1`).
- "Confidence" is a **completeness heuristic proxy, not model confidence** (`engine.py:101-116`).
- `docai` extraction is a `NotImplementedError` slot (`factory.py:74`) and the `gemini` *classifier*
  is likewise unbuilt (`classification/factory.py:46`).

**Why it matters.** The real-document extraction path is real but **unproven end-to-end** — it never
runs against the live model in CI and is not the default. **Fix:** at minimum, run the gated live
parity suite on a schedule against a real project so the adapter doesn't rot.

---

## 🟡 5. CI is structurally biased toward passing

`.github/workflows/ci.yml` + `Makefile`:

- **`skills-ref` is an unverified assumption.** `ci.yml:94-97` installs `${SKILLS_REF_PACKAGE:-skills-ref}`
  with an inline "ASSUMPTION (confirm in S0-infra-1)" comment. If that npm package isn't the right
  validator, the skills job breaks or validates nothing.
- **`make test-suite` runs a stub.** `scripts/shared_suite.py:2,32` is a "runner stub" that prints
  "no seam/golden suites present yet — stub no-op (exit 0)". The `shared-suite` CI job (with a real
  Postgres service attached) can be green while asserting nothing.
- **Every Makefile target self-skips when inputs are absent** and exits 0 — `test` (`Makefile:89`),
  `test-e2e` (`:99`), `lint-frontend`/`typecheck-frontend` (`:62,80`), `skills-validate` (`:122`),
  `tf-*`. A misplaced or renamed file makes CI **pass by doing nothing** instead of failing loudly.
- **Terraform is plan-time only** (`terraform test` via `mock_provider`, `ci.yml:52-54`) — syntactic,
  not functional; no apply, no real GCP.
- **Frontend pnpm cache is disabled** pending a lockfile (`ci.yml:79`).
- **Self-inflicted red (now fixed).** The `ruff format` commit `ed9d231` left 3 `ruff check` errors
  (two E501, one F401) with no follow-up lint — CI's `make lint-python` would have failed on the next
  run. Fixed in this change. The lesson: `ruff format` and `ruff check` are separate gates; run both.

**Why it matters.** A green CI badge here does not guarantee the advertised things ran. **Fix:** make
skip-branches loud (fail, or emit a CI annotation) once a subsystem is expected to exist, and replace
the shared-suite stub with the real suite now that seam/golden tests exist.

---

## 🟡 6. Delivery-path test coverage is uneven; console_server has none

- Seams/aggregates/edges/extraction are **well covered** (the bulk of the 480 tests live under
  `tests/bridge/**` and `tests/seams/**`).
- FastAPI delivery servers are thinner: `test_ops_server.py`, `test_portal_server.py`,
  `test_timewarp_server.py` exist — but **`console_server.py` has no test file** (confirmed:
  `ls tests/agents/address/`). The agent-console *frontend* is now covered (finding 2), but its
  Python delivery server still has no test.
- **Test-count drift:** commit `cabfde8` and the QA checklist cite "477 tests"; the current tree
  collects **480**. Minor, but the headline number is stale in docs.

---

## ⚪ 7. Honestly-labeled future work (large "advertised vs built" surface)

These are correctly flagged in-code as deferred, but collectively they are a lot of the story the
outward docs imply is present:

- `NotImplementedError` slots: Document AI extraction (`extraction/factory.py:74`), Gemini classifier
  (`classification/factory.py:46`), exchange-store `materialize` (`seams/exchange_store.py:67`,
  `seams/gcp/exchange_store.py`).
- `PassthroughFulfillment` is a stub scaffold (`edges/fulfillment.py:5-8,74`).
- Disposition port "cannot express HITL/resubmit" (`disposition/service.py:12`).
- Skill/card placeholder fallbacks for bare/malformed folders (`edges/a2a/card.py:53,70`).
- **`scripts/run-core.sh` is stale** — it imports `bridge.edges.app`, which does not exist (the real
  app is `bridge.edges.a2a.app:create_app`), so its "real server" branch never fires. Documented in
  `docs/qa/phase1-checklist.md` § D.1 but not yet fixed.
- **Trust boundary is permissive by default** — the local authenticator only enforces per-party
  scoping under `strict=True`; the default skips enforcement for unauthenticated callers
  (`docs/qa/phase1-checklist.md` § B, "CRITICAL"). Fine for local demos, a footgun if shipped as-is.
- **The GCP deployed path has never actually been run** — every GCP-gated verification is marked
  "PENDING (human)" (`docs/qa/phase1-checklist.md` §§ A.4, D.2). Phase-1 exit was signed off on the
  **local** path only.

---

## 🟠 8. Frontend is MUI, not the advertised Tailwind + shadcn/ui

**Advertised.** README (`README.md:33`) and `docs/decisions/adr-0001-stack.md:23` name **Tailwind +
shadcn/ui** as the frontend UI library.

**Actual.** Every surface is built on **MUI (Material UI)**, not Tailwind or shadcn:

- `frontend/{provider-portal,ops-dashboard,timewarp,agent-console}/package.json` each depend on
  `@mui/material`, `@mui/icons-material`, `@emotion/react`, `@emotion/styled`.
- `grep -rn "tailwind\|shadcn" frontend --include=package.json` returns **nothing** — no Tailwind
  config, no shadcn components anywhere.

**Why it matters.** This is a straight **advertised-vs-built mismatch in the stack decision itself** —
and, tellingly, one this very audit missed until an external review caught it, which is a reminder
that "candid" is a moving target. The choice is defensible (MUI's component set fits the
dashboard-heavy surfaces), but the docs claimed the opposite. **Fix (done):** README and ADR-0001
corrected to state MUI, with the deviation recorded in the ADR's Implementation status section.

---

## 🟠 9. The "A2A edge" is a bespoke REST mapping, not the A2A protocol

**Advertised.** README / `wiki/bridge-a2a-edge.md` and `docs/decisions/adr-0001-stack.md:32,39` present
an **A2A** front door — "send a message, get/list/cancel tasks," "A2A has stable SDKs" — implying the
published Agent2Agent wire protocol. The route prefix is `/a2a/…`.

**Actual.** The edge is a **hand-rolled plain-JSON REST mapping on FastAPI**, not A2A:

- Bespoke routes carry the domain types directly — `POST /a2a/exchanges` (body `CollectRequest`),
  `POST /a2a/exchanges/{context}/turns` (body `RequirementsList`), `GET /a2a/tasks/{id}`,
  `.../events` (hand-rolled SSE) — see `.claude/plans/S1-core-3-a2a-a2ui-edges.md:76-83,215-224`.
- **No JSON-RPC 2.0**, no spec method names (`message/send`, `tasks/get`, …), no A2A
  `Message`/`Task`/`Artifact`/`Part` envelopes. The plans say so explicitly: "Full JSON-RPC A2A
  envelope fidelity … deferred hardening" (`S1-core-3…md:58`); "Full A2A-protocol fidelity … out of
  scope; there is no `a2a-sdk` in this repo" (`S1-agent-2…md:57`).
- **No `a2a-sdk` dependency** anywhere (`bridge/pyproject.toml`, `uv.lock`) — despite ADR-0001:32
  citing "the A2A SDK" as a reason to pick Python. The only conformant surface is the well-known
  **Agent Card** (`/.well-known/agent-card.json`).

**Why it matters.** A real A2A-conformant agent cannot talk to these routes; `/a2a/` signals intent,
not conformance. This violates the repo's own **"as standard as possible … a custom layer needs a
specific, recorded justification"** principle (`wiki/bridge-adk.md:20`) — the same principle ADR-0006
applied to the runtime — and the deviation was carried only in *plan* files, never a recorded
decision. **Fix (decision recorded):** `docs/decisions/adr-0007-canonical-a2a-edge.md` mandates
canonical A2A on the `a2a-sdk`; the domain contract is unchanged (envelope-only migration).
Implementation is tracked in `PLAN.md` → Deferred hardening. **Wiki reframed** (`bridge-a2a-edge.md`
now states target-vs-today); wiring the SDK remains open.

---

## Remediation priorities (recommended order)

1. **Truth-in-advertising pass (cheap, high trust return).** Reconcile README/ADR ADK language with
   the hand-rolled loop; correct the S1-core-10 "done" scope; fix the stale test count; state the
   real frontend UI library (MUI). (Findings 1, 3, 6, 8.)
2. **Make CI fail loudly (cheap).** Replace the `shared_suite.py` stub with the real suite; turn
   silent skip-branches into failures/annotations once a subsystem exists; confirm `skills-ref`. (5.)
3. **Broaden frontend e2e (medium).** ~~SSE + REST stubs for the other three surfaces~~ **done** (all
   four surfaces now have Playwright e2e — finding 2). Still open: add a `console_server` Python test,
   and consider a Vitest component layer. (6.)
4. **Prove the live paths on a schedule (medium).** Run the gated Gemini parity suite and the
   `BRIDGE_TEST_GCP=1` seam parity against a real project periodically. (4, finding 7 GCP.)
5. **Fix the known footguns.** `scripts/run-core.sh`, and decide whether strict auth should be the
   default. (7.)
6. **Conform the A2A edge to the protocol (medium-large).** Adopt `a2a-sdk`; replace the bespoke REST
   routes with JSON-RPC 2.0 + spec methods/objects, keeping the domain contract unchanged. Decided in
   ADR-0007. (9.)
