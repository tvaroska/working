# ADR-0011 — Contract-type sharing strategy (shared package)

- **Status:** Accepted
- **Date:** 2026-08-15
- **Ratified:** 2026-08-15 (S0.8 sign-off gate)
- **Scope:** How contract types (`CollectRequest`, `ExchangeTurn`, `CollectionStatus`, `LedgerEntry`, etc.) are shared between the `agents/` and `bridge/` projects while preserving the invariant that `bridge/` never imports `agents/`.
- **Ratified at:** S0.8 (sign-off gate; physical move deferred until after sign-off)
- **Context:** `CLAUDE.md` (invariant: `bridge/` never imports `agents/`; "Core vs. demos" — `bridge/` is a reusable showcase artifact, agents are consumers); `PLAN.md` S0.2, S0.8; `wiki/bridge-aggregate-model.md`; `docs/decisions/adr-0001-stack.md`

## Context

The A2A Document Bridge architecture separates the **reusable Bridge core** (`bridge/`) from the **processing agents** that consume it (`agents/`). The core invariant (CLAUDE.md): **`bridge/` never imports `agents/`**. Parity between them (canonicalization, disposition logic) holds *by discipline*, enforced by the shared seam suite that tests both mock and real implementations — not by import.

The two projects are **physically separate uv projects** (each has its own `pyproject.toml`, `uv.lock`, `.venv`). Because `bridge/` does not depend on `agents`, the `agents` package is not even installed in `bridge/`'s environment, so `import agents` would fail regardless.

However, both projects need to share the **domain contract types** — the Pydantic models that define the A2A payload carried inside `Message`/`Part`/`Artifact` (`CollectRequest`, `ExchangeTurn`, `CollectionStatus`, `RequirementsList`, `LedgerEntry`, extraction field schemas). These types are the **wire contract under validation** (Milestone 0) and must stay synchronized: the Bridge emits them, agents consume them. Divergence here breaks interoperability.

Currently (as of M0), the contract types live in `agents/src/contract/`. This placement worked for the tracer bullet (agents-only), but Sprint 0 scaffolds `bridge/` as a separate project — which cannot import from `agents`. **The open decision:** how should contract types be shared between the two projects while preserving the invariant?

## Decision

Adopt a **shared third package `contract`** that both `agents/` and `bridge/` depend on as a uv path dependency. Neither project imports the other; both import the shared third package. This preserves the invariant that `bridge/` never imports `agents/` (a shared *third* package is explicitly allowed by CLAUDE.md).

### Package structure

- A new **`contract/` project** (or `packages/contract/`) at the repository root, with its own `pyproject.toml` (minimal: name `a2a-document-bridge-contract`, version `0.0.0`, Python `>=3.12`, dependencies `pydantic>=2` only — no ADK or a2a-sdk, to keep it lightweight and minimize cross-project lock churn).
- `contract/src/contract/` contains the domain models (relocated from `agents/src/contract/` with no code changes).
- Both `agents/pyproject.toml` and `bridge/pyproject.toml` add:
  ```toml
  dependencies = [
      "a2a-document-bridge-contract",
      ...
  ]

  [tool.uv.sources]
  a2a-document-bridge-contract = { path = "../contract", editable = true }
  ```
- `agents/pyproject.toml` drops `src/contract` from its `[tool.hatch.build.targets.wheel].packages` list.
- Both projects re-lock (`uv sync` from each root) to pick up the path dependency.
- Import name stays `contract` in both projects (`import contract`, `from contract import CollectRequest` — no call-site churn).

### Timing

This ADR was authored with **Status: Proposed** during S0.2 (bridge scaffold) and **ratified at S0.8**. The physical restructure (creating `contract/`, moving the code, updating `pyproject.toml`s, re-locking) remains a **follow-up task now that S0.8 has ratified this ADR**. The contract extraction is a separate post-sign-off task; S0.8 only ratifies the decision.

## Rationale

