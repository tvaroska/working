# Feature — Frontend (Three Surfaces)

**Status:** ✅ Built (Release 1 — all three surfaces + time-warp) · **Release:** 1 → extended each phase · **Spec:** `wiki/bridge-frontend.md`, `wiki/bridge-a2ui-edge.md`, `wiki/bridge-zones.md`

Three surfaces, one per actor, make the mediation legible on stage and validate A2UI early. They are A2UI hosts (content-not-pixels) and their split across the trust boundary demonstrates the two-zone model.

## Surfaces
1. **Processing-Agent Console** (internal) — ledger handed, reasoning, satisfaction check, requirements list + timeline. Where sense B is watchable.
2. **Servicer Ops Dashboard** (internal) — exchanges in flight, classified ledger filling live, disposition outcomes, HITL/escalation queues.
3. **End-user / Provider Portal** (external) — A2UI Path-B: upload, disposition, outstanding items. The only surface across the boundary.

## Presentation modes
- Split-Screen Theater (default) — portal (external) ↔ console + dashboard (internal), Gateway boundary drawn between.
- Timeline — the exchange as a scrubbable event stream.
- Architecture X-Ray (Release 3) — live traffic overlaid on the component/seam diagram.

## Time-warp (Release 1)
Presenter control over the virtual clock: fast-forward an SLA window so `overdue → escalated` fires on cue; step / pause / replay.

## Evolution
- R1 Address: all three surfaces + time-warp; ledger fill, sense-B reject, HITL/escalation
- R2 Benefits: console negotiate/bind controls; dashboard program comparison view; portal multi-format quotes
- R2 RFP: console shows Requirements mutated live; dashboard casefile view + wrong-doc flags
- R3 Maturity: Architecture X-Ray overlay; outbound/party-channel views

## Completed Work

- **S1-front-1** Processing-Agent Console (`frontend/agent-console/`).
- **S1-front-2** Servicer Ops Dashboard (`frontend/ops-dashboard/`).
- **S1-front-3** Provider Portal — A2UI Path-B (`frontend/provider-portal/`).
- **S1-front-4** Time-warp presenter control over the virtual clock (`frontend/timewarp/`).
- **S2-front-1** Terraform to deploy portal (external zone) + console/dashboard (internal zone); timewarp runs locally.

**Known gaps** (see `docs/tech-debt.md`): only provider-portal has automated tests (Playwright e2e, backend stubbed at the network boundary); the other three surfaces and `console_server.py` have none. Shared UI/domain code (`theme.ts`, `Panel.tsx`, `Badges.tsx`, `domain/contract.ts`) is copy-pasted across the four apps and drifting — no shared package yet.
