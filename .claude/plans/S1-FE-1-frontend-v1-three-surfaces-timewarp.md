# S1-FE-1 — Frontend v1: three surfaces + time-warp

**Sprint:** 1 (Phase 1 local) · **Task line:** `PLAN.md` "Frontend v1 — three surfaces + time-warp"
**Design roots:** `wiki/bridge-frontend.md`, `docs/features/frontend.md`, `wiki/bridge-a2ui-edge.md`,
`wiki/bridge-zones.md`, `wiki/bridge-proactive.md`, and **`docs/lessons-learned.md §B` (B1–B4) + `§C2`
(port map) + `§C3` (env) + `§C1` (skill/SLA values)** — these B/C sections are the harvested
knowledge of a *prior* frontend implementation that was reset to clean slate; treat them as the
authoritative spec for the wire/SSE/port shape.

> **This is a large, cross-cutting task** (Python async SSE/REST BFF servers **plus** a React
> multi-app workspace + shared package + snake→camel domain layers + SSE close discipline + Playwright
> one-shot-SSE stubbing + two presentation modes + time-warp over the virtual clock). Execute it in
> the **phased order in §9**, verifying green at each phase. Do not try to land it all at once.

---

## 1. Goal (what "done" means)

Turn the S0.4 single-app placeholder shell into **Frontend v1**: the three actor surfaces + the
time-warp presenter control, each backed by a thin Python BFF server, wired end-to-end against the
real local components already built in M1 (bridge core, A2UI edge M1.10, scheduler M1.12, the address
agent graph S1-6). Concretely:

1. **Processing-Agent Console** (`/console`, internal, **SSE**) — the agent's mind per turn: the
   ledger it was handed, its reasoning, the `is_satisfied` satisfaction check, and the returned
   requirements list (`required | optional | satisfied | waived`) with `done`. **Sense B is watchable
   here** (the agent — not the Bridge — rejects the two-same-issuer set and asks for one more). Folds
   in a **Timeline**.
2. **Servicer Ops Dashboard** (`/ops`, internal, **SSE**) — the read-model: exchanges in flight, each
   exchange's classified ledger filling live, disposition outcomes, and the **HITL** + **escalation**
   queues.
3. **End-user / Provider Portal** (`/portal`, external, **REST**) — the A2UI **Path-B** surface
   (M1.10): upload a document (fixture id in local/demo), see its disposition + what's still
   outstanding. The only surface across the trust boundary.
4. **Time-warp** (`/timewarp`, **plain REST, no SSE**) — presenter control over the virtual clock:
   fast-forward an SLA window so `overdue → escalated` fires on cue; step / pause; replay.
5. **Presentation modes:** **Split-Screen Theater** (default — portal left/external ↔ console+ops
   right/internal, Gateway boundary drawn between) and **Timeline** (scrubbable event stream).

**Single hardest acceptance:** with the four BFF servers running against local adapters + the fixture
extraction engine, a Playwright e2e drives the Split-Screen Theater through the address arc — request
→ ledger fills → sense-B reject of two-same-issuer bills → time-warp fast-forwards the SLA →
`overdue → escalated` on the ops dashboard — using the **one-shot SSE stub** (B1) at the network
boundary, green in CI.

### Non-goals (do NOT do here)
- **No GCP / Terraform deploy.** `docs/features/frontend.md` lists "Terraform to deploy portal +
  console/dashboard" — that is **Sprint 2** (GCP adapters + IaC). Frontend v1 is **local only**.
- **No Architecture X-Ray** (Phase 4). No Benefits/RFP surface additions (Phase 2/3): no
  negotiate/bind, no program-comparison, no casefile view, no live-requirement-mutation view.
- **No real blob upload / Gemini.** Portal intake carries a `fixture_id` (demo furniture, M1.10);
  real blob→Gemini is Sprint 2/Phase 4.
- **No new domain logic.** Completeness is `is_satisfied` (agents) / `propose_requirements` (bridge
  M1.9); disposition is `run_disposition_gate` (M1.6). The frontend/BFF **project and relay** — they
  never recompute the satisfaction rule or mint a disposition (invariant: *LLM routes, code decides*;
  a model/UI may never mint a KYC acceptance).
