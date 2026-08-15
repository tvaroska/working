---
type: atom
related:
  - "[[bridge-demo-suite]]"
  - "[[bridge-patterns]]"
  - "[[bridge-a2a-edge]]"
  - "[[bridge-a2ui-edge]]"
  - "[[bridge-disposition]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# Benefits Demo — scenario & build checklist

> The Phase-2 **depth** demo: a broker's agent gathers group-benefits quotes from **N carriers** and needs **one comparable view** to decide on. This is the [[bridge-patterns|Negotiate]] pattern over a **program** — fan-out → normalize → compare/standard-gap → negotiate → bind → rollup. The payoff is the moment N messy, multi-currency, multi-language quotes render as one apples-to-apples table with the gaps flagged.

## Scenario — group benefits procurement

A benefits broker's agent must source a group health plan for client *Acme Corp* (synthetic) from **four carriers** in different regions. It opens one **program** and fans out one leg per carrier — `request benefits-quote for program:acme-2026, party:carrier-{a,b,c,d}`. Each leg is its **own [[bridge-aggregate-model|context + party]]**; competitors never share a context ([[bridge-a2a-edge|isolation by per-leg addressing]]). The agent asks once per carrier and waits for a single normalized comparison.

| Beat | What happens | Proves |
|---|---|---|
| 1 · Fan-out | Agent opens `program:acme-2026`, requests a quote on four isolated legs. | program context linking N legs · per-leg party isolation |
| 2 · Mixed responses | **Two carriers answer via their own agents (Path A):** Carrier A's agent is built with **Google ADK**, Carrier B's with **LangGraph** — both respond over A2A (USD). Carriers C, D upload PDFs (Path B) in **EUR / French** and **GBP / German**. | [[bridge-dual-path|dual-path]] at fan-out scale · **A2A framework interoperability** (ADK ↔ LangGraph ↔ the Bridge) · heterogeneous inputs |
| 3 · Normalize | Multilingual extraction + **FX normalization** map every quote to one schema, one currency, one language. | the normalization that makes comparison possible |
| 4 · Compare + standard-gap | The [[bridge-a2ui-edge|program comparison view]] renders four legs side by side; each is flagged against the **program standard** via pack-declared rules (e.g. "deductible ≤ X", "must cover Y") — [[bridge-disposition|sense A]]. Carrier B's quote shows a coverage gap. | **the golden payoff** · declared-rule standard-gap (Bridge surfaces, never decides the deal) |
| 5 · Negotiate | Agent pushes back on Carrier B's gap over A2A; **B's LangGraph agent** returns a **revised quote** → a new artifact **version** on the same leg; the comparison updates live. | Negotiate pattern · versioned revise loop · **multi-turn A2A with a non-ADK counterparty** |
| 6 · Bind + rollup | Agent binds the winning leg (**sense B — the deal is the agent's**); the Bridge records per-leg bind → **program rollup** → audit trail. | bind → rollup → audit · the mediator never decides acceptance |

## What we need to make it work

**Skills:**
- **Process skill `benefits-quote`** — pattern `Negotiate`, policy (SLA, nudges, revise-loop cap), candidate doctypes `[benefits-quote]`, and the **program standard** rules the comparison flags against (declared, agent-overridable).
- **Doctype skill `benefits-quote`** — schema (premium, deductible, coverage limits, exclusions, currency, language, effective dates), prompt, validation.

**Phase-2 capabilities (the depth build):**
- **Programs** — a provider-facing program context that links N legs and carries the rollup; per-leg isolation enforced by addressing ([[bridge-a2a-edge|Programs]]).
- **Multilingual extraction + FX normalization** — the [[bridge-fulfillment-graph|extraction graph]]'s aspirational layer: translate + convert to one schema/currency/language.
- **Declared-rule standard-gap disposition** — flag each normalized quote against the program standard (sense A); routes to negotiation.
- **Negotiate + versioned revise loop** — artifact versioning on the same leg; the comparison recomputes as versions land.
- **Program comparison A2UI view** — N legs side by side, one currency and schema, gaps flagged.
- **Bind → program rollup → audit** — per-leg bind, program-level rollup, an audit trail.

**Simulated provider agents (new in Phase 2 — the interoperability proof):**
- **Framework-diverse counterparties.** The Path-A carriers are stood up as **real A2A agents in the external zone**, each its own A2A client + agent logic responding to the Bridge's [[bridge-a2a-edge|A2A edge]]. Deliberately built in **two different frameworks** — Carrier A in **Google ADK**, Carrier B in **LangGraph** — to prove A2A is framework-agnostic: the ADK-built Bridge negotiates, multi-turn, with a **non-ADK** counterparty and never notices the difference. This is the platform-evaluator headline for depth: *interoperability, not just fan-out.*
- **The LangGraph carrier drives the negotiate loop** (beat 5): it holds the coverage gap, receives the pushback over A2A, and returns a revised quote — so the interop proof covers the **multi-turn revise loop**, not a one-shot response. Both simulated agents are demo furniture (like the A2UI reference renderer), not part of the Bridge core.

**Core machinery (from Phase 1):** both edges, dual-path, extraction seam (fixture + Gemini), disposition gates, HITL, proactive follow-up, seams, network zones.

**Demo data:** **synthetic** quote documents — four carriers, three currencies (USD/EUR/GBP), three languages (English/French/German); the **LangGraph** carrier (B) carries both the deliberate coverage gap and the revise round. Two Path-A structured quotes (A, B), two Path-B PDFs (C, D). Doubles as extraction fixtures + test corpus. An **FX rate source** (fixed rates for a deterministic run).

**Tests:** golden runs per branch (structured vs PDF intake, each language/currency, standard-gap flag, revise loop, bind + rollup) against fixture and Gemini adapters, **plus a cross-framework interop test**: the same A2A conversation must pass whether the counterparty agent is the ADK or the LangGraph build.

## Open decisions
- **FX rate source** — fixed table (deterministic demo) vs a live seam; settle before Phase 2.
- Where the **program standard** rules live — inline in the process skill vs a separate declared-standard artifact the agent can swap per client.

## Related
- [[bridge-demo-suite|demo implementations]], [[bridge-patterns|patterns]], [[bridge-a2a-edge|A2A edge / Programs]], [[bridge-a2ui-edge|A2UI edge / comparison]], [[bridge-disposition|disposition]]
