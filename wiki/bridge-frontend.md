---
type: concept
up:
  - "[[bridge-implementation-plan]]"
related:
  - "[[bridge-a2ui-edge]]"
  - "[[bridge-zones]]"
  - "[[bridge-demo-suite]]"
tags: [bridge]
status: review
updated: 2026-08-06
---

# Frontend

> The process is invisible unless you can *see* it. Three surfaces — one per actor — make the mediation legible on stage and validate the [[bridge-a2ui-edge|A2UI]] protocol early. They are **A2UI hosts** (the Bridge/agent send *content*, the surface renders pixels — content-not-pixels), and their split across the trust boundary itself demonstrates the [[bridge-zones|two-zone model]]. Built in **Sprint 1**, extended each phase.

## The three surfaces (one per actor)

### 1. Processing-Agent Console — *internal*
The counterparty agent's mind, made visible. Per turn it shows: the **ledger it was handed**, its **reasoning**, the **satisfaction check**, and the **requirements list it returns** (`required | optional | satisfied | waived`) with `done`. This is where **sense B** is watchable — the audience sees the *agent* (not the Bridge) reject the two-same-issuer set and ask for one more. A folded-in **Timeline** shows the turn-by-turn negotiation.

### 2. Servicer Ops Dashboard — *internal*
The read-model. Exchanges in flight, each exchange's **classified ledger** filling live, disposition outcomes, and the **HITL** and **escalation** queues (approve/reject, reviewer resolves the mid-confidence bill). The operator's window into a running Bridge.

### 3. End-user / Provider Portal — *external*
The human counterparty's [[bridge-a2ui-edge|A2UI Path-B]] surface: upload a document, see its disposition and what's still outstanding. Lives in the **external zone** — the only surface across the boundary, which is the point.

## Presentation modes

- **Split-Screen Theater** (default) — provider portal (left, external) ↔ agent console + ops dashboard (right, internal), the Gateway boundary drawn between them. One story, both zones, the seam visible.
- **Timeline** — the exchange as an event stream (request → arrivals → chase → escalate → deliver); scrub it.
- **Architecture X-Ray** (Phase 4) — overlay the live traffic on the component/seam diagram; watch calls light up the extraction seam, scheduler, Gateway.

## Time-warp (Sprint 1)

A presenter control over the [[bridge-proactive|virtual clock]]: **fast-forward** an SLA window so `overdue → escalated` fires on cue, **step / pause** through beats, **replay** a run. Turns the demo's slowest, most important proof (proactive follow-up) into a few seconds of stage time.

## Evolution by phase

| Phase | Surface additions |
|---|---|
| 1 — Address | all three surfaces + time-warp; ledger fill, sense-B reject, HITL/escalation |
| 2 — Benefits | console gains **negotiate/bind** controls; dashboard gains the **program comparison view**; portal takes multi-format quotes |
| 3 — RFP | console shows the **Requirements list being mutated** live; dashboard gains the **casefile view** + wrong-doc flags |
| 4 — Maturity | **Architecture X-Ray** overlay; outbound/party-channel views |

## Related
- [[bridge-implementation-plan|implementation plan]], [[bridge-a2ui-edge|A2UI edge]], [[bridge-zones|network zones]], [[bridge-demo-suite|demos]]
