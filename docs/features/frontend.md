# Feature — Frontend (Three Surfaces)

**Status:** 📋 Planned (0%) · **Release:** 1 → extended each phase · **Spec:** `wiki/bridge-frontend.md`, `wiki/bridge-a2ui-edge.md`, `wiki/bridge-zones.md`

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

## Build components (Release 1)
- Processing-Agent Console (`frontend/agent-console/`, internal zone, SSE).
- Servicer Ops Dashboard (`frontend/ops-dashboard/`, internal zone, SSE).
- Provider Portal — A2UI Path-B (`frontend/provider-portal/`, external zone).
- Time-warp presenter control over the virtual clock (`frontend/timewarp/`, plain REST, runs locally — not deployed).
- Terraform to deploy portal (external zone) + console/dashboard (internal zone).

**Watch-items for the build:** each surface hand-maps the snake_case wire to camelCase in its own `domain/` layer — factor shared UI/domain code (`theme.ts`, `Panel.tsx`, `Badges.tsx`, `domain/contract.ts`) into a shared package rather than copy-pasting across the four apps. Playwright e2e stubs the backend at the network boundary; add a component-unit layer and a `console_server` test rather than relying on browser e2e alone. SSE/Playwright and time-warp specifics are in `docs/lessons-learned.md §B`.
