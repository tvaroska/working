# Infrastructure as Code

This directory contains GCP-only IaC for the A2A Document Bridge. Local PC dev has no Terraform — the local adapters for the six seams (Sessions, Task store, Exchange store, Skill registry, Scheduler, Extraction) run without GCP resources.

## Directory Layout

```
infra/
  terraform/
    versions.tf            # Provider pins + backend config stub
    variables.tf           # Core vars (project_id, region)
    main.tf                # Root module (wires child modules in Sprint 2)
    outputs.tf             # Terraform outputs (Sprint 2)
    terraform.tfvars.example
    modules/               # Child modules (Sprint 2)
      network/
      runtime/
      gateway/
      services/
      iam/
      database/
      tasks/
      secrets/
      frontend/
    envs/                  # Per-environment config (Sprint 2)
      dev/
        backend.hcl
        dev.tfvars
      prod/
        backend.hcl
        prod.tfvars
```

## Local Commands

From the `infra/terraform/` directory:

```bash
cd infra/terraform
terraform fmt -check -recursive   # Format check (runs in CI)
terraform init -backend=false     # Initialize (stateless, no GCP credentials)
terraform validate                # Validate configuration
```

## Sprint Boundary

- **Sprint 0** (current): Skeleton + fmt/validate CI gate. No resources, no remote state, no `plan`/`apply`.
- **Sprint 2**: The 8 child modules, real GCP resources, full `terraform.tfvars.example` defaults (see `docs/lessons-learned.md §C4`), and the credential-free `*.tftest.hcl` (`mock_provider`) plan-time suite. Also includes the two-phase-apply gotcha handling (§C4).

## Notes

- **`.terraform.lock.hcl` is gitignored** — CI regenerates providers each run. Sprint 2 may reconsider committing it for provider reproducibility.
- **Credential-free validation**: The `*.tftest.hcl` suite (Sprint 2) using `mock_provider` is the only proof the config was coherent without applying to GCP.
- **Remote state backend** (GCS) is commented out in `versions.tf` until the tfstate bucket exists (Sprint 2).
