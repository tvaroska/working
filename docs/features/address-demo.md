# Feature — Address Demo (+ Live Doctype-Add)

**Status:** 📋 Planned (0%) · **Release:** 1 · **Spec:** `wiki/bridge-address-demo.md`, `wiki/bridge-demo-suite.md`

The Phase-1 warm-up and objection-handler: a servicer's agent needs proof of address and asks once. Satisfied by **one government ID or two bills from different companies** — a bounded Collect with agent-owned completeness and no typed slots.

## Scenario (KYC onboarding, party: Jordan Lee, synthetic)
- **Exchange 1 — Path A (fast, ~30s):** structured gov-ID assertion on the A2A edge → validate-only → satisfied on first document.
- **Exchange 2 — Path B (the meaty case):** two-bills branch via the A2UI portal — classify, issuer-canonicalize, disposition; agent rejects a same-issuer set (sense B); silence triggers proactive chase → escalate; blurry bill → resubmission → HITL; two distinct issuers → done → one clean normalized artifact delivered.

## Live doctype-add (exec-audience beat, Release 1 / Sprint 2)
Down-payment on the Release-2 reusability headline, at small scale on one deployed core:
- **Run 1 (simple):** core knows only `utility-bill`.
- **Live moment (config-only, platform win):** upload the `gov-id` doctype skill to the running core → Agent Card regenerates → new capability, no redeploy.
- **Run 2 (full):** structured gov-ID on Path A → instant satisfaction; a fulfillment path that didn't exist in Run 1.
- **Honesty rule:** label-space change is config (platform); satisfaction count-rule change is the agent's (sense B) — narrate them separately, never as one "skill update."

## Skills (config — Agent Skills format, one `SKILL.md` folder each; see `wiki/bridge-skills.md`)
- Process `address-proof` — pattern `Collect (bounded)`, candidate doctypes `[gov-id, utility-bill]`, policy (SLA, max nudges, retry cap, thresholds) in `assets/policy.yaml`; **no** satisfaction rule.
- Doctype `gov-id`, doctype `utility-bill` (issuer canonicalized to a stable key) — schema in `assets/schema.json`, extraction prompt in the `SKILL.md` body.

## Build components
- Synthetic document corpus (driver license, same-issuer + distinct-issuer bills, expired ID, blurry bill) + scripted timeline — the eval spec lives in `wiki/evals/address/`.
- Shared golden-run suite — Path A instant, distinct-issuer accept, same-issuer reject, resubmission, HITL, escalation; runs against the fixture adapter first, then the real Bridge.
- Two-run demo script — Run 1 (utility-bill only) → live add `gov-id` → Run 2 (gov-id Path-A instant), with the config-vs-sense-B honesty split narrated separately.
- Skills to author: process `address-proof`, doctypes `gov-id` / `utility-bill` (concrete values in `docs/lessons-learned.md §C1`).

Sprint A proves the demo on the local path; Sprint B runs the deployed-GCP walkthrough after the Terraform apply (see `docs/features/gcp-infra.md`).