- **No production-agent coupling.** `agent.py`/`graph.py` MUST stay import-clean of the demo servers.
  The BFF servers are **demo furniture** (like `tests/support/live_bridge_server.py`) and are the
  only agent-side code allowed to `import bridge`.

---

## 2. Current state (verified) — what you inherit

- **`frontend/` is a SINGLE Vite app** (react-ts + MUI + react-router), NOT a workspace. Pages:
  `src/pages/{Console,Ops,Portal}.tsx` are static placeholders; `src/components/Layout.tsx` (AppBar +
  nav to `/console`, `/ops`, `/portal`); `src/App.tsx` routes; `src/theme.ts`. Scripts: `dev/build/
  lint/format/format:check/test (vitest run)/test:e2e (playwright)/preview`. `packageManager:
  pnpm@10.33.0`, node 22. `e2e/smoke.spec.ts` + `playwright.config.ts` (webServer = `pnpm preview
  --port 4173`, baseURL `http://localhost:4173`). Vitest excludes `e2e/**`. **No timewarp page, no
  SSE, no domain/ layer, no shared package.** S0.4 plan explicitly says Sprint 1 splits this into
  per-surface apps + a shared package — **that split is this task.**
- **Backend BFF servers do NOT exist.** `docs/lessons-learned.md §C2` port map names them but no code
  exists: `agents.address.console_server:app` (8010, SSE), `ops_server:app` (8011, SSE),
  `portal_server:app` (8012, REST), `timewarp_server:app` (8013, REST no-SSE). The core a2a app
  (`bridge.edges.a2a.app:create_app`) is 8000. **You build all four BFF servers.**
- **Backend building blocks that already exist and you wire against:**
  - `agents/src/agents/address/graph.py` — the durable Collect loop (`build_collect_node`,
    `build_gate`, `build_present`); `is_satisfied` in `satisfaction.py`; `EXCHANGE_CONTEXT_STATE_KEY`
    threaded on session state; the ledger/turn live on the shared session.
  - `bridge/src/bridge/edges/a2ui/` (M1.10): `build_screen`, `party_status_view`, `submit_intake`,
    `render_screen`, `A2uiResponse`, `A2uiScreen`, `IntakeMode`, `intake_to_document`. **The portal
    BFF wraps these.**
  - `bridge/src/bridge/scheduler.py` + `adapters/local/scheduler.py` (M1.12): durable Scheduler seam
    with an **injectable virtual clock**; `due(now)` marks timers `fired` in place (exactly-once).
    **The timewarp BFF drives this.**
  - `bridge.edges.a2a.app:create_app` (M1.8): the read-model source for ops (exchanges, ledger,
    disposition). `bridge/src/bridge/seams/exchange_store.py` (`get/save/materialize`).
  - `agents/pyproject.toml` already depends on `a2a-document-bridge-core` (bridge) **and**
    `a2a-document-bridge-contract` — so the BFF servers CAN import bridge/contract. FastAPI/uvicorn
    are **not yet** deps (Starlette is, transitively via a2a-sdk); **add `fastapi` + `uvicorn` +
    `sse-starlette` to `agents/pyproject.toml`** (or use raw Starlette `StreamingResponse` as the
    mock/core apps do — see §4 decision).
  - `wiki/evals/address/`: `expected.json` (8 fixtures), `timeline.json` (event stream for Timeline
    mode + as an e2e script source), `description.md`, `images/`.

---

## 3. Key design decisions & gotchas (READ before coding — hard-won, do not re-derive)

- **B1 — the one-shot SSE stub for Playwright.** Playwright's `page.route` fulfills **one-shot**, but
  `EventSource` wants a live `text/event-stream`. The working trick: deliver the **entire** scripted
  stream (all `snapshot`/`turn` frames + the terminal `done`) as a **single response body**; the
  client closes on `done`, so the connection-end never triggers a reconnect. Put this in
  `frontend/e2e/sse.ts` + document in `frontend/e2e/README.md`.
- **B2 — client-side SSE close discipline.** Every frontend SSE client sets a `finished` flag so the
  **expected** server-side close after `done` does not surface as an error. The Python `_sse()`
  emitters must mirror this (emit a terminal `done` event, then close cleanly).
