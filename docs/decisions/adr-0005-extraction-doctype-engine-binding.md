# ADR-0005 — Extraction-seam doctype→engine binding (Gemini schema/prompt vs Document AI processor+entity map; Gemini-only fallback)

- **Status:** Accepted
- **Date:** 2026-08-06
- **Resolves:** `PLAN.md` → S0-docs-1 (decision 4 of 4)
- **Context:** `wiki/bridge-open-questions.md` → Open decisions, `wiki/bridge-seams.md`, `wiki/bridge-skills.md`, `docs/architecture.md` §8

## Context

Extraction is behind one swappable seam with engine-selectable adapters: fixture (deterministic), **Gemini**, **Document AI** (`wiki/bridge-seams.md`). The engines bind to a doctype differently — "Gemini takes an arbitrary schema and prompt, Document AI needs a processor bound per doctype." The open question (`wiki/bridge-open-questions.md`) asks how a doctype declares its binding for each engine, and what the **capability envelope** is when no Document AI processor covers a doctype (Gemini-only fallback? auto-select the capable engine?).

The skills spec already sketches the binding: a doctype skill is `schema + prompt` for Gemini plus an **optional** `engine binding` for Document AI (`a processor plus an entity→field map`), and "a doctype no Document AI processor covers is simply Gemini-only (its capability envelope)" (`wiki/bridge-skills.md`).

## Decision

**A doctype skill declares its engine binding in `SKILL.md` frontmatter `metadata` plus bundled `assets/`, and the extraction seam resolves the active engine per doctype at fulfillment time.**

**Binding declared by the doctype skill:**

- **Gemini binding (always present):** the extraction prompt is the `SKILL.md` body; the constrained-JSON schema is `assets/schema.json`, referenced by `metadata.bridge-schema`. This is the baseline every doctype skill carries.
- **Document AI binding (optional):** `metadata.bridge-docai-processor` names the processor id (empty string = none), and an `assets/docai-entity-map.yaml` supplies the **entity→field map** aligning Document AI processor entities to the doctype's field names. Present only for doctypes a processor covers.
- `metadata.bridge-extraction-engine` states the doctype's **preferred** engine (default `gemini`).

**Resolution at fulfillment time** — the seam picks the engine by this order:

1. **Config seam mode** selects the operative engine set (fixture for local/tests; Gemini and/or Document AI when deployed). This is `config + per-doctype capability`, not local-vs-GCP (`wiki/bridge-seams.md`).
2. **Per-doctype capability** decides the concrete engine: if the operative mode selects **Document AI** *and* the doctype has a bound processor (`bridge-docai-processor` non-empty with an entity map) → use Document AI; **otherwise fall back to Gemini** (the doctype's Gemini binding is always present).
3. The **no-processor fallback is Gemini-only, never a hard failure.** A doctype with no Document AI processor is a fully supported doctype — Gemini is its capability envelope. The seam logs the fallback (for observability) and proceeds; it does **not** error and does **not** silently drop to fixture.

**Phase 1 scope:** only the **fixture** and **Gemini** adapters ship (`wiki/bridge-open-questions.md` minimal cut; `PLAN.md` S1-core-5, S2-infra-2). The Document AI binding fields (`bridge-docai-processor`, `assets/docai-entity-map.yaml`) are **defined in the doctype-skill contract now but inert** until the Document AI adapter lands (Phase 4). Phase-1 doctype skills carry only the Gemini binding.

## Rationale

- **The wiki already leans here.** `wiki/bridge-skills.md` states the Gemini binding is intrinsic, the Document AI binding is optional, and no-processor = Gemini-only capability envelope. This ADR records that lean and makes the resolution order explicit.
- **Gemini-first fallback over hard failure or auto-select-to-fixture** keeps extraction robust: every doctype always has a working engine (Gemini), so adding Document AI is a per-doctype *upgrade*, never a gate. This is "auto-select the capable engine" resolved conservatively — capable = Gemini unless a processor is explicitly bound.
- **Declaring the Document AI contract now, inert** means the Phase-4 adapter is a pure seam add with no doctype re-authoring — the one-adapter-swap proof (`wiki/bridge-seams.md`) stays literal.
- **Binding lives in the skill, engine-agnostic disposition downstream** (see ADR-0004) — the mediation around extraction never moves when the engine is swapped (`docs/architecture.md` §2.1).

## Consequences

- Phase-1 extraction seam (`PLAN.md` S1-core-5) implements the fixture + Gemini adapters and the resolution order, with the Document AI branch present but unreachable (no adapter, empty processor bindings).
- The doctype-skill contract gains two documented, optional keys/assets (`bridge-docai-processor`, `docai-entity-map.yaml`); `skills-ref validate` still governs folder structure, and a Bridge-side check validates the entity map only when a processor is declared.
- The Document AI adapter (Phase 4, `wiki/bridge-open-questions.md`) reads `bridge-docai-processor` + `docai-entity-map.yaml`; adding it requires no change to existing doctype skills that omit those fields.
- A per-doctype fallback log line is emitted when Document AI is the operative mode but a doctype lacks a processor — useful signal for coverage gaps.

## Alternatives considered

- **Hard-fail when the operative engine can't serve a doctype.** Simple rule, but breaks the "extraction always works" property and makes Document AI adoption an all-or-nothing migration. Rejected in favor of Gemini fallback.
- **Auto-select purely by capability with no per-doctype preference.** Loses the ability to state a doctype's preferred engine (e.g. a compliance doctype that should prefer Document AI). Kept a preference field; capability still overrides when the processor is absent. 
- **Model the binding outside the skill (central engine-map file).** Splits doctype config across two places and breaks "adding a doctype is a folder upload." Rejected — binding stays in the skill.
- **Ship the Document AI binding fields only when the adapter lands.** Would force re-authoring existing skills at Phase 4. Rejected — define the inert contract now.
