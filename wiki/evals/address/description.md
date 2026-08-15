---
type: eval
related:
  - "[[bridge-address-demo]]"
  - "[[bridge-collect]]"
  - "[[bridge-disposition]]"
tags: [bridge, eval]
status: review
updated: 2026-08-15
---

# Eval — Address (proof of address)

> **This is an eval, not a skill.** It is the spec of *what correct looks like* for the Address use-case: the use-case description, the example input documents (images), and the **expected outputs** for each. The runtime config the Bridge loads lives separately in `skills/` (`address-proof`, `gov-id`, `utility-bill`) — skills are not evals.

## Use-case

Prove a person's address. The satisfaction rule (owned by the app, sense B) is **one government ID _or_ two utility bills from different companies**. A party submits documents over one or more turns; the Bridge classifies each against the candidate label space (`gov-id`, `utility-bill`), dispositions it (sense A — legible? right type? unexpired? confident?), maintains the classified ledger, and chases the delta until the app judges the set complete. See [[bridge-address-demo]] for the demo narrative and [[bridge-collect]] for the loop.

**No real PII.** All documents use the synthetic identity **Jordan Lee** and are marked `synthetic: true`.

## Example inputs + expected outputs

Each row is one eval case: an input document (`images/*.svg`) with fixed extraction signals → the expected disposition/gate. The machine-readable form is `expected.json`; the scripted arrival order is `timeline.json`.

| id (image) | doctype | issuer | signals | **expected outcome** | what it proves |
|---|---|---|---|---|---|
| `gov-id-clean` | gov-id | — | conf=0.96, legible, unflagged, expiry=2030 | **accepted (auto_approve)** | Clean ID satisfies address-proof alone (Path A instant) |
| `gov-id-expired` | gov-id | — | conf=0.93, legible, flagged=expiry, expiry=2019 | **pending (hitl_review)** | Flagged-field gate → human review |
| `bill-powerco-clean` | utility-bill | power-co | conf=0.97, legible, unflagged | **accepted (auto_approve)** | First PowerCo bill; same-issuer scenario |
| `bill-powerco-clean-2` | utility-bill | power-co | conf=0.95, legible, unflagged | **accepted (auto_approve)** | issuer_raw="Power Co." → canonicalization variant |
| `bill-aquautil-clean` | utility-bill | aqua-util | conf=0.96, legible, unflagged | **accepted (auto_approve)** | Pairs with PowerCo to satisfy 2-distinct-issuer |
| `bill-aquautil-clear` | utility-bill | aqua-util | conf=0.72, legible, unflagged | **pending (hitl_review)** | Mid-confidence gate (resubmitted after blurry) |
| `bill-aquautil-blurry` | utility-bill | aqua-util | conf=0.30, illegible | **rejected (resubmit)** | Quality gate + resubmission flow |
| `passport-unsupported` | passport | gov | outside label space | **rejected (unsupported)** | Label-space rejection |

**Key eval scenarios** (the golden runs, from `timeline.json`): Path-A instant accept (`gov-id-clean`); distinct-issuer accept (`bill-powerco-clean` + `bill-aquautil-clean`); same-issuer reject (two PowerCo → not two *distinct*); resubmission (`bill-aquautil-blurry` → `bill-aquautil-clear`); HITL (`gov-id-expired`); escalation (SLA breach on the virtual clock).

## Issuer canonicalization

Bills carry both `issuer_raw` (as extracted) and `issuer` (canonical). The eval asserts `issuer == canonicalize(issuer_raw)` via `bridge.classification.canonicalize_issuer`:
- `PowerCo` → `power-co` · `Power Co.` → `power-co` (suffix "co" kept; only Ltd/Inc/etc. dropped) · `AquaUtil` → `aqua-util`

## Files

- **`expected.json`** — the eval corpus: 8 records (party `jordan-lee`), each with input signals + `expected_disposition` + `expected_gate` + `artifact` (image path).
- **`timeline.json`** — scripted virtual-clock exchanges (Exchange 1: Path A instant; Exchange 2: Path B full ladder).
- **`images/*.svg`** — synthetic SVG placeholders (deterministic, no external refs, no PII; the blurry one visually conveys blur).

## Consumers (parity — tests enforce no-drift)

The eval doubles as the deterministic extraction table and the golden-run corpus. Loaded by `tests/address/_corpus.py` (`load_corpus()`, `build_extraction_table()`, `load_timeline()`). Parity anchors held by tests:
1. `bridge.extraction.fixture._DEFAULT_TABLE` — 5 shared ids; gate-driving signals match exactly.
2. `agents.address.portal_server.SAMPLES` — every `{"fixture": id}` resolves to a corpus doc.
3. `timeline.json` — every referenced id exists in `expected.json`.

`tests/address/test_corpus.py` enforces well-formedness, canonicalization parity, no-drift from `_DEFAULT_TABLE`/`SAMPLES`, category coverage, no-PII, and timeline validity.

## Related
- [[bridge-address-demo|Address demo]], [[bridge-collect|Collect]], [[bridge-disposition|disposition]], [[evals|evals index]]
