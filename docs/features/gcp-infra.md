# Feature — GCP Substrate & Terraform

**Status:** 🚧 Written + plan-tested, **not yet applied/deployed** (Release 1 base infra) → extended · **Spec:** `wiki/bridge-gcp-substrate.md`, `wiki/bridge-zones.md`, `wiki/bridge-seams.md`

The managed-GCP wiring and trust boundary *are* part of what's demonstrated. Seam parity, not local-then-port: the interface is designed once (local adapter in the phase's Sprint A), only the GCP-backed implementation and its Terraform land in Sprint B, re-running the same shared suite.

## Scope (Release 1 — heaviest Terraform sprint)
- **GCP adapters:** Agent Runtime, Sessions, Skill Registry, Cloud Tasks, managed relational store (task + exchange), Gemini extraction, authenticated A2A + Agent Identity.
- **Terraform:** runtime, VPC + two-zone network, Agent Gateway ingress + per-party scoping, Identity/IAM, Cloud Tasks, DB, Gemini access, secrets.
- Re-run the shared suite on GCP; trust-boundary check (a party can address only its own leg).

## Later releases
- R2: program-scale Gateway addressing, FX secret, multilingual Gemini; Terraform deltas ≈ small (the reusability proof).
- R3: Memory Bank, managed A2A task-store swap, Document AI processors, multi-tenancy, real outbound channels; hardening — VPC Service Controls, CMEK, Security Command Center, BigQuery observability + eval.

## Risk
Release-1 Sprint 2 carries all base infra. If too big, split base-infra into its own half-sprint. Later infra lightness is intentional evidence of reusability.

## Completed Work

> **Caveat:** all Terraform is validated at **plan time only** (`terraform test` + `mock_provider`); it has never been `apply`d against a real GCP project (no project provisioned — `docs/qa/phase1-checklist.md` GCP rows are `PENDING (human)`). The GCP seam adapters (S2-infra-1..3, in `bridge/seams/gcp/`) likewise pass their parity suite locally but are unproven against live services.

- **S2-infra-4 — Terraform base substrate** (Agent Runtime + two-zone VPC network + Agent Gateway
  ingress + per-party scoping). First Terraform in the repo: root module + three child modules
  (`network`, `runtime`, `gateway`) under `infra/terraform/`. The two subnets model the two **trust**
  zones with firewall rules isolating the internal zone; the runtime is a Cloud Run v2 service
  (egress routed through the VPC, ingress computed from `enable_gateway`); the gateway is a toggleable
  external HTTPS LB → Serverless NEG; per-party `roles/run.invoker` bindings (no `allUsers`) are the
  ingress half of the trust boundary and feed the S2-infra-3 identity seam via the `identity_audience`
  / `party_names` outputs. Credential-free plan-time tests (`terraform test` + `mock_provider`), a
  `terraform` CI job, and self-skipping `make tf-fmt/tf-validate/tf-test` targets. SA/IAM roles,
  Cloud Tasks, DB, Gemini, secrets, and the image build are deliberately left to S2-infra-5 / the
  deploy pipeline. Plan: `.claude/plans/S2-infra-4-terraform-runtime-network-gateway.md`.

- **S2-infra-5 — Terraform workload IAM, Cloud Tasks, DB, Gemini access, secrets.** Five new child
  modules under `infra/terraform/` wired into the S2-infra-4 skeleton: `services` (project API
  enablement, `disable_on_destroy = false`), `iam` (the `bridge-runtime` workload service account +
  `cloudsql.client` / `cloudtasks.enqueuer` / `aiplatform.user` grants + the Cloud Tasks service-agent
  `serviceAccountTokenCreator` for OIDC callback minting), `database` (Cloud SQL Postgres 16 on
  **private IP** via Private Services Access — reserved global address + service-networking connection,
  `ipv4_enabled = false` — plus the `bridge` db/user and a generated password), `tasks` (the
  `bridge-followups` Cloud Tasks queue), and `secrets` (Secret Manager secrets + per-secret accessor
  IAM). The `runtime` module gained a `secret_env` block and a Tasks-callback `run.invoker` binding
  (distinct from the per-party family). The root assembles the DB DSN, stores it as the `DATABASE_URL`
  **secret env** (never plaintext), seeds `BRIDGE_SEAM_MODE=gcp` + project/location + `BRIDGE_GCP_TASKS_*`
  + identity knobs, and exposes `runtime_service_account_email` / `db_connection_name` /
  `tasks_queue_path` / `db_url_secret_id` outputs. The Cloud Tasks target URL / identity audience are
  var-driven (two-phase apply) to avoid the runtime/gateway dependency cycle. "Gemini access" is API
  enablement (`aiplatform.googleapis.com`) + one IAM role — no standalone resource. Credential-free
  plan-time tests (`mock_provider`) cover the IAM role set, the Postgres-16 private-IP DB, the queue,
  the DB-DSN secret + accessor + secret count, the `DATABASE_URL` secret-env, and the Tasks-callback
  invoker. No `bridge/`/Python changes. Plan:
  `.claude/plans/S2-infra-5-terraform-iam-tasks-db-gemini-secrets.md`.

- **S2-front-1 — Deploy the three frontend surfaces to GCP** (provider-portal in the external zone,
  agent-console + ops-dashboard in the internal zone). New `modules/frontend` child module
  (`infra/terraform/`) provisions the three actor surfaces as Cloud Run v2 services, enforcing the
  zone-based trust boundary via ingress + invoker IAM: the **provider-portal** (external) has public
  ingress (`INGRESS_TRAFFIC_ALL` by default) + `allUsers` invoker (when `frontend_portal_public = true`,
  the default); the **agent-console** + **ops-dashboard** (internal) have internal ingress
  (`INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`) and **no `allUsers` invoker** (only operator principals
  from `frontend_operator_principals` get `roles/run.invoker`). The fourth surface (`timewarp` presenter
  control) is **not deployed** — the presenter runs it locally. Container artifact: a shared multi-stage
  `frontend/Dockerfile` (ARG SURFACE selects the workspace package) that builds the SPA with pnpm and
  serves `dist/` from nginx, **preserving the same-origin API proxy** (`/portal`, `/console`, `/ops` →
  `BACKEND_ORIGIN`) the dev Vite proxies already use (no CORS, no `agents/` backend code change). SSE-safe
  proxy headers for the agent-console + ops-dashboard streams. `VITE_*_BASE` stays empty at build time —
  the production container keeps the SPA and its API same-origin. Image refs + backend origins are
  Terraform input vars (`frontend_surfaces` / `frontend_backend_origins`, all with defaults — S2-infra-7's
  gotcha). Root outputs `frontend_service_uris` + `portal_url`. Plan-time `mock_provider` tests
  (`tests/frontend.tftest.hcl`) verify: three surfaces deployed (no timewarp), portal external ingress,
  internal surfaces internal ingress + absence of `allUsers`, the portal public-invoker toggle, and
  operator-principal bindings landing on internal surfaces only (the trust boundary S2-test-1 checks).
  Docs updated (`frontend/README.md` Production deploy section, `docs/features/gcp-infra.md`,
  `.env.example`). No `bridge/` or `agents/` changes; the existing `terraform` CI job + `tf-*` Makefile
  targets auto-pick-up the new files. Plan: `.claude/plans/S2-front-1-deploy-frontend-surfaces.md`.
