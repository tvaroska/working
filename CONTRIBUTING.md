# Contributing to A2A Document Bridge

Thank you for your interest in contributing. This document describes the development workflow, tooling, and conventions.

## Prerequisites

You will need the following tools installed:

- **Python 3.12+** — required for `agents/` and `bridge/` projects
- **uv 0.9+** — Python package manager ([install](https://docs.astral.sh/uv/))
- **Node.js 22+** — required for the frontend
- **pnpm 10+** — Node package manager ([install](https://pnpm.io/installation))
- **Terraform 1.15+** — for infrastructure as code ([install](https://www.terraform.io/downloads))
- **make** — task runner (usually pre-installed on Linux/macOS)
- **uvx** — bundled with uv, used for `pre-commit` and `agentskills`

## One-Command Setup

From the repository root, run:

```bash
make setup
```

This command will:
1. Install dependencies for `agents/` (uv sync)
2. Install dependencies for `bridge/` (uv sync)
3. Install dependencies for `frontend/` (pnpm install)
4. Enable pre-commit hooks (`uvx pre-commit install`)

After setup completes, verify everything works:

```bash
make test   # Run all test suites
make lint   # Lint/format-check everything
```

## Daily Development Loop

### Running All Projects

- **`make test`** — run all test suites (agents pytest + bridge pytest + frontend vitest)
- **`make lint`** — lint/format-check everything (mirrors CI exactly)
- **`make fmt`** — auto-format all code across the monorepo

### Per-Project Commands

When working on a single project, you can run commands directly:

**agents/** or **bridge/**:
```bash
cd agents  # or cd bridge
uv run pytest              # run tests
uv run ruff check .        # lint
uv run ruff format .       # format
```

If `uv` is unavailable, fall back to `.venv/bin/pytest` (requires manual venv activation).

**frontend/**:
```bash
cd frontend
pnpm test           # run vitest tests
pnpm lint           # eslint
pnpm format         # prettier (auto-fix)
pnpm format:check   # prettier (check-only)
```

**infra/terraform/**:
```bash
terraform -chdir=infra/terraform fmt -recursive         # format
terraform -chdir=infra/terraform fmt -check -recursive  # check-only
terraform -chdir=infra/terraform validate               # validate configs
```

**skills/**:
```bash
uvx --from skills-ref==0.1.1 agentskills validate skills/<skill-name>/
```

## Pre-Commit Hooks

Pre-commit hooks run automatically on `git commit` after you've run `make setup`. They perform:

- **Python** (agents/, bridge/): `ruff check --fix` + `ruff format` (auto-fixes)
- **Frontend**: prettier format check (reports issues, does not auto-fix)
- **Terraform**: `terraform fmt -check` (reports issues, does not auto-fix)
- **Skills**: `agentskills validate` on all skill folders
- **Hygiene**: trailing whitespace, end-of-file fixer, YAML check, merge conflict detection, large file check

**Important**: Frontend and Terraform hooks are **check-only**. If they fail, run `make fmt` to fix the formatting issues, then commit again. Python hooks auto-fix during the commit.

To manually run all hooks on all files:

```bash
uvx pre-commit run --all-files
```

## Environment Variables

The repository uses environment variables for configuration. See **[`.env.example`](.env.example)** at the repository root for a complete reference.

### Where .env Files Live

- **agents/**: The actual `.env` file must be placed at `agents/src/agents/address/.env` (not at the repo root or `agents/` root). The `adk web` dev server auto-loads environment variables from this location.
- **bridge/**: No `.env` needed yet (coming in Sprint 1).
- **frontend/**: No `.env` needed yet (coming in Sprint 1).

All `.env` files are **gitignored**. Only `.env.example` files are tracked in version control.

### Required Variables (agents/)

Copy `agents/src/agents/address/.env.example` to `agents/src/agents/address/.env` and set:

- `GOOGLE_GENAI_USE_VERTEXAI=TRUE`
- `GOOGLE_CLOUD_LOCATION=global`
- `GOOGLE_CLOUD_PROJECT=your-project-id` (replace with your actual GCP project ID)

Optional overrides are documented in the `.env.example` file.

## CI / Merge Gate

The repository uses GitHub Actions for continuous integration. The **required status check** is **`ci-success`**, which aggregates results from:

- `agents` — ruff lint + pytest
- `core` (bridge/) — ruff lint + pytest
- `skills` — agentskills validate
- `frontend` — eslint + vitest

CI is path-filtered: changes to `agents/` only run the agents job, changes to `frontend/` only run the frontend job, etc. Documentation-only PRs skip code jobs.

**Local green → CI green**: The `make lint` and `make test` commands mirror CI exactly. If both pass locally, CI should pass.

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for the full CI configuration.

## Project Structure

This is a **polyglot monorepo** with four sub-projects:

- **agents/** — Python (uv), address processing agent and mock Bridge server
- **bridge/** — Python (uv), reusable Bridge core (the showcase artifact)
- **frontend/** — TypeScript + React + Vite + MUI (pnpm)
- **infra/terraform/** — Terraform infrastructure as code
- **skills/** — Agent Skills format (validated with `skills-ref`)

Each sub-project has its own toolchain, lockfile, and test suite. The root `Makefile` aggregates commands across all projects.

## Code Quality Standards

- **Python**: Ruff enforces linting and formatting. Line length = 100 characters. Target Python 3.12.
- **TypeScript/JavaScript**: ESLint + Prettier enforce standards.
- **Terraform**: `terraform fmt` enforces formatting. Terraform 1.15+ required.
- **Skills**: Agent Skills format validated with `skills-ref==0.1.1`.

All code must pass `make lint` before merge. CI enforces this.

## Testing

All tests must pass before merge. Run the full suite with `make test`, or run per-project as shown above.

- **agents/**: pytest (~49 tests as of Sprint 0)
- **bridge/**: pytest (seam suite + core tests)
- **frontend/**: vitest + Playwright e2e

## Skills Validation

Agent Skills live in `skills/*/` folders. Each skill must have a `SKILL.md` manifest. Validate with:

```bash
uvx --from skills-ref==0.1.1 agentskills validate skills/<skill-name>/
```

This command is part of `make lint` and runs automatically in CI and pre-commit hooks.

## Questions or Issues?

- Review the [design documentation](wiki/bridge.md) for architectural context.
- Check [PLAN.md](PLAN.md) for the current development status and active tasks.
- Open an issue on GitHub for bugs or feature requests.

---

**Happy contributing!**