- **Preserves the invariant.** `bridge/` imports `contract`, not `agents`; `agents` imports `contract`, not `bridge`. The invariant "`bridge/` never imports `agents/`" remains true. A shared third package is explicitly allowed (CLAUDE.md: "parity between them holds *by discipline* + the shared seam suite, not by import").
- **Zero call-site churn.** Import name is `contract` in both projects, identical to the current `agents/src/contract/` layout. No code changes at call sites, only `pyproject.toml` updates.
- **Simpler than duplicate-by-discipline.** Keeping two separate copies of the contract models (one in `agents/`, one in `bridge/`) invites drift on the load-bearing wire types. The shared seam suite can detect drift, but preventing it is better than detecting it. A shared package makes "one contract, two consumers" structurally obvious.
- **Standard uv path-dependency pattern.** `tool.uv.sources` with `{ path = "...", editable = true }` is the documented uv mechanism for local multi-package repos. The editable install means changes to `contract/` are immediately visible in both projects without re-install.
- **Lightweight package.** Contract models depend only on `pydantic`, not on heavy SDKs (ADK, a2a-sdk, google-cloud-*), so changes to `contract/` rarely force re-locks of `agents/` or `bridge/`. The contract types are Pydantic models plus helpers — genuinely reusable pieces, not coupled to one project's environment.

## Consequences

- **Three uv projects** (agents, bridge, contract) instead of two. Each has its own `pyproject.toml`, `uv.lock`. Contract changes trigger re-lock in both consumers, but the lightweight dependency list minimizes churn.
- **No cross-project import allowed.** The shared third package is the *only* permitted sharing mechanism between `agents/` and `bridge/`. Any logic that needs to be shared must either (a) live in `contract/` if it is domain-payload-related and has no heavy dependencies, or (b) be duplicated-by-discipline and kept in parity by the shared seam suite. The test `bridge/tests/test_no_agents_import.py` locks the isolation guard in CI.
- **Parity discipline stays unchanged.** Canonicalization, disposition, `is_satisfied` logic (heavy, ADK-coupled) remain duplicated between `bridge/` and `agents/` and converge via the shared seam suite, not by import. `contract/` is only for the **data models** that cross the wire.
- **Contract changes are tracked.** Because `contract/` is a separate project with its own lockfile, bumping a contract version (if ever needed) is a deliberate dependency change in both consumers, visible in the lock diff.

## Alternatives considered

### Alternative 1: Duplicate-by-discipline (each project has its own copy)

Keep two separate `contract` packages: `agents/src/contract/` and `bridge/src/contract/`, maintained in parity by the shared seam suite (which would fail if the wire types diverge).

**Rejected as the target because:**
- Invites drift on the load-bearing wire types. The shared suite can *detect* divergence, but preventing it is better.
- Higher discipline cost — any contract change requires manual synchronization across two codebases.
- Loses the structural signal that "the contract is a shared artifact."

**Noted as the fallback:** if the shared-package approach proves too heavyweight (e.g., cross-project lock churn becomes a friction point), this alternative is the escape hatch. The seam suite already enforces terminal-outcome parity; extending it to enforce contract-model parity is feasible.

### Alternative 2: `agents/` depends on `bridge/` (or vice versa)

One project imports the other to share the contract types.

**Rejected:** violates the invariant "`bridge/` never imports `agents/`" (and its symmetric: agents shouldn't depend on the core they consume). The reusability claim is that "`bridge/` is the showcase artifact; agents are consumers." A consumer depending on the producer is backward.

### Alternative 3: Publish `contract` as a real PyPI package

Create `a2a-document-bridge-contract` as a separately-versioned, published package that both `agents/` and `bridge/` depend on as a normal pip/uv dependency.

**Rejected for now:** adds release/versioning ceremony for what is currently an internal wire contract under active development. The path-dependency approach gives the same import isolation without the publishing overhead. Revisit if the contract stabilizes and external agents need to depend on it.

## Sign-off gate

This ADR was authored with **Status: Proposed** during S0.2 (bridge scaffold), ratified at **S0.8** (stack + open-decision validation gate). The physical move of `contract/` out of `agents/src/` remains a follow-up task.

Mechanics for the follow-up (post-S0.8 ratification):
1. Create `contract/pyproject.toml` (minimal: pydantic-only, no heavy deps).
2. Move `agents/src/contract/` to `contract/src/contract/` (code unchanged).
3. Update `agents/pyproject.toml` and `bridge/pyproject.toml`: add `a2a-document-bridge-contract` to dependencies, add `[tool.uv.sources]` path dependency, drop `src/contract` from `agents/`'s wheel-packages list.
4. Re-lock both (`uv sync` from `agents/` and `bridge/`).
5. Verify `import contract` works in both projects and `test_scaffold.py` passes.
6. Update any docs that reference `agents/src/contract/` to point to `contract/`.
