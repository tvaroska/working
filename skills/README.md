# Skills

This directory contains runtime **Agent Skills** configuration (agentskills.io format), not evaluation fixtures. Each skill is a folder with a `SKILL.md` manifest (YAML frontmatter + Markdown body) and optional `assets/` and `references/`.

**Two kinds** (via `metadata.bridge-kind`):
- **process** — parameterizes an exchange (e.g., `address-proof` defines the Collect over candidate doctypes)
- **doctype** — parameterizes an extraction task (e.g., `gov-id`, `utility-bill` define schemas and validation rules)

## Local validation

Validate one skill:
```bash
uvx --from skills-ref==0.1.1 agentskills validate skills/address-proof
```

Validate all skills:
```bash
for d in skills/*/; do uvx --from skills-ref==0.1.1 agentskills validate "$d" || break; done
```

**Note:** This validation is gated in CI (`.github/workflows/ci.yml`). These commands will be consolidated into the root dev-env documentation and pre-commit hooks in task S0.7.
