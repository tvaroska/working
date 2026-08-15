---
type: concept
down:
  - "[[bridge-frontend]]"
related:
  - "[[bridge-stages]]"
  - "[[bridge-seams]]"
  - "[[bridge-open-questions]]"
tags: [bridge]
status: review
updated: 2026-08-06
---

# Implementation Plan

> The build sequence for the [[bridge-stages|four phases]]: **4 phases × 2 sprints = 8 sprints.** Each phase is **agent-first** — its processing agent is built before the Bridge code for that phase. Each phase's **Sprint A** proves behavior **locally** (local seam adapters, virtual clock, fixture extractor); **Sprint B** adds the **GCP adapters + Terraform**, deploys, and runs **manual tests** on the real platform.

## Three cross-cutting rules

1. **Agent-first.** Every phase starts by building its [[bridge-collect|processing agent]] — the counterparty that owns the per-turn decisions (sense B). The agent defines the A2A contract (what it sends and expects each turn), so building it first nails the multi-turn negotiation before the Bridge is committed. This works because *the difference between demos is the agent, not the Bridge*.
2. **Mock Document Bridge (Sprint 1).** Before the real Bridge exists, a simulated Bridge speaks the A2A multi-turn contract — accepts the requirements list, injects fixture document arrivals, reports a ledger, fakes chase/timeout. The agent's negotiation is developed and tested against it. It then **persists as the contract double / test harness** for every later phase, so agent regressions are caught without standing up the platform.
3. **Seam parity, not local-then-port.** Sprint A defines each seam **interface**, builds the **local adapter**, and writes the **shared test suite**; Sprint B builds the **GCP adapter** and re-runs *that same suite* against it ([[bridge-seams|seams]]). The interface is designed once; only the GCP-backed implementation and its Terraform land in B.

## Frontend across the plan

Three surfaces (the three actors), built in Sprint 1 and extended each phase — see [[bridge-frontend]]. They compose into the split-screen presentation view and themselves illustrate the [[bridge-zones|two-zone model]]. A presenter **time-warp** control (virtual clock) ships in Sprint 1.

---

## Phase 1 — Address

**Sprint 1 — Local (agent-first)**
1. **Address processing agent** — runs the multi-turn loop; owns the satisfaction policy (`ID or 2 distinct bills`); emits the requirements list each turn.
2. **Mock Document Bridge** — the A2A contract + fixture document arrivals; the harness the agent negotiates against (persists as the contract double).
3. **Frontend v1** — [[bridge-frontend|three surfaces]] (agent console, ops dashboard, provider portal) + time-warp control.
4. **Real Bridge (local)** — aggregate model, both edges, dual-path, extraction graph (fixture), disposition + classification + issuer canonicalization, classified ledger, proactive (virtual clock), seam **local adapters**. Swap mock→real behind the same contract; shared suite green.
- **Exit:** Address runs end-to-end locally and is visible in the frontend; the agent is unchanged when the mock is swapped for the real Bridge.

**Sprint 2 — GCP + Terraform**
- **GCP adapters:** Agent Runtime, Sessions, Skill Registry, Cloud Tasks, managed relational store (task + exchange), **Gemini** extraction, authenticated A2A + Agent Identity. Frontend deployed.
- **Terraform:** runtime, VPC + two-zone network, Agent Gateway ingress + per-party scoping, Identity/IAM, Cloud Tasks, DB, Gemini access, secrets.
- **Live doctype-add (down-payment on the Phase-3 headline).** Pull forward a *minimal* slice of the Sprint-6 live-add: run Address twice on the one deployed core with a skill uploaded **between runs, no redeploy** — see [[bridge-address-demo|the two-run live-add scenario]]. This lands the **Agent-Card regeneration** mechanism early (the [[bridge-a2a-edge|card]] is generated from installed skills). Two distinct beats, honestly separated:
  - **Config-only (the platform proof):** upload the `gov-id` **doctype skill** to the running core → card regenerates to advertise gov-ID → Run 2 gains the instant Path-A gov-ID fulfillment path that did not exist in Run 1. No agent change, no redeploy.
  - **Agent policy (labeled as the servicer's change, not the platform's):** the satisfaction tightens (e.g. `>=1 bill` → `gov-id OR 2 distinct bills`). This is [[bridge-address-demo|sense B]] — the **completeness decision** is the agent's, **not** a config/redeploy win — and must be narrated as such. (Per ADR-0006 the tightening can also surface as the skill's **prose satisfaction description**, never a formal rule, which the Bridge best-efforts an advisory assessment from; the decision still sits with the agent.)
