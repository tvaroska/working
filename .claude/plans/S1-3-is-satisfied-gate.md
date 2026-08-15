# S1-3 — `is_satisfied` completeness gate (deterministic sense-B tool)

## Context

PLAN.md Sprint-1 bullet **S1-3**. This adds the Address demo's **completeness ("done")
decision** as a **deterministic pure function over the classified ledger**, exposed to the
address `LlmAgent` as an **authoritative tool**. It is the code half of the repo's central
safety invariant: **LLM routes, code decides** — *a model may never mint "complete"*
(CLAUDE.md; `docs/lessons-learned.md` A3). S1-4 wires it into the multi-turn Collect loop;
S1-3 delivers the pure function + the tool + the unit tests only.

The rule is fixed for Address (`wiki/bridge-address-demo.md` "The satisfaction function"):

```
satisfied(ledger) =
     any(d.doctype == "gov-id"      and d.accepted)
  or count(distinct d.issuer for d in ledger
           where d.doctype == "utility-bill" and d.accepted) >= 2
```

This is **sense B** (completeness of the *set*) and lives on the **agent** side, distinct
from the Bridge's per-document disposition (sense A). "The difference between demos is the
agent, not the Bridge" — so this code belongs under the address agent package, never in
`bridge_client/` (the transport) and never in a (not-yet-existing) `bridge/`.

## Verified facts (read from the codebase — do not re-derive)

- **`Disposition`** is a `StrEnum` with `ACCEPTED = "accepted"`, `PENDING = "pending"`,
  `REJECTED = "rejected"` (`agents/src/contract/models.py`). "Accepted" in the rule ==
  `entry.disposition == Disposition.ACCEPTED`. HITL/pending and resubmit/rejected do **not**
  count toward completeness.
