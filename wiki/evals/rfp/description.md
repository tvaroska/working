---
type: eval
related:
  - "[[bridge-rfp-demo]]"
tags: [bridge, eval, scaffold]
status: draft
updated: 2026-08-15
---

# Eval — RFP *(scaffold — not yet authored)*

> **Scaffold only.** RFP is the Phase-3 (aspirational, headline) demo; its eval corpus and expected outputs are **not yet authored**. This page fixes the structure so the eval can be filled in when the demo is built. **Evals are not skills** — runtime config will live in `skills/` when authored.

## Use-case *(to be written)*

Emergent Collect at scale in a different industry — requirements that mutate on learned facts, conditional items, N suppliers, added *live* with no redeploy. Same multi-turn loop as Address, with a smarter per-turn reply. See [[bridge-rfp-demo]] for the design narrative.

## Example inputs + expected outputs *(to be authored)*

_No corpus yet._ When authored, each case = an input document/response (`images/…`) with fixed signals → expected disposition/gate, plus expected requirements-list mutation per turn (the emergent-Collect dimension). Mirror the [[address/description|Address eval]] shape; populate `expected.json` and this table together.

| id (image) | doctype | signals | **expected outcome** | what it proves |
|---|---|---|---|---|
| _tbd_ | _tbd_ | _tbd_ | _tbd_ | _tbd_ |

## Files

- **`expected.json`** — placeholder (`documents: []`); fill with the eval corpus.
- **`images/`** — empty; add synthetic, no-PII example documents.

## Related
- [[bridge-rfp-demo|RFP demo]], [[evals|evals index]]