- Re-run shared suite on GCP; **manual test pass** + trust-boundary check (a party can address only its own leg).
- **Exit:** Address on the deployed GCP path, visible in the deployed frontend; both runs + the live doctype-add demonstrated; manual checklist signed. *(Heaviest Terraform sprint — all base infra. If too big, split base-infra into its own half-sprint.)*
- **⚠ Scope risk.** The card-regeneration / live-add mechanism is otherwise scheduled for **Sprint 6** (Phase 3). Pulling a minimal version into Sprint 2 is a deliberate scope add, justified by the exec-audience demo; keep it *minimal* (one doctype-add, sequential runs) — the full concurrent showcase runner stays in Phase 3.

## Phase 2 — Benefits

**Sprint 3 — Local (agent-first)**
1. **Benefits processing agent** — the negotiate policy: fan-out, read the comparison, drive the revise loop, decide the bind (sense B). Developed against the mock Bridge (extended: N legs + revised-quote arrivals).
2. **Frontend v2** — agent console gains negotiate/bind controls; ops dashboard gains the **program comparison view**; portal handles multi-format quote upload.
3. **Real Bridge delta (local)** — programs (isolated legs), Negotiate flow + versioned revise loop, multilingual + FX normalization, declared-rule standard-gap, bind → rollup → audit.
- **Exit:** "one comparable view" arc runs locally, visible in the comparison frontend.

**Sprint 4 — GCP + Terraform**
- GCP: program-scale Gateway addressing, deployed comparison UI, FX secret, Gemini multilingual on real docs; Terraform delta; re-run suite.
- **Manual test:** 4 carriers, 3 currencies/languages, a live negotiate round, bind → rollup. Plus **one live doctype-add** (Phase-3 down-payment).
- **Exit:** Benefits deployed + manual sign-off.

## Phase 3 — RFP

**Sprint 5 — Local (agent-first)**
1. **RFP processing agent** — the emergent policy: posts and **mutates** Requirements per turn, handles conditionals, asserts done. Against the mock Bridge (extended: messy/unlabeled/wrong-doc arrivals).
2. **Frontend v3** — agent console shows **Requirements being mutated**; ops dashboard shows the **casefile view** + wrong-doc flags; portal handles the messy bundle.
3. **Real Bridge delta (local)** — emergent Collect, open-set classification, wrong/unrequested flagging; **showcase runner** (all demos, concurrent).
- **Exit:** RFP + Address + Benefits run concurrently on one local core, one dashboard.

**Sprint 6 — GCP + Terraform**
- GCP: **live skill-add** to the running deployed core (Agent Card regenerates, no redeploy); showcase runner on GCP; Terraform delta ≈ none — *the reusability proof: new industry = skills, not infra.*
- **Manual test:** add RFP live while Address/Benefits exchanges are in flight; one card + one dashboard serve all three.
- **Exit:** the reusability headline, on the deployed platform.

## Phase 4 — Maturity & hardening (core-only)

**Sprint 7 — Local**
- *(Lighter on new agent work — hardening, not a new demo.)* Where an agent-facing surface changes (Bridge-as-client + outbound, dual-path B→A migration), extend an existing agent + the mock's outbound simulation first.
- Four-signal [[bridge-disposition|disposition]] + wrong-doc detection; [[bridge-party-memory|party memory]] consumers; cold-inbound Extract edge; **Document AI adapter** (extraction-seam swap parity); **frontend v4** — the [[bridge-frontend|Architecture X-Ray]].
- **Exit:** hardening features proven locally, incl. Gemini↔Document AI parity and B→A migration preserving history.

**Sprint 8 — GCP + Terraform**
- GCP: Memory Bank, managed A2A task-store swap, Document AI processors, per-customer multi-tenancy, real outbound channels.
- **Terraform:** VPC Service Controls, CMEK, Security Command Center, BigQuery observability + eval, multi-tenant deploy.
- **Manual test:** security posture, tenancy isolation, engine swap on GCP, observability dashboards.
- **Exit:** production-grade hardened deployment.

---

## Risks

- **Phase 1 is front-loaded.** Sprint 2 carries all base infra; Sprints 4/6 are deliberately light on infra — that lightness *is* the reusability proof.
- **Sprints 5–6 (RFP) are the most cuttable yet bear the headline.** If schedule slips, protect the **live-add** beat (Sprint 6) even if emergent-Collect depth (Sprint 5) is trimmed. See [[bridge-demo-suite|demo implementations]].
- **The mock Bridge is a maintained artifact, not throwaway** — it's the permanent agent-side test double.

## Related
- [[bridge-stages|build phases]], [[bridge-frontend|frontend]], [[bridge-seams|seams]], [[bridge-open-questions|scope]]
