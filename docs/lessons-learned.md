# Lessons Learned — A2A Document Bridge (invariants to carry into the build)

> **Why this file exists.** The Bridge is a clean-slate build against the `wiki/` + `docs/` spec. A
> lot of the hard-won rationale is the kind that normally lives *outside* the spec — the non-obvious
> invariants, the correctness traps, and the concrete config values a build would otherwise re-derive
> by guesswork. This document captures them up front so the build doesn't re-pay for them.
>
> File paths below (e.g. `bridge/src/bridge/...`) are the **intended homes** for each concern, not a
> record of existing code. Companion to `docs/decisions/` (the ADRs).

---

## Part A — Design lessons & non-obvious invariants (carry these into the build)

### A1. Escalation ≠ rejection; `resubmit` is deliberately non-resumable
When extraction keeps failing after N resubmissions, the document routes to a **human**
(`phase="escalated"`, disposition `PENDING`) — **not** rejected. The rationale: *"the doc was never
judged wrong, we just gave up reading it."* Resumable phases are `{hitl, escalated}` only;
`resubmit` is **not** resumable because it awaits a *fresh document*, not a human decision. The build
that collapses "we can't read this" into "rejected" loses a real, correct distinction.

### A2. The mock↔real parity contract is terminal-outcome, NOT ledger-identical
The scripted mock Bridge and the real Bridge legitimately **diverge turn-by-turn**:
- The mock scripts a resubmission as `REJECTED`; the real Bridge suspends it `PENDING`.
- Path-A "instant accept" is 1 turn on the mock but ≥2 turns on the real Bridge (the document
  arrives via `/responses` *after* `open`).

So the swap-parity test asserts only the **terminal outcome** — `done` / `TerminalReason.DONE` plus
the accepted-issuer set — never a step-by-step ledger match. **The mock is a permanent contract
double, not throwaway.** The build must keep "parity = same destination, not same path" or the mock
will look broken when it is correct.

### A3. The ADK↔deterministic parity: the *code gate*, not the model, owns the verdict
The LLM-driven Collect loop (`LlmAgent`) must reach the **same terminal outcome** as the frozen
deterministic `run_collect` across all six golden branches — parity on **outcome**, never on turn
count. Two invariants the tests pin:
- Path-A short-circuits with **zero model calls**.
- A never-satisfying ledger hits `MAX_TURNS` with `done=False`.

This is the central safety property of the ADK-native runtime: **a model cannot mint a KYC
acceptance.** The satisfaction verdict (sense B) is a deterministic code gate the LLM cannot
override. Preserve this split (LLM routes / code decides) — see `docs/decisions/adr-0001-stack.md`.

### A4. Issuer canonicalization gotchas
- **"co" is NOT a corporate suffix.** `"Power Co."` must canonicalize to `power-co` (keep the `co`).
  Only `Ltd/Inc/LLC/GmbH/…` are stripped.
- **camelCase splitting can *fragment* a suffix** (`GmbH` → `Gmb H`), so the canonicalizer also tests
  the joined last-two tokens, not just the final token.
- **bridge↔mock canonicalization parity is convention-only** — `bridge/` never imports `agents/`, so
  the two implementations line up *by discipline*, enforced by the shared test suite. The build that
  shares a module here is fine, but if kept separate the convention must be re-established.