- **B3 — the wire is snake_case; every surface hand-maps to camelCase in its own `domain/` layer.**
  The A2A/console contract is snake_case on the wire (`key_fields → keyFields`, `doctype_hint →
  doctypeHint`), camelCase in TS. Each surface re-implements the mapping in `<app>/src/domain/`
  (e.g. `provider-portal/src/domain/outstanding.ts`, `ops-dashboard/src/domain/readModel.ts`,
  `agent-console/src/domain/sense.ts`). **Real domain logic (sense-B derivation, ops read-model
  projection) lives in `domain/` and is unit-tested directly** (Vitest) — do not rely on browser e2e
  alone. Factor the shared contract types into the shared package (`domain/contract.ts`), but each
  surface keeps its own projection.
- **B4 — time-warp deliberately avoids SSE.** The timewarp server is **plain REST, no server
  background task** — a virtual clock has no wall-clock progression, so **"Play" is the browser on a
  `setInterval`** hitting a `tick`/`advance` REST endpoint. This dodges the SSE fan-out /
  orphaned-background-task concurrency the ops-dashboard already has to solve. "Play" is intentionally
  **not** e2e-tested (timer-driven, flaky) — e2e uses explicit step/advance calls instead.
- **Shared package to avoid 4-way copy-paste** (`docs/features/frontend.md` watch-item): factor
  `theme.ts`, `Panel.tsx`, `Badges.tsx`, `domain/contract.ts`, and the SSE client hook into a shared
  workspace package (`frontend/packages/shared/` → `@bridge/shared`). Each of the 4 apps depends on
  it via `workspace:*`.
- **pnpm workspace vs. the S0.1 CI job.** The S0.1 CI `frontend` job runs (cwd `frontend/`):
  `pnpm install --frozen-lockfile` → `pnpm lint` → `pnpm test` → `pnpm build` → playwright install →
  `pnpm test:e2e`. When you convert to a workspace, the **root `frontend/package.json` scripts must
  fan out recursively** (`pnpm -r lint`, `pnpm -r test`, `pnpm -r build`) so the four contract script
  names still exit 0 from `frontend/`. Keep `packageManager: pnpm@10.33.0`. Add `pnpm-workspace.yaml`
  (`packages: ['apps/*', 'packages/*']`). Regenerate + **commit `pnpm-lock.yaml`** (CI is
  `--frozen-lockfile`). Keep Playwright e2e at the **`frontend/` root** (one `playwright.config.ts`,
  one `e2e/` dir) driving the Split-Screen Theater across apps — don't scatter e2e per app.
  - **Gotcha:** a single dev server that hosts all four surfaces is far simpler for e2e + Split-Screen
    Theater than four Vite dev servers behind a proxy. **Recommended:** keep **one Vite app**
    (`apps/theater/`, the host shell) that mounts all four surfaces as routed React modules, and make
    `agent-console`/`ops-dashboard`/`provider-portal`/`timewarp` **library packages** (`packages/*`)
    consumed by the host — rather than four independently-served Vite apps. This satisfies "per-surface
    apps + shared package" (the surfaces are separable packages) while keeping one build/dev/preview/
    e2e target and one `dist/` for Playwright's `webServer`. Record this deviation from §C2's
    "one Vite dev server per surface" in the README (§C2's per-surface ports are for the **BFF
    servers**, which stay four separate uvicorn processes; the Vite proxy forwards each `/console`,
    `/ops`, `/portal`, `/timewarp` prefix to its backend port). If you instead prefer true multi-app
    Vite, you must add a proxy/orchestration layer and multi-webServer Playwright config — more work,
    same outcome; the single-host-shell approach is the intended one.
- **snake→camel only at the domain boundary.** Keep raw wire types (snake) at the SSE/fetch client;
  map to camel in `domain/`; components consume camel only. Do not sprinkle `snake_case` through JSX.
- **Sense B is the console's whole point.** The console must visibly show the agent rejecting two
  bills from the **same** issuer (canonicalized) and asking for one more — driven by `is_satisfied`
  over the classified ledger. Source the reasoning/ledger/satisfaction/requirements per turn from the
  console BFF (which observes the agent graph run). Do **not** recompute completeness in TS.
