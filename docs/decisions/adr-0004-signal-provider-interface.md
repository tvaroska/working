# ADR-0004 — Signal-provider interface shape (fixed four-signal contract, one Phase-1 implementation)

- **Status:** Accepted — **amended by `docs/decisions/adr-0006-adk-native-runtime.md`** (2026-08-14): the four-signal contract, the `SignalProvider` interface, **and the app's ownership of the completeness *decision* all stand**. The one change: the Bridge is no longer completeness-*blind*. Its `LlmAgent` now makes a **best-effort** completeness assessment by interpreting the skill's natural-language satisfaction rule over the ledger (proposing what's outstanding, chasing) — but this is advisory, with no deterministic rule and no enforcement; the app still decides. See ADR-0006 → "Completeness."
- **Date:** 2026-08-06
- **Resolves:** `PLAN.md` → S0-docs-1 (decision 3 of 4)
- **Context:** `wiki/bridge-open-questions.md` → Open decisions, `wiki/bridge-disposition.md`, `wiki/bridge-seams.md`, `wiki/bridge-skills.md`

## Context

Disposition (sense A) routes a submission by reading **signals**. The target is a **four-signal model** — legibility, type match, extraction confidence (+ fields requiring review), completeness (+ failed rules) — because one confidence scalar can't separate *unreadable* from *readable-but-wrong* from *readable-right-but-expired* (`wiki/bridge-disposition.md`). The full model, a pluggable signal provider (mock / model-reported / computed), and wrong-doc detection are **deferred post-golden**.

The open question (`wiki/bridge-open-questions.md`) asks to **settle the interface before it's needed** — so extraction adapters, disposition, and skills bind to a stable shape now, and later providers slot in without moving the mediation around them. This ADR fixes the *shape*, not the *implementations*.

## Decision

**Define the four-signal contract now as a fixed Pydantic model, and read it through a single `SignalProvider` interface.** Extraction adapters and disposition are written against this contract in Phase 1; only one provider implementation ships.

**The signal contract** — a fixed-schema value object with all four signals, each independently optional/nullable so a provider may populate a subset:

```
DispositionSignals:
  legibility:   Signal | None   # can we read it?            → resubmission
  type_match:   Signal | None   # right kind?                → reject / clarify
  confidence:   Signal | None   # read correctly?            → HITL vs auto-approve
                 + fields_needing_review: [field]
  completeness: Signal | None   # complete + rule-valid?     → request-more / reject
                 + failed_rules: [rule]

Signal:
  value:  float | enum          # score or categorical
  source: "extracted" | "reported" | "computed" | "mock"
  detail: str | None
```

**The provider interface** — `SignalProvider.signals(document, doctype_skill, extraction_result) -> DispositionSignals`. Disposition consumes `DispositionSignals` **engine-agnostically and provider-agnostically** — it never reads an engine's raw output. This matches the seam contract: "the extraction service returns normalized fields plus per-field and overall confidence, legibility, and flagged fields; disposition reads those signals engine-agnostically" (`wiki/bridge-seams.md`).

**Phase 1 ships exactly one provider — the extraction-derived provider.** It populates `legibility` and `confidence` (with `fields_needing_review`) from the extraction seam output, and `type_match` from Phase-1 doctype classification against the candidate label space. The per-artifact `completeness` **signal** is **left unpopulated by the SignalProvider in Phase 1**; disposition treats absent signals as "not evaluated," not "failed." (Note, per ADR-0006: *set*-completeness — "is the casefile done?" — is a separate concern from this per-doc signal. The **app still decides** it, but the Bridge's `LlmAgent` now makes a **best-effort** assessment by interpreting the skill's prose satisfaction rule over the ledger — advisory, not enforced, not via the SignalProvider. The earlier framing that set-completeness is *"the agent's, never the Bridge"* is refined to *"the app decides; the Bridge best-efforts."*) The gate logic uses `legibility` (resubmit gate) and `confidence` (auto-approve/HITL gate) exactly as ADR-0002's thresholds specify.

**Deferred (post-golden):** additional provider implementations (model-reported, computed, mock beyond tests) and wrong-doc detection. They implement the *same* `SignalProvider` interface and produce the *same* `DispositionSignals` — no interface change, which is the point of settling the shape now.

## Rationale

- **Settle the shape, defer the mechanism.** The wiki asks to fix the interface before it is needed; fixing the value object and one method now lets disposition and extraction adapters bind to a stable contract while deferring the extra providers.
- **Engine- and provider-agnostic disposition** is already the seam requirement (`wiki/bridge-seams.md`); a fixed `DispositionSignals` is the concrete realization.
- **Optional-per-signal** lets Phase 1 populate a subset (the "confidence-only special case" plus early type-match) without a separate Phase-1 shape that would later break — the four-signal target is the shape from day one.
- **Completeness signal excluded on purpose** keeps the sense-A/sense-B boundary crisp: the SignalProvider never fills a set-completeness signal. (Set-completeness itself is decided by the app; per ADR-0006 the Bridge additionally best-efforts an assessment of it, but that is the LlmAgent's reasoning over the ledger, not a provider signal.)

## Consequences

- Phase-1 disposition (`PLAN.md` S1-core-6) codes against `DispositionSignals` + `SignalProvider`, with the extraction-derived provider as the sole implementation and a mock/fixture provider for tests.
- The extraction seam output must carry per-field + overall confidence, legibility, and flagged fields so the provider can map them (already required by `wiki/bridge-seams.md`).
- Adding model-reported / computed providers later is additive: a new class implementing `SignalProvider`, selected by config — no change to disposition or the contract.
- `source` on each `Signal` records provenance (extracted vs reported vs computed vs mock), which future eval/observability can read.

## Alternatives considered

- **Pass raw extraction output to disposition; no signal abstraction yet.** Least code now, but couples disposition to engine shape and forces a rewrite when the four-signal model lands — contradicts "settle the interface before it's needed." Rejected.
- **Ship a confidence-only interface now, widen later.** Would break the contract when the other three signals arrive; the wiki explicitly wants the shape settled up front. Rejected.
- **Build all provider implementations now (mock/model/computed).** Scope beyond the minimal cut; the demo needs one provider. Deferred per `wiki/bridge-disposition.md`.