### A5. The ledger has no timestamp — it relies on dict insertion order (latent trap)
The classified ledger has **no `created_at`**; ordering rides on Python dict insertion order in the
in-memory projection. This works locally but is a **correctness trap for any relational/GCP backend**,
which returns rows unordered — the build's persistent adapter **needs a deterministic sort key**.
This was the single most-cited "plan gotcha" (#7) and appears **nowhere in wiki/docs**.

Related ledger invariants (from the plan's ranked list): the ledger is a **view, not a record**
(append-only projection over exchange tasks); the `_as_doctype` default-to-`utility-bill` fallback is
**load-bearing for parity** (don't "clean it up" blindly); coordinator-exclusion logic must stay in
the *edge* to avoid an import cycle.

### A6. Trust boundary is permissive-by-default (a deliberate footgun)
An unauthenticated / `None` caller is a **no-op** — per-party leg scoping is enforced **only under
`strict=True`**. This exists for **backward-compat with the header-free client** (an unchanged client
must keep driving `open → advance`). It is a real footgun: the build should decide whether to keep
permissive-default or flip to deny-default, but must do so *knowingly*. (The
"why" — header-free back-compat — is the load-bearing rationale.)

### A7. Scheduler idempotency: `due()` marks timers fired *in place*
`due(now)` marks each returned timer `fired` in place, so a second call never re-emits it — the
proactive engine's **no-duplicate-events** guarantee rides entirely on this. The GCP mirror uses
*"deletion is the fired signal"*; Agent Engine sessions have no upsert, so it's **delete-then-create**;
the relational adapter deliberately **connects-per-op** to dodge a class of stale-connection bugs.
The build of the scheduler must preserve exactly-once emission.

### A8. The core's label space is hard-coded, not skill-derived (the "honesty trap")
`_CANDIDATE_DOCTYPES = ("gov-id", "utility-bill")` is hard-coded in the disposition/validate-only
core — it is **not** derived from the installed skills. Consequence: even with the `gov-id` skill
*absent*, the core would still validate-accept a Path-A gov-id. This is why the two-run demo must
ground *"the capability didn't exist yet"* on the **Agent Card** (which is skill-derived), **never on
a rejection**. Do **not** "fix" the label space in isolation — it would break the sense-A disposition
tests. The build should make the label space genuinely skill-derived *and* update those tests
together.

### A9. Demo/console backends importing `bridge` is intentional, not a layering violation
The "agent unchanged" proof rests on the **agent core** (`run_collect`, satisfaction fn) never
importing `bridge`. But demo/console **furniture** (`two_run.py`, `timewarp_server.py`,
`portal_server.py`, `ops_server.py`) importing `bridge` is fine and precedented. Also: `demos/` is
**not** a uv workspace member, so demo backends live under `agents/src/agents/address/` to be
importable by `tests/` without path hacks. Keep the boundary at the *agent core*, not at "anything in
the demo tree."

### A10. Keep the "why" next to the invariant
The load-bearing invariants above (A1–A9) are exactly the ones that were previously scattered across
code comments and planning notes rather than the spec — the class of knowledge that silently rots
when it lives only in one place. As the build proceeds, keep each such rationale attached to the code
or the spec, not buried in a side channel; this file is the seed of that discipline, not a substitute
for it.

---

## Part B — Frontend / e2e integration knowledge

### B1. The one-shot SSE stub for Playwright
Playwright's `page.route` fulfills **one-shot**, but `EventSource` wants a live `text/event-stream`.
The working trick: deliver the **entire** scripted stream (all `snapshot`/`turn` frames + the terminal
`done`) as a **single response body**; the client closes on `done`, so the connection-end never
triggers a reconnect. This was hard-won (`e2e/sse.ts` + `e2e/README.md`).

### B2. Client-side SSE close discipline
Each frontend SSE client sets a `finished` flag so the **expected** server-side close after `done`
doesn't surface as an error. The Python `_sse()` emitters rely on this mirror pattern.

### B3. The wire is snake_case; every surface hand-maps to camelCase
The A2A/console contract is **snake_case on the wire**, camelCase in TS (`key_fields → keyFields`,
`doctype_hint → doctypeHint`). Each surface re-implements this mapping in its `domain/` layer
(`provider-portal/domain/outstanding.ts`, `ops-dashboard/domain/readModel.ts`). Real domain logic
(sense-B derivation, ops read-model projection) lived in `frontend/**/domain/` and was exercised only
by e2e — those are the reference implementations to consult.

### B4. Time-warp deliberately avoids SSE
The timewarp server is **plain REST, no server background task** — a virtual clock has no wall-clock
progression, so "Play" is the **browser** on a `setInterval`. This deliberately avoids the SSE
fan-out / orphaned-background-task concurrency problems the **ops-dashboard already had to solve**.
(For the same reason, "Play" is intentionally *not* e2e-tested — timer-driven, flaky.)

---

## Part C — Config values worth carrying forward (from deleted `skills/`, `infra/`, scripts)

The strict "keep only wiki + docs" delete removes the actual, consumable config. `docs/` describes
the *format*; these are the concrete **values** the build would otherwise re-derive by guesswork.

### C1. Skills — runtime config (`skills/`)
Three skills; kinds via `metadata.bridge-kind`:

- **`address-proof`** (process, `bridge-pattern: collect`, `candidate-doctypes: "gov-id utility-bill"`).
  `policy.yaml` (feeds `ExtractionPolicy.from_mapping` + `SLAPolicy.from_mapping`; matches coded
  defaults):
  - thresholds: `resubmit_below: 0.55`, `auto_approve_at: 0.85`
  - retry: `max_resumissions: 3` *(sic — `max_resubmissions: 3`)*
  - sla: `deadline: 3`, `cadence: 2`, `max_nudges: 2` (ticks; ladder overdue→reminder→escalated)
  - The skill declares **no** satisfaction rule — completeness is the app's (sense B). Thresholds
    `0.55 / 0.85 / 3` are also in ADR-0002; the **SLA numbers are only here**.
- **`gov-id`** (doctype, `extraction-engine: gemini`). Required fields: `doctype` (enum `gov-id`),
  `full_name`, `document_number`, `expiry_date` (ISO date). Validation rules (parsed, not yet
  enforced in Phase 1): `not_expired` (expiry_date in future), `complete_fields`. Active disposition
  signals: `legibility`, `type_match`, `confidence` (completeness disabled — it's the agent's sense-B).
- **`utility-bill`** (doctype, `extraction-engine: gemini`). Required fields: `doctype` (enum
  `utility-bill`), `issuer` (canonicalized), `account_holder`, `service_address`, `statement_date`.
  Validation rules: `recent_bill` (`window_days: 90`), `address_present`. Same active signals as
  gov-id. Canonicalization: `PowerCo` / `Power Co.` / `PowerCo Ltd` → `power-co` (see A4).

The `gov-id` skill appears in **no** wiki/docs page — it exists only here.

### C2. Local run topology — port map (`scripts/run-*.sh`)
Each backend pairs with `pnpm --filter @bridge/<surface> dev`, whose Vite proxy forwards the prefix
to the port:

| Port | uvicorn target | Surface / prefix |
|---|---|---|
| 8000 | `bridge.edges.a2a.app:create_app` (factory) | core |
| 8010 | `agents.address.console_server:app` (SSE) | agent-console `/console` |
| 8011 | `agents.address.ops_server:app` | ops-dashboard `/ops` |
| 8012 | `agents.address.portal_server:app` | provider-portal `/portal` |
| 8013 | `agents.address.timewarp_server:app` (REST, no SSE) | time-warp `/timewarp` |

`bootstrap.sh` sequence: tooling check → `.env` copy → `uv sync` → pnpm install → `docker compose up
-d postgres`. `docker-compose.yml` runs **Postgres only** on purpose — the app runs on the host so the
seam-parity story (local vs GCP adapters) holds.

### C3. Env-var contract (`.env.example`)
- **Seam mode:** `BRIDGE_SEAM_MODE=local|gcp`, with per-seam overrides
  `BRIDGE_SEAM_{SESSIONS,TASK_STORE,EXCHANGE_STORE,SKILL_REGISTRY,SCHEDULER}` (blank = inherit) —
  lets you move one boundary onto a managed service at a time.
- **Extraction is its own axis** (capability, not local/gcp): `BRIDGE_EXTRACTION_ENGINE=fixture|gemini|docai`
  (`fixture` default; `BRIDGE_EXTRACTION_GEMINI_MODEL=gemini-2.0-flash`).
- **Skills:** `BRIDGE_SKILLS_DIR=./skills`. **Fixtures:** `BRIDGE_FIXTURES_DIR` (now the eval corpus
  lives in `wiki/evals/` — update this in the build). **Clock:** `BRIDGE_CLOCK_MODE=virtual`.
- **GCP knobs** (set from Terraform outputs): `BRIDGE_GCP_TASKS_{QUEUE,TARGET_URL,SERVICE_ACCOUNT}`,
  `BRIDGE_GCP_SESSIONS_APP_NAME`, `BRIDGE_GCP_SKILLS_BUCKET`,
  `BRIDGE_GCP_IDENTITY_{AUDIENCE,ALLOWED_PARTIES}`. Test opt-ins: `BRIDGE_TEST_GCP=1`,
  `BRIDGE_TEST_GEMINI=1`.

### C4. Terraform defaults (`infra/terraform/terraform.tfvars.example`)
8 modules (network / runtime / gateway / iam / database / tasks / secrets / frontend). Key defaults:
- Two-zone trust CIDRs: `external_subnet_cidr=10.10.0.0/24`, `internal_subnet_cidr=10.20.0.0/24`,
  `connector_cidr=10.8.0.0/28` (connector **must** be /28).
- Cloud SQL Postgres 16: `db_tier=db-f1-micro`, `ZONAL`, `db_name=bridge`, `db_user=bridge`,
  `db_disk_size=10`, `private_services_cidr_prefix=16`.
- Cloud Tasks: `tasks_queue_name=bridge-followups`, `tasks_max_dispatches_per_second=10`,
  `tasks_max_attempts=5`.
- Gateway off by default (`enable_gateway=false`); when on, needs ≥1 domain. Standalone ingress
  `INGRESS_TRAFFIC_ALL`.
- **Two-phase-apply gotcha:** in standalone mode the Cloud Run URL is only known after the first
  apply, so `tasks_target_url` is set and re-applied on a second pass.
- Frontend surfaces: provider-portal (external zone, `/portal`), agent-console + ops-dashboard
  (internal zone, `/console` `/ops`); per-party `run.invoker` scoping; portal public-invoker toggle.
- No secrets/real project IDs are in the examples (placeholders only) — nothing sensitive is lost.
- The `*.tftest.hcl` suite (credential-free `mock_provider` plan-time tests) was the **only** proof
  the config was coherent — it was never `apply`d. The build's infra needs its own such check.

### C5. ADK / A2A version targets to pin from day one
- **`google-adk >= 2.7.0, < 3`.** `ResumabilityConfig` is `[EXPERIMENTAL]` in 2.7.0 and is what
  long-running HITL pause/resume relies on. Two crux APIs to verify with a spike before leaning on
  them: (1) HITL pause/resume via a long-running function call + an id/name-matched `FunctionResponse`
  fed back through `runner.run_async`; (2) an `LlmAgent` driving a tool loop under a scripted `BaseLlm`
  (the offline model double that makes CI deterministic).
- **`a2a-sdk`** is load-bearing for the agent edge (canonical A2A). Pin it and track its release
  cadence / `[EXPERIMENTAL]` surfaces the same way. See `docs/decisions/adr-0001-stack.md`.