- **The BFF servers may import bridge; the production agent may not.** Mirror the discipline in
  `agents/pyproject.toml` (comment: "production agent must NOT import bridge; only the parity test
  server does") — extend "…and the demo BFF servers (`*_server.py`)". Keep `agent.py`/`graph.py`
  free of any `*_server` import.
- **Skill/SLA values for time-warp** (`§C1`): `address-proof` policy — `deadline: 3`, `cadence: 2`,
  `max_nudges: 2` ticks, ladder `overdue → reminder → escalated`; thresholds `0.55`/`0.85`. The
  timewarp UI fast-forwards ticks; after `deadline` ticks with no fulfillment, ops shows `escalated`.
- **Env/config** (`§C3`): `BRIDGE_CLOCK_MODE=virtual`, `BRIDGE_EXTRACTION_ENGINE=fixture`,
  `BRIDGE_SKILLS_DIR=./skills`, `BRIDGE_FIXTURES_DIR` (now `wiki/evals/`), `BRIDGE_SEAM_MODE=local`.
  The BFF servers read these; document per-server port defaults (8010–8013) with env overrides.

---

## 4. Backend: the four BFF servers (`agents/src/agents/address/`)

Build these first (the frontend consumes them). Follow the existing Starlette idiom in
`agents/src/agents/mock_bridge/app.py` and `bridge/src/bridge/edges/a2a/app.py` (Starlette app +
lifespan + routes). **Decision:** use **Starlette + `sse-starlette`'s `EventSourceResponse`** for the
SSE servers (console/ops) and **plain Starlette JSON routes** for portal/timewarp — this matches the
repo's existing Starlette usage and avoids introducing FastAPI. Add `sse-starlette` to
`agents/pyproject.toml`; `uvicorn` is needed to run them (add it; a2a-sdk pulls Starlette already).
Each module exposes a module-level `app` (so `uvicorn agents.address.console_server:app` works, per
§C2) built by a `create_app(...)` factory (testable without a live socket).

Shared conventions for all four:
- CORS enabled for the Vite dev origin (localhost:5173 or the theater port) — dev only.
- A `GET /health` returning `{"status":"ok"}`.
- Snake_case JSON on the wire (the frontend `domain/` maps to camel — B3).
- SSE emitters (`_sse()`): yield `snapshot` (initial full state) then incremental `turn`/`event`
  frames, then a terminal **`done`** event, then return (clean close — B2). Named SSE events
  (`event: snapshot` / `event: turn` / `event: done`).

### 4.1 `console_server.py` (port 8010, SSE) — Processing-Agent Console BFF
- Drives an address-agent **Collect run** in-process (reuse `graph.py`'s
  `build_collect_node`/`build_gate`/`build_present` + a Runner on local session service, as the S1-6
  test harness does) against a chosen scenario (default: distinct-issuer arc so sense-B reject is
  visible), and streams **per-turn** frames: `{ledger_handed, reasoning, satisfaction:{done,
  outstanding}, requirements:[{item,status}], round}`.
- `GET /console/stream?scenario=<id>` → SSE. `GET /console/scenarios` → scenario list.
- The satisfaction check comes from `is_satisfied(...)` over the ledger (authoritative — do not
  recompute in TS). Reasoning text can be the agent's turn output / a structured summary of why it
  routed `again` vs `done`.

### 4.2 `ops_server.py` (port 8011, SSE) — Servicer Ops Dashboard BFF
- Stands up an **in-process Bridge core** on local adapters (import bridge — allowed for demo
  servers) OR observes the same run as console; streams the **read-model**: exchanges in flight, each
  exchange's classified ledger (`list[LedgerEntry]` + outstanding + terminal), disposition outcomes,
  and the **HITL** + **escalation** queues.
- `GET /ops/stream` → SSE (`snapshot` = current read-model; `event` frames on each disposition / queue
  change / `overdue→escalated`). `POST /ops/hitl/{id}/{approve|reject}` → resolve a HITL item
  (drives the M1.7 resumable HITL phase). Escalation surfaces from the scheduler ladder (M1.12) —
  wired via the timewarp server's clock (shared scheduler instance; see §4.4).
- The ops read-model projection reference lives in TS `ops-dashboard/domain/readModel.ts` (B3) — the
  server sends raw ledger/queue snapshots; the projection (grouping by actionable state, per
  **exchange** not raw task) is the TS domain layer.

### 4.3 `portal_server.py` (port 8012, REST) — Provider Portal BFF (A2UI Path-B)
- Thin wrapper over the M1.10 A2UI edge:
  - `GET /portal/screen?context=<id>` → `build_screen(status, requirements).model_dump(mode="json")`
    (the declarative `A2uiScreen`: party-status view + intake spec).
  - `POST /portal/intake` body `{mode, fixture_id, text?, fields?}` → construct `A2uiResponse` →
    `await submit_intake(response, engine=FixtureExtractionEngine(), attempts=<prior>)` → return the
    `FulfillmentResult` + refreshed screen. Thread `attempts` for the non-resumable resubmit loop (A1).
- **Content-not-pixels:** the server emits the declarative screen; the portal renders it in MUI. The
  M1.10 `render_screen` (text) is demo furniture — the React portal is the real host here.

### 4.4 `timewarp_server.py` (port 8013, REST, **no SSE** — B4) — virtual-clock control
- Owns/holds the **shared virtual clock + Scheduler** instance (M1.12) that ops (§4.2) reads, so
  advancing the clock here surfaces `overdue→escalated` there.
- `GET /timewarp/state` → `{now, sla:{deadline,cadence,max_nudges}, timers:[...], phase}`.
- `POST /timewarp/advance` body `{ticks:int}` → advance the virtual clock N ticks, call
  `scheduler.due(now)` (marks timers `fired` in place — **exactly-once**, A7), return new state.
- `POST /timewarp/step` → advance one tick. `POST /timewarp/reset` → reset the clock/scenario
  (replay). **No background task** — the clock only moves on an explicit request; the browser's
  `setInterval` ("Play") calls `/advance` repeatedly (B4).

### 4.5 Run scripts + port map (`scripts/` — new dir)
- Create `scripts/run-console.sh`, `run-ops.sh`, `run-portal.sh`, `run-timewarp.sh`, `run-core.sh`
  (uvicorn on 8010–8013 / 8000 per §C2), plus a `scripts/run-all.sh` (background all + the theater
  Vite dev). Reference `§C2`'s `bootstrap.sh` sequence and Vite-proxy-per-prefix convention.
- Document the port map in `agents/README.md` (extend the existing run doc) and `frontend/README.md`.

---

## 5. Frontend: workspace restructure + the surfaces (`frontend/`)

### 5.1 Restructure to a workspace (one host shell + surface packages + shared)
- `frontend/pnpm-workspace.yaml`: `packages: ['apps/*', 'packages/*']`.
- `frontend/apps/theater/` — the **host shell** Vite app (moves the current `src/` here): AppBar +
  nav + router; hosts all four surfaces as routed modules; owns `playwright.config.ts` webServer
  target (`pnpm --filter theater preview`). Also implements the **Split-Screen Theater** layout.
- `frontend/packages/shared/` (`@bridge/shared`): `theme.ts` (move from `src/theme.ts`),
  `Panel.tsx`, `Badges.tsx` (disposition/status chips), `domain/contract.ts` (shared snake→camel
  contract types + mappers), `useSse.ts` (the SSE client hook with B2 close discipline), zone-boundary
  visual.
- `frontend/packages/agent-console/`, `packages/ops-dashboard/`, `packages/provider-portal/`,
  `packages/timewarp/` — one package per surface, each exporting a React component + its own
  `src/domain/` mapping layer. Each `depends on @bridge/shared` via `workspace:*`.
- Root `frontend/package.json`: scripts fan out (`"lint":"pnpm -r lint"`, `"test":"pnpm -r test"`,
  `"build":"pnpm -r build"`, `"test:e2e":"playwright test"`, `"dev":"pnpm --filter theater dev"`,
  `"preview":"pnpm --filter theater preview"`, `"format"`/`"format:check"` at root over the tree).
  Keep `packageManager` + node 22. **Regenerate and commit `pnpm-lock.yaml`.**
- Vite dev proxy (in `apps/theater/vite.config.ts`): forward `/console`→8010, `/ops`→8011,
  `/portal`→8012, `/timewarp`→8013 (per §C2).

### 5.2 The surfaces (React + MUI, content-not-pixels)
- **agent-console** — per-turn cards: *Ledger handed* → *Reasoning* → *Satisfaction check
  (done + outstanding)* → *Requirements list* (chips `required|optional|satisfied|waived`, `done`
  badge). Consumes `/console/stream` via `useSse`. `domain/sense.ts` derives the sense-B display from
  the raw turn frames (the reject-two-same-issuer beat must be legible). Folds in the **Timeline**
  (§5.3).
- **ops-dashboard** — exchanges-in-flight list; per-exchange classified-ledger table filling live;
  disposition outcomes; **HITL queue** (approve/reject buttons → `POST /ops/hitl/...`); **escalation
  queue**. Consumes `/ops/stream`. `domain/readModel.ts` projects raw snapshots → grouped-by-
  actionable-state, **per exchange** (B3).
- **provider-portal** — renders the declarative `A2uiScreen` from `/portal/screen`: party-status
  ("sent / accepted / outstanding / next") + intake affordance (upload fixture / paste text). Submit
  → `POST /portal/intake` → show disposition + refreshed outstanding. `domain/outstanding.ts` maps
  the wire screen to camel. **External-zone** styling (visually across the Gateway boundary).
- **timewarp** — presenter control: shows virtual `now` + SLA window; **Step** / **Advance N** /
  **Reset** buttons hit the timewarp REST endpoints; **Play** = browser `setInterval` calling
  `/advance` (B4). Watching ops during Play shows `overdue → escalated`.

### 5.3 Presentation modes
- **Split-Screen Theater** (default route, e.g. `/` or `/theater`): provider-portal (left, external
  zone) ↔ agent-console + ops-dashboard (right, internal zone), with the **Gateway boundary drawn
  between** them. Time-warp control docked (e.g. a top/bottom bar). One story, both zones.
- **Timeline** (`/timeline` or a console fold-in): the exchange as a scrubbable event stream
  (request → arrivals → chase → escalate → deliver). Source events from the console/ops streams and/or
  `wiki/evals/address/timeline.json`. Scrubbing replays frames from a buffered event log (no re-fetch).

---

## 6. Seams touched

**None new.** The frontend is not a managed-service boundary (no local+GCP adapter pair — per the
S0.4 note). The BFF servers **consume** existing seams (Scheduler M1.12, Exchange/Task store M1.2,
Extraction fixture M1.7, Skill registry M1.3) via the already-built local adapters; they add **no new
seam** and no GCP adapter (that's Sprint 2's deploy work). Honor the invariants transitively: the
classified ledger has no timestamp (deterministic sort key already in the adapter — don't reorder in
TS); scheduler `due(now)` is exactly-once (drive it, don't reimplement); trust boundary is
permissive-by-default (zones are a *visual* here, enforced at the network layer in deploy — Sprint 2).

---

## 7. Tests to add

- **Python (BFF servers) — `agents/tests/`** (pytest, `uv run pytest` from `agents/`):
  - `test_console_server.py` — drive `create_app`'s SSE endpoint with an ASGI test client; assert the
    distinct-issuer scenario streams a turn where `satisfaction.done is False` with the same-issuer
    set rejected and one bill outstanding, then `done` after a distinct second bill (sense B). Assert a
    terminal `done` event closes the stream (B2).
  - `test_ops_server.py` — assert the read-model snapshot buckets ledger/HITL/escalation; assert
    `POST /ops/hitl/{id}/approve` resolves the item; assert an escalated exchange appears after the
    clock passes `deadline`.
  - `test_portal_server.py` — `POST /portal/intake` with `fixture_id="gov-id-clean"` → auto-approve;
    `bill-aquautil-blurry` → resubmit; `passport-unsupported` → rejected; `GET /portal/screen`
    round-trips a JSON `A2uiScreen`. (Parity anchor: same `FulfillmentResult` as M1.10 `submit_intake`.)
  - `test_timewarp_server.py` — `POST /timewarp/advance {ticks:3}` fires the SLA timer **exactly
    once** (A7) and moves the exchange `overdue→escalated`; `reset` restores; **no background task**
    (state only changes on request — B4).
- **Frontend unit (Vitest, per package `domain/`)** — the reference domain logic (B3):
  - `agent-console/src/domain/sense.test.ts` — sense-B derivation (two same-issuer bills → not done,
    ask one more; distinct issuers → done).
  - `ops-dashboard/src/domain/readModel.test.ts` — projection groups by actionable state, per exchange.
  - `provider-portal/src/domain/outstanding.test.ts` — snake→camel map + outstanding/next derivation.
  - `shared/domain/contract.test.ts` — the snake→camel mappers (`key_fields→keyFields`,
    `doctype_hint→doctypeHint`).
- **Playwright e2e — `frontend/e2e/`** (the S0.1 CI step already runs `pnpm test:e2e`):
  - Add `e2e/sse.ts` (the **one-shot SSE stub** — B1: whole scripted stream incl. `done` as one body)
    + `e2e/README.md` documenting B1/B2.
  - `e2e/theater.spec.ts` — the Split-Screen Theater arc: stub `/console/stream` + `/ops/stream` (SSE
    one-shot) and `/timewarp/*` (REST), drive request → ledger fills → sense-B reject → time-warp
    **Advance** (explicit, not Play — B4) → `overdue→escalated` on ops. Assert visible headings +
    zone boundary rendered. Keep the existing `smoke.spec.ts` (or fold into theater) green.
- **CI:** no `ci.yml` change needed — the `frontend` job already runs install→lint→test→build→
  playwright→e2e, and there is no dedicated BFF-server job beyond the existing `agents` job (the new
  `agents/tests/test_*_server.py` run under it). Verify the `agents` job stays green with the new
  `fastapi`/`sse-starlette`/`uvicorn` deps (regenerate `agents/uv.lock`, commit it).

---

## 8. Files to create / modify (summary)

**Create (backend):**
- `agents/src/agents/address/console_server.py`, `ops_server.py`, `portal_server.py`,
  `timewarp_server.py`
- `agents/tests/test_console_server.py`, `test_ops_server.py`, `test_portal_server.py`,
  `test_timewarp_server.py`
- `scripts/run-console.sh`, `run-ops.sh`, `run-portal.sh`, `run-timewarp.sh`, `run-core.sh`,
  `run-all.sh`

**Modify (backend):**
- `agents/pyproject.toml` — add `sse-starlette`, `uvicorn`; extend the "servers may import bridge"
  comment to include `*_server.py`. Regenerate + commit `agents/uv.lock`.
- `agents/README.md` — run doc: start the four servers + core + theater; port map.

**Create/restructure (frontend):**
- `frontend/pnpm-workspace.yaml`; `frontend/apps/theater/` (host shell, moved from current `src/`);
  `frontend/packages/shared/` (`theme.ts`, `Panel.tsx`, `Badges.tsx`, `domain/contract.ts`,
  `useSse.ts`); `frontend/packages/{agent-console,ops-dashboard,provider-portal,timewarp}/` each with
  `src/` + `src/domain/` + a package.json (`@bridge/*`, `workspace:*` dep on shared).
- `frontend/e2e/sse.ts`, `frontend/e2e/README.md`, `frontend/e2e/theater.spec.ts`.
- Per-package Vitest `domain/*.test.ts` files (§7).

**Modify (frontend):**
- `frontend/package.json` — recursive scripts (`pnpm -r ...`), keep `packageManager`/engines;
  regenerate + commit `pnpm-lock.yaml`.
- `frontend/apps/theater/vite.config.ts` — dev proxy for `/console`,`/ops`,`/portal`,`/timewarp`;
  keep the Vitest `test` block + `e2e/**` exclude.
- `frontend/playwright.config.ts` — webServer → `pnpm --filter theater preview` (built `dist/`).
- `frontend/README.md` — document the workspace layout, per-surface packages, the shared package, the
  BFF port map (§C2), the single-host-shell deviation (§3), and the snake→camel `domain/` rule (B3).

---

## 9. Suggested execution order (phased — verify green at each step)

1. **Backend BFF skeletons first** (no frontend yet): add deps; build the four `*_server.py` with
   `create_app` factories + `/health`; write `test_*_server.py`; `cd agents && uv run ruff check . &&
   uv run pytest` green. This de-risks the wire shape before any React.
2. **Workspace restructure** (frontend still placeholders): pnpm-workspace, host shell in
   `apps/theater/`, `packages/shared/`, four empty surface packages; recursive scripts; commit
   lockfile; `pnpm -r lint/test/build` + existing `smoke.spec.ts` green.
3. **Wire each surface to its BFF** one at a time (portal → ops → console → timewarp), each with its
   `domain/` layer + Vitest domain tests. Verify against the running server manually / via the domain
   unit tests.
4. **Presentation modes:** Split-Screen Theater layout + zone boundary; Timeline scrub.
5. **e2e:** `sse.ts` one-shot stub + `theater.spec.ts`; `pnpm build && pnpm test:e2e` green locally,
   then confirm the CI `frontend` job passes.
6. **Run scripts + docs;** final full green (`agents/` pytest + `frontend/` lint/test/build/e2e).

## 10. Acceptance criteria (all must hold)
1. Four BFF servers exist under `agents.address.*_server` on ports 8010–8013 per §C2 (console/ops =
   SSE, portal/timewarp = REST; timewarp has **no** background task — B4); each has a `create_app`
   factory + passing pytest; the production agent (`agent.py`/`graph.py`) imports none of them.
2. `frontend/` is a pnpm **workspace** — host shell (`apps/theater`) + four surface packages + a
   shared package; root `pnpm lint`/`test`/`build` (recursive) exit 0; `pnpm-lock.yaml` committed;
   `packageManager: pnpm@10.33.0` kept.
3. **Processing-Agent Console** shows per-turn ledger/reasoning/satisfaction/requirements and the
   **sense-B reject** of two same-issuer bills (via `is_satisfied`, not recomputed in TS).
4. **Ops Dashboard** shows exchanges-in-flight + live classified ledger + disposition + **HITL** and
   **escalation** queues; HITL approve/reject resolves via the BFF.
5. **Provider Portal** hosts the M1.10 A2UI Path-B screen (declarative, content-not-pixels): submit a
   fixture intake → disposition + refreshed outstanding; resubmit threads `attempts`.
6. **Time-warp** advances the virtual clock via REST (step/advance/reset; Play = browser
   `setInterval`), driving `overdue → escalated` on ops (exactly-once timer firing — A7).
7. **Split-Screen Theater** (default) renders portal (external) ↔ console+ops (internal) with the
   Gateway boundary drawn between; **Timeline** mode scrubs the event stream.
8. Each surface hand-maps snake→camel in its own `domain/` layer, unit-tested (Vitest); the SSE
   clients honor the `finished`/close discipline (B2).
9. Playwright e2e drives the theater arc via the one-shot SSE stub (B1); the CI `frontend` job
   (install→lint→test→build→playwright→e2e) is green, and the `agents` job (with new deps + server
   tests) is green.
10. No GCP/Terraform, no Gemini, no Benefits/RFP/X-Ray surfaces; invariants preserved (LLM
    routes/code decides; ledger sort key untouched; scheduler exactly-once).

## 11. Notes for the implementer
- The B/C lessons are a *reconstruction spec* of a prior build — when a detail here is thin, `§B`/`§C`
  and `docs/features/frontend.md` are the tie-breakers; the wiki pages give intent, not wire detail.
- Prefer reusing the S1-6 durable-graph run harness (`agents/tests/test_durable_graph.py`) as the
  pattern for the console/ops in-process agent+bridge run rather than inventing new orchestration.
- Keep the reference `render_screen` (M1.10, Python text) untouched — the React portal supersedes it
  as the host, but the text renderer stays as demo furniture / a contract check.
- If four independent Vite dev servers are attempted instead of the single host shell, budget extra
  time for a proxy + multi-`webServer` Playwright config; the host-shell approach in §3 is the
  intended, lower-risk path.
