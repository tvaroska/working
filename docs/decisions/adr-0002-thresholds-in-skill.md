# ADR-0002 — Thresholds live in the process-skill policy, not in code constants

- **Status:** Accepted
- **Date:** 2026-08-06
- **Resolves:** `PLAN.md` → S0-docs-1 (decision 1 of 4)
- **Context:** `wiki/bridge-open-questions.md` → Open decisions, `wiki/bridge-skills.md`, `wiki/bridge-disposition.md`, `wiki/bridge-fulfillment-graph.md`

## Context

The Phase-1 disposition gates use three tunable numbers: the **resubmit threshold** (below it, request a resubmission), the **auto-approve threshold** (at/above it with no flags, auto-approve; else HITL), and the **retry cap** (max resubmission attempts, currently 3). Today these are effectively constants in the fulfillment graph. The question (`wiki/bridge-open-questions.md`): lift them into the skill, or keep them as code defaults with skill overrides?

The skills spec already resolves the direction. A process skill carries `assets/policy.yaml` for "reminders, SLA, retries, escalation, thresholds" (`wiki/bridge-skills.md`), and that note states plainly: "**policy** already lives in the skill (`assets/policy.yaml`)." SLA/proactive policy is already read from the process-skill policy (`wiki/bridge-proactive.md`). Thresholds are the same class of tunable and belong in the same place.

## Decision

**Disposition thresholds are policy, and policy lives in the process skill.** The resubmit threshold, auto-approve threshold, and retry cap are read from the active process skill's `assets/policy.yaml` (e.g. `address-proof/assets/policy.yaml`), the same file that already carries SLA cadence, max nudges, and escalation.

The Bridge ships **built-in defaults** in code, used **only** when the skill omits a given key. The resolution order per value is: **skill policy value → built-in default**. The skill is authoritative; defaults exist so a skill need not declare every knob and so the gates always resolve.

Concretely for Phase 1 `address-proof/assets/policy.yaml`:

```yaml
thresholds:
  resubmit_below: 0.55      # quality gate: below → request resubmission
  auto_approve_at: 0.85     # confidence gate: at/above + no flags → auto-approve
retry:
  max_resubmissions: 3      # capped resubmission loop
```

Values are loaded and validated through a Pydantic policy model at skill install/activation; missing keys fall back to the coded defaults. No per-doctype threshold override in Phase 1 (thresholds are an exchange-level policy concern; the doctype skill owns validation rules and signals, not gate cut-offs).

## Rationale

- **The wiki already leans here.** `wiki/bridge-skills.md` states policy already lives in `assets/policy.yaml`; thresholds are policy. This makes the decision a documentation of intent, not a new commitment.
- **One authoritative source, single mental model.** SLA and thresholds are both "how this process should behave" — keeping them in one `policy.yaml` avoids a split where cadence is configurable but gates are hard-coded.
- **Config-only tuning fits the thesis.** A new industry / process is new skills, not new code (`docs/architecture.md` §2.3). Tunable gates in the skill keep behavior change on the config side of that line.
- **Defaults keep it minimal and safe.** Coded defaults mean the gates never fail to resolve and a minimal skill stays terse — the change is additive and low-risk.

## Consequences

- The Phase-1 policy model must define, load, and validate the `thresholds` and `retry` blocks; the fulfillment graph reads resolved values, never literals.
- `skills-ref validate` continues to gate skill folders; policy-schema validation is a Bridge-side concern layered on top (the Agent Skills spec does not constrain `assets/policy.yaml` contents).
- Coded defaults must be documented alongside the model so an author knows what they inherit by omission.

## Alternatives considered

- **Keep thresholds as pure code constants.** Simplest, but contradicts `wiki/bridge-skills.md` (policy already in the skill) and forces a redeploy to tune a demo — against the config-only ethos. Rejected.
- **Thresholds in the skill with no coded defaults (skill must declare all).** More explicit, but makes minimal skills verbose and risks an unresolved gate if a key is forgotten. Rejected in favor of defaults-with-override.
- **Per-doctype threshold overrides.** More flexibility, unneeded for Phase 1 and adds a second precedence layer. Deferred; reversible (add a doctype-level override that wins over process policy if a case ever demands it).