- **`LedgerEntry.issuer` is already the canonical issuer key** (contract docstring: "canonical
  issuer"; produced by the Bridge, sense A). For `gov-id` it is `None`. So the "distinct-issuer
  via issuer canonicalization" requirement is satisfied by comparing `entry.issuer` values as-is
  — **do not re-canonicalize in the gate** (see Decision 3).
- **`CollectionStatus`** (`contract`) holds `ledger: list[LedgerEntry]`, `outstanding: list[str]`,
  `terminal: bool`. `ExchangeTurn` wraps `context_id + status`. All Pydantic, `extra="forbid"`.
- **Eval fixtures** (`wiki/evals/address/expected.json`) — the raw entries carry extra keys
  (`issuer_raw`, `expected_disposition`, `expected_gate`, `artifact`, `synthetic`, `note`) that
  fail `LedgerEntry`'s `extra="forbid"`, so a `LedgerEntry` **must be built explicitly**, mapping
  `expected_disposition → disposition` and `extraction` via `Extraction.model_validate(...)`. The
  existing pattern is in `agents/src/agents/mock_bridge/fixtures.py::load_gov_id_clean_entry` and
  `agents/tests/test_contract.py::test_ledger_entry_from_eval_entry_explicit_mapping` — mirror it.
  Fixture facts that pin the tests:
  - `gov-id-clean` → `gov-id`, issuer `null`, disposition `accepted` → gov-id branch true.
  - `gov-id-expired` → `gov-id`, disposition `pending` → does NOT satisfy.
  - `bill-powerco-clean` (`issuer_raw:"PowerCo"`) and `bill-powerco-clean-2`
    (`issuer_raw:"Power Co."`) both have canonical `issuer:"power-co"`, disposition `accepted` →
    **one** distinct issuer (this is the A4 "'co' is not a suffix" canonicalization equivalence).
  - `bill-aquautil-clean` → `aqua-util`, `accepted`.
  - `bill-aquautil-clear` → `aqua-util`, `pending` (HITL) → not accepted.
  - `bill-aquautil-blurry` → `aqua-util`, `rejected` → not accepted.
  - `passport-unsupported` → `passport`, `rejected` → not a utility-bill, not accepted.
- **`agents/src/agents/address/render.py`** already exists and its docstring says it is
  "retained for the Sprint-1 `is_satisfied` gate" — `collection_to_dict(turn)` and
  `_entry_summary` are available if useful, but the gate does not need them.
- **ADK tool mechanics** (`google-adk` 2.7.0): a plain function passed in `LlmAgent(tools=[...])`
  is auto-wrapped as a `FunctionTool`; its params become the tool schema. A parameter named
  `tool_context: ToolContext` is **injected by ADK**, not surfaced to the model — this is how a
  tool reads authoritative session state without the model supplying (or fabricating) it.
- **Import rule (CLAUDE.md):** the new module lives in `agents/` and may import `contract` +
  `google-adk` + stdlib. It must **not** import `bridge_client.*` and there is no `bridge/`.

## Design decisions (resolve these once, here)

1. **Home = `agents/src/agents/address/satisfaction.py`.** Sense-B, address-specific, agent-owned.
   Not `bridge_client/` (transport), not `contract/` (shared shapes). Export the tool from the
   address package as needed by S1-4.
2. **Authoritative tool reads the ledger from session state, never from model args.** The pure
   function takes typed data; the tool wrapper takes only `tool_context` and reads the latest
   collection status from `tool_context.state`. If the model could pass the ledger, it could mint
   completeness — forbidden. This is the load-bearing "code decides" guarantee.
3. **The gate trusts the ledger's canonical `issuer`; it does NOT re-canonicalize.** Per-document
   issuer canonicalization is sense A (the Bridge). The agent compares the already-canonical keys.
   Re-canonicalizing here would (a) duplicate sense-A logic on the agent side, (b) require the gate
   to own a canonicalizer the Bridge owns, violating the sense split. Distinctness = size of the
   set of `entry.issuer` over accepted utility-bills. **Rejected alternative:** defensive
   re-canonicalization in the gate — documented and declined.
4. **Bills with a `None`/empty issuer do not count toward the distinct set.** A utility-bill whose
   issuer could not be extracted cannot be proven distinct, so it is excluded from the count
   (defensive; fixtures always carry an issuer, but the real Bridge might not).
5. **`outstanding` is doctype-level guidance, `list[str]`.** When not done, both alternatives
   remain open, so `outstanding = ["gov-id", "utility-bill"]` (sorted, deduped). The "one more from
   a *different* company" nuance is the agent's prose reasoning (sense B) layered on top in S1-4 —
   the deterministic gate reports doctypes only. When done, `outstanding = []`. Matches the
   `contract.CollectionStatus.outstanding: list[str]` shape and the candidate-doctype label space
   (`gov-id`, `utility-bill`).

## Deliverable 1 — pure gate + result model

`agents/src/agents/address/satisfaction.py` (new)

```python
"""Deterministic Address completeness gate (sense B) — the code that decides "done".

LLM routes, code decides: this is the authoritative satisfaction function the model
may call but never override (docs/lessons-learned.md A3). Address rule: proof of
address is satisfied by one accepted gov-id OR two accepted utility-bills from
distinct (already-canonical) issuers.
"""
from pydantic import BaseModel, ConfigDict, Field
from contract import CollectionStatus, Disposition, LedgerEntry

GOV_ID = "gov-id"
UTILITY_BILL = "utility-bill"
REQUIRED_DISTINCT_ISSUERS = 2

class SatisfactionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    done: bool
    outstanding: list[str] = Field(default_factory=list)
    accepted_issuers: list[str] = Field(default_factory=list)  # sorted canonical set (parity, A2)

def is_satisfied(status: CollectionStatus) -> SatisfactionResult:
    accepted = [e for e in status.ledger if e.disposition == Disposition.ACCEPTED]
    gov_id_ok = any(e.doctype == GOV_ID for e in accepted)
    bill_issuers = sorted({
        e.issuer for e in accepted
        if e.doctype == UTILITY_BILL and e.issuer  # exclude None/empty (Decision 4)
    })
    done = gov_id_ok or len(bill_issuers) >= REQUIRED_DISTINCT_ISSUERS
    outstanding = [] if done else [GOV_ID, UTILITY_BILL]
    return SatisfactionResult(done=done, outstanding=outstanding, accepted_issuers=bill_issuers)
```

Notes:
- Accept `CollectionStatus` (the classified-ledger container the Bridge returns). Provide a thin
  convenience: `is_satisfied` may also be called with an `ExchangeTurn` by pulling `.status` — but
  keep the canonical signature on `CollectionStatus`; let the caller pass `turn.status`.
- `accepted_issuers` is a small, justified extra: `docs/lessons-learned.md` A2/A3 make the
  **accepted-issuer set** the mock↔real / ADK↔deterministic parity *destination*. Surfacing it now
  costs nothing and lets S1-4's parity tests assert it. Keep `done` + `outstanding` as the primary
  contract per the task.

## Deliverable 2 — authoritative ADK tool wrapper

Same file (or expose from `agents/src/agents/address/__init__.py`).

```python
from google.adk.tools.tool_context import ToolContext

COLLECTION_STATUS_STATE_KEY = "collection_status"  # S1-4 writes the latest ExchangeTurn/status here

def check_completeness(tool_context: ToolContext) -> dict:
    """Authoritative completeness gate. Reads the classified ledger from session
    state (never from the model) and returns {done, outstanding, accepted_issuers}.
    The model may call this to route; it can never fabricate "done"."""
    raw = tool_context.state.get(COLLECTION_STATUS_STATE_KEY)
    if not raw:
        # No collection yet -> not done, both alternatives outstanding.
        return SatisfactionResult(done=False, outstanding=[GOV_ID, UTILITY_BILL]).model_dump()
    status = _coerce_status(raw)  # accept CollectionStatus | ExchangeTurn | dict of either
    return is_satisfied(status).model_dump()
```

- `_coerce_status(raw)`: accept a `CollectionStatus`, an `ExchangeTurn` (use `.status`), or a plain
  `dict` (try `ExchangeTurn.model_validate` then fall back to `CollectionStatus.model_validate`).
  Robust to however S1-4 stores it; document the accepted shapes. If it cannot be coerced, treat as
  "no collection yet" (return not-done) rather than raising — a tool that raises would surface as an
  error event and could stall the loop.
- **State-key convention:** `COLLECTION_STATUS_STATE_KEY = "collection_status"`. Export it so S1-4
  writes the Bridge tool's returned `ExchangeTurn` under the same key. This is the single coupling
  point between S1-3 and S1-4; call it out in the module docstring.
- Do **not** wire the tool into `LlmAgent(tools=[...])` here — that is S1-4 (the task says
  "wired by S1-4"). Just make it importable (e.g. `from agents.address.satisfaction import
  check_completeness, is_satisfied, SatisfactionResult, COLLECTION_STATUS_STATE_KEY`). Optionally
  add it to `agents/src/agents/address/__init__.py` exports for discoverability.

## Deliverable 3 — unit tests

`agents/tests/test_satisfaction.py` (new). Reuse the explicit eval-entry mapping pattern from
`test_contract.py` / `mock_bridge/fixtures.py`. Add a small local helper:

```python
def _entries(*ids) -> list[LedgerEntry]:
    # load wiki/evals/address/expected.json (parents[2] / "wiki" / ... as in test_contract.py),
    # for each id build LedgerEntry(id, doctype, issuer, Disposition(expected_disposition),
    # Extraction.model_validate(extraction))
```

Cases (assert on `is_satisfied(CollectionStatus(ledger=_entries(...)))`):

| Ledger | `done` | Key assertion |
|---|---|---|
| `gov-id-clean` | `True` | gov-id OR branch; `accepted_issuers == []` |
| `gov-id-expired` | `False` | pending gov-id does not satisfy; `outstanding == ["gov-id","utility-bill"]` |
| `bill-powerco-clean`, `bill-powerco-clean-2` | `False` | **canonicalization equivalence** — both `power-co` → 1 distinct issuer; `accepted_issuers == ["power-co"]` |
| `bill-powerco-clean`, `bill-aquautil-clean` | `True` | 2 distinct accepted → done; `accepted_issuers == ["aqua-util","power-co"]` |
| `bill-powerco-clean`, `bill-aquautil-clear` | `False` | AquaUtil is `pending` → 1 distinct accepted |
| `bill-powerco-clean`, `bill-aquautil-blurry` | `False` | AquaUtil is `rejected` → 1 distinct accepted |
| `gov-id-clean`, `bill-aquautil-blurry` | `True` | gov-id branch wins regardless of a rejected bill |
| `passport-unsupported` | `False` | rejected non-bill doesn't count |
| empty `[]` | `False` | `outstanding == ["gov-id","utility-bill"]`, `accepted_issuers == []` |
| all seven `bill-*` + gov-ids (full corpus) | `True` | gov-id-clean present → done; also 2 distinct accepted issuers present |

Tool-wrapper tests (build a minimal fake/stub `tool_context` exposing `.state` as a dict, or a real
`ToolContext` if easy to construct — a lightweight stub is fine since the wrapper only touches
`.state.get`):
- state absent → `{"done": False, "outstanding": ["gov-id","utility-bill"], ...}`.
- state = an `ExchangeTurn` dict with a satisfying ledger (e.g. gov-id-clean) → `done True`.
- state = a `CollectionStatus` dict with two distinct accepted bills → `done True`.
- state = garbage/uncoercible → not-done (no raise).

## Files

- **New:** `agents/src/agents/address/satisfaction.py` (pure gate + result model + tool wrapper).
- **New:** `agents/tests/test_satisfaction.py`.
- **Edit (optional):** `agents/src/agents/address/__init__.py` — export
  `is_satisfied`, `SatisfactionResult`, `check_completeness`, `COLLECTION_STATUS_STATE_KEY`.
- **Edit (at completion):** `PLAN.md` — mark **S1-3** `- [x]` with
  `_(done <date>; Plan: /home/boris/working/.claude/plans/S1-3-is-satisfied-gate.md)_`.
- **Do NOT touch:** `bridge_client/*`, `contract/*`, the mock, `agent.py` (loop wiring is S1-4).

## Seams touched

None new. This is agent-side sense-B logic, not a managed-service boundary — no local/GCP adapter
pair. (It will later run inside the Collect loop the seam suite covers, but S1-3 adds no seam.)

## Gotchas (do not rediscover)

- **"co" is not a corporate suffix** (A4): the two PowerCo fixtures (`"PowerCo"` / `"Power Co."`)
  are already canonical `power-co` in the fixture — they MUST count as **one** issuer. The test above
  locks this; if it ever counts as two, canonicalization upstream regressed.
- **Only `ACCEPTED` counts.** `pending` (HITL) and `rejected`/resubmit are not completeness signals
  (A1: escalation ≠ rejection, but neither is "done"). Filter strictly on `Disposition.ACCEPTED`.
- **The model must not supply the ledger.** Keep the tool signature `tool_context`-only. A tool that
  accepts ledger data as an argument would let the model fabricate completeness — the exact thing
  A3 forbids.
- **No timestamps / ordering** (A5): the gate is order-independent (set + any), so the ledger's
  insertion-order fragility does not affect it — good, keep it that way (never rely on ledger order).
- **Tool must not raise on missing/garbage state** — return not-done instead, so a first-turn call
  (before any collection) or a malformed state doesn't error the loop.
- Sort `accepted_issuers` and keep `outstanding` deterministic so tests are stable across runs.

## Verification

- `uv run pytest` (fallback `.venv/bin/pytest`) from `agents/` — all green, incl. the new
  `test_satisfaction.py` and the unchanged existing suite (`test_contract.py`, `test_mock_bridge.py`,
  `test_native_consumer.py`, `test_control_return.py`, `test_round_trip.py`, `test_address_agent.py`,
  `test_scaffold.py`).
- `uv run ruff check` — clean.

## Acceptance criteria

1. `is_satisfied(CollectionStatus)` is a **deterministic pure function** implementing the Address
   rule (`gov-id` accepted **OR** ≥2 accepted utility-bills from distinct canonical issuers),
   returning `done` + `outstanding` (+ `accepted_issuers`).
2. Distinct-issuer is decided over the ledger's already-canonical `issuer` key; the two PowerCo
   fixtures count as one issuer (canonicalization equivalence verified).
3. Only `Disposition.ACCEPTED` entries count; `pending`/`rejected` never satisfy.
4. Exposed as an **authoritative ADK tool** (`check_completeness(tool_context)`) that reads the
   classified ledger from session state, not from model arguments — the model can call it to route
   but can never mint "complete".
5. Unit-tested against the `wiki/evals/address/expected.json` fixtures across all branches above;
   full suite + ruff green.
6. No changes to `bridge_client/`, `contract/`, or the mock; loop wiring left for S1-4.

## Out of scope (later bullets)

Multi-turn Collect loop + writing `collection_status` to state + wiring `check_completeness` into
`LlmAgent(tools=[...])` and the durable single-task/context span (S1-4); mock multi-turn document
arrivals / distinct-issuer bill fixtures / chase (S1-5); any RFP-style mutating requirements.
</content>
</invoke>
