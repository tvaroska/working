.DEFAULT_GOAL := help
.PHONY: help setup test lint fmt

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup:  ## One-command dev setup: install all deps + enable pre-commit
	cd agents && uv sync
	cd bridge && uv sync
	cd frontend && pnpm install
	uvx pre-commit install
	@echo "Setup complete. Run 'make test' and 'make lint'."

test:  ## Run all test suites (agents, bridge, frontend)
	cd agents && uv run pytest
	cd bridge && uv run pytest
	cd frontend && pnpm test

lint:  ## Lint/format-check everything (mirrors CI)
	cd agents && uv run ruff check .
	cd bridge && uv run ruff check .
	cd frontend && pnpm lint
	terraform -chdir=infra/terraform fmt -check -recursive
	for d in skills/*/; do [ -f "$${d}SKILL.md" ] || continue; uvx --from skills-ref==0.1.1 agentskills validate "$$d" || exit 1; done

fmt:  ## Auto-format everything
	cd agents && uv run ruff format . && uv run ruff check --fix .
	cd bridge && uv run ruff format . && uv run ruff check --fix .
	cd frontend && pnpm format
	terraform -chdir=infra/terraform fmt -recursive
