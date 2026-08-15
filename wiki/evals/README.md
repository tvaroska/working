---
type: eval-index
related:
  - "[[bridge-demo-suite]]"
tags: [bridge, eval]
status: review
updated: 2026-08-15
---

# Evals

> **Evals are spec, not runtime config.** Each eval captures, per use-case, the **use-case description**, the **example inputs** (documents / images), and the **expected outputs** (disposition + gate per input). They define *what correct looks like* and are the source of truth for the golden-run suite.
>
> **Evals ≠ skills.** Skills (`skills/`) are the Agent Skills folders the Bridge loads at runtime (doctype extraction specs, process policy). Evals (`wiki/evals/`) are the test/spec corpus that grades behaviour. Keep them separate: a skill is *how the Bridge behaves*; an eval is *how we check it behaved correctly*.

## Layout

```
wiki/evals/<use-case>/
  description.md   — use-case description + example inputs + expected-outputs table (a wiki atom)
  expected.json    — machine-readable eval corpus: inputs + expected disposition/gate
  timeline.json    — scripted arrival order (where a use-case has a virtual-clock scenario)
  images/          — example input documents (synthetic, no PII)
```

## Use-cases

| Use-case | Status | Eval |
|---|---|---|
| **Address** (proof of address) | built (Phase 1) | [[address/description\|address]] — 8 documents, full expected outputs, golden scenarios |
| **Benefits** | aspirational (Phase 2) | [[benefits/description\|benefits]] — scaffold (structure only, no corpus yet) |
| **RFP** | aspirational (Phase 3) | [[rfp/description\|rfp]] — scaffold (structure only, no corpus yet) |

Only **Address** is built and has a real corpus + expected outputs. Benefits and RFP are scaffolds: the structure exists so their evals can be authored when the demos are built. See [[bridge-demo-suite]] for the demo arc.
