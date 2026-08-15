# Feature — GCP Substrate & Terraform

**Status:** 📋 Planned (0%) · **Release:** 1 (base infra) → extended each phase · **Spec:** `wiki/bridge-gcp-substrate.md`, `wiki/bridge-zones.md`, `wiki/bridge-seams.md`

The managed-GCP wiring and trust boundary *are* part of what's demonstrated. **GCP Agent Platform is the production environment; a local PC is the development environment** — every managed-service boundary is a seam with a local adapter and a GCP adapter. Seam parity, not local-then-port: the interface is designed once (local adapter in the phase's Sprint A), only the GCP-backed implementation and its Terraform land in Sprint B, re-running the same shared suite.

## Scope (Release 1 — heaviest Terraform sprint)
- **GCP seam adapters:** Agent Runtime, Sessions (Vertex/Agent Engine), Skill Registry (GCS), Cloud Tasks scheduler, managed relational store (Postgres task + exchange), Gemini extraction, authenticated A2A + Agent Identity.
- **Terraform:** runtime (Cloud Run v2), VPC + two-zone network, Agent Gateway ingress + per-party scoping, Identity/IAM, Cloud Tasks, Cloud SQL Postgres 16 (private IP), Gemini access, Secret Manager.
- **Frontend deploy:** provider-portal (external zone, public ingress) + agent-console/ops-dashboard (internal zone, no `allUsers`, operator-principal invoker only); timewarp is not deployed.
- Re-run the shared suite on GCP; trust-boundary check (a party can address only its own leg).

## Intended layout
Terraform under `infra/terraform/` as a root module + child modules: `network` (two subnets modelling the two trust zones + firewall isolation), `runtime` (Cloud Run v2, egress via VPC, ingress computed from `enable_gateway`, secret-env block), `gateway` (toggleable external HTTPS LB → Serverless NEG), `services` (project API enablement), `iam` (the `bridge-runtime` workload SA + `cloudsql.client` / `cloudtasks.enqueuer` / `aiplatform.user` grants + the Cloud Tasks token-creator for OIDC callbacks), `database` (Cloud SQL Postgres 16 on private IP via Private Services Access), `tasks` (the `bridge-followups` queue), `secrets` (Secret Manager + per-secret accessor IAM; the DB DSN is a `DATABASE_URL` secret env, never plaintext), and `frontend` (the three deployed surfaces). Concrete default values (CIDRs, tiers, queue settings, the two-phase-apply gotcha) are in `docs/lessons-learned.md §C4`.

Validation is credential-free plan-time tests (`terraform test` + `mock_provider`); the deployed-path parity run (`BRIDGE_TEST_GCP=1`) is Sprint-B, against a provisioned project with ADC + reachable Cloud SQL.

## Later releases
- R2: program-scale Gateway addressing, FX secret, multilingual Gemini; Terraform deltas ≈ small (the reusability proof).
- R3: Memory Bank, managed A2A task-store swap, Document AI processors, multi-tenancy, real outbound channels; hardening — VPC Service Controls, CMEK, Security Command Center, BigQuery observability + eval.

## Risk
Release-1 Sprint 2 carries all base infra. If too big, split base-infra into its own half-sprint. Later infra lightness is intentional evidence of reusability.
