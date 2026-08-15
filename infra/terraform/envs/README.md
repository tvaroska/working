# Per-Environment Configuration

Each environment directory (e.g., `dev/`, `prod/`) holds:

- `backend.hcl` — Partial backend config for `terraform init -backend-config=envs/<env>/backend.hcl`
- `<env>.tfvars` — Environment-specific variables for `terraform plan/apply -var-file=envs/<env>/<env>.tfvars`

Populated in Sprint 2.
