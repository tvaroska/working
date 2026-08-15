---
type: atom
related:
  - "[[bridge-demo-suite]]"
  - "[[bridge-collect]]"
  - "[[bridge-skills]]"
  - "[[bridge-disposition]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# RFP Demo — scenario & build checklist

> The Phase-3 **breadth headline**: a *different industry* running the **emergent** [[bridge-collect|Collect]] — agent-mutated Requirements, conditional items, N suppliers — added **live** to the running core with **no redeploy**. It generalizes the pattern [[bridge-address-demo|Address]] introduced bounded; it does not invent it. The single clearest proof of the reusability thesis: one deployed core, a whole new use-case uploaded as configuration while other exchanges are in flight.

## What's different from Address

**Same [[bridge-collect|multi-turn loop]], smarter reply.** RFP is the *identical* Bridge machinery as [[bridge-address-demo|Address]] — collect → parse → report ledger → agent returns a requirements list → chase → repeat. The only difference is the agent's per-turn reply: Address runs a fixed policy; RFP runs an emergent, mutating one. **No new pattern, no code change** — Collect is a built-in flow, and there is no DSL.

Address was a *bounded* Collect: a fixed satisfaction rule over a **classified ledger**, no persisted agent artifact. RFP is the **emergent** form, and it earns the two versioned artifacts:

| Artifact | Owner | Source of truth for |
|---|---|---|
| **Requirements** | processing agent | *what's needed* and *is it done* — mutated at runtime |
| **Collection status** | Bridge | *what we have* — per-item state, rejections, outstanding |

Here **slots legitimately appear** — they are agent-owned Requirement *items* in the Requirements artifact, not a Bridge invention (contrast [[bridge-address-demo|Address's ledger]]).

## Scenario — procurement casefile

A procurement team's agent runs an **RFP** to onboard a new supplier, *Nimbus Logistics* (synthetic). The agent posts an initial **Requirements** set — proposal, pricing sheet, insurance certificate, W-9 — and the Bridge chases, classifies, and reports. The requirement list **grows as facts emerge**.

| Beat | What happens | Proves |
|---|---|---|
| 0 · Live-add | With Address + Benefits exchanges already running, upload the **RFP doctype + process skills** to the core. The [[bridge-a2a-edge|Agent Card]] regenerates; the [[bridge-a2ui-edge|dashboard]] gains RFP exchanges — **no redeploy, no interruption.** | **the reusability headline** · one core speaks a new industry live |
| 1 · Post Requirements | Agent posts the initial Requirements; Bridge opens the casefile and begins chasing outstanding items. | agent-owned Requirements · Bridge-owned Collection status |
| 2 · Messy intake | Nimbus submits a bundle: proposal + pricing, one **unlabeled** scan, and the insurance cert is **the wrong document**. Bridge **classifies** each against the candidate doctypes, matches an open item, normalizes, dispositions per item, flags the wrong/unrequested one. | **open-set classification** · per-item disposition · Collection status live |
| 3 · Emergent requirement | The proposal reveals Nimbus is an **international** supplier → the agent **adds** a tax-residency form to Requirements ("self-employed → tax return" style conditional — the *agent* adds an item, not a Bridge trigger). Bridge chases the delta. | **agent-mutated Requirements** · conditional logic stays sense B |
| 4 · Complete | Nimbus supplies the missing cert and the new form; agent evaluates → waives one nice-to-have, asserts **done** → finalize. | agent judges completeness of a *set* (sense B) and decides done · the Bridge best-efforts an advisory assessment and chases the delta |

## What we need to make it work

**Skills:**
- **Process skill `rfp`** — pattern `Collect (emergent)`, policy, candidate doctypes (the label space for classification). **Pattern now lives in the skill**, not code (see below).
- **Doctype skills** — `rfp-proposal`, `pricing-sheet`, `insurance-cert`, `w9`, `tax-residency`, … each schema + prompt + validation, reusable across processes.

**Phase-3 capabilities (the breadth build):**
- **The Collect graph** — post Requirements → chase → classify → normalize → disposition per item → update Collection status → agent evaluates → loop on the delta ([[bridge-collect|Collect]]).
- **Two versioned artifacts** — agent-owned Requirements (mutable at runtime) + Bridge-owned Collection status.
- **Open-set classification** — route unlabeled docs to a candidate item, or flag wrong/unrequested.
- **No pattern work.** Collect is a **built-in flow** ([[bridge-patterns|closed pattern set]]); RFP selects it via `pattern` and adds skills. There is no workflow DSL and nothing to "lift into the skill" — "adding a demo is configuration" holds because the flow already exists and the emergent behavior lives in the agent's per-turn reply.
- **Showcase runner** — boots one core with all demos loaded and exercises Address + Benefits + RFP concurrently — the proof of multi-use-case coexistence.

**Core machinery (from Phases 1–2):** both edges, dual-path, extraction seam, disposition, HITL, proactive, seams, network zones, programs.

**Demo data:** **synthetic** supplier bundle — proposal, pricing sheet, a wrong "insurance cert," an unlabeled scan, plus the later tax-residency form. Doubles as fixtures + test corpus.

**Tests:** golden runs for live-add (card regenerates, existing exchanges untouched), messy intake (classification + wrong-doc flag), an emergent-requirement round, and completeness assertion — against fixture and Gemini adapters.

## Open decisions
- **Requirements-list schema** — settle the small fixed shape the agent returns each turn (item, `status: required|optional|satisfied|waived`, doctype hint, note). Data, not a language (see [[bridge-collect|Collect]]).
- ⚠ RFP is **last-built and most cuttable** yet bears the headline — protect it from cut, or pull a minimal live-add proof forward (the Phase-2 doctype-add down-payment). See [[bridge-demo-suite|demo implementations]].

## Related
- [[bridge-demo-suite|demo implementations]], [[bridge-collect|Collect]], [[bridge-skills|skills]], [[bridge-disposition|disposition]]
