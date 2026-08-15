---
type: atom
related:
  - "[[bridge-edges]]"
  - "[[bridge-fulfillment-graph]]"
  - "[[bridge-disposition]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# Dual-Path Fulfillment

> When a servicer requests a doc from party X, X responds — **indistinguishably to the requester** — in one of two modes, decided only by **what kind of response arrives**.

| Mode | Party | What arrives | Bridge does |
|---|---|---|---|
| **Path A — structured** | has an agent | a structured data response on the A2A edge (carrying the exchange context token) | **validate-only** — schema validation + [[bridge-disposition\|disposition]], **no extraction call** |
| **Path B — portal** | no agent | PDF / free-text / form via the A2UI portal | **extract / normalize** → disposition → HITL if flagged (the [[bridge-fulfillment-graph\|extraction graph]]) |
| **Operator-fulfilled** | internal human | upload on X's behalf | as Path B; lower priority |

**Party-first, inbound.** Both modes are the party *responding* to an already-open exchange — the Bridge minted the context at request time. That is why Phase 1 needs **no A2A client and no outbound**.

**The migration payoff.** When a Path-B party later builds its own A2A agent, it flips to Path A by **config only** — history preserved, and the servicer's code never changes. Both modes appear in the **Address warm-up demo** (e.g. a party agent returns a structured ID assertion on Path A; a human uploads an ID photo or two bill PDFs on Path B); the full Path B → Path A migration lands at Phase 4.

This is the concrete meaning of "uniform internal interface regardless of party maturity": the messy variety lives at the edge, and everything past intake is one normalized artifact stream.

## Related
- [[bridge-edges|two edges]], [[bridge-fulfillment-graph|extraction graph]], [[bridge-disposition|disposition]]
