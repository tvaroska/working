# ADR-0013 — Servicing-agent-authored explanations relayed to the party via A2UI

- **Status:** Accepted
- **Date:** 2026-08-16
- **Ratified at:** M1 sign-off gate (2026-08-16) — the `reason_code`-as-free-string trade-off (see Consequences) accepted on the record; contract fields (`reason_code`/`message`, `Requirement`/`RequirementsList`) and the requirements-with-reasons relay were built in M1.9 against this decision.
- **Context:** `wiki/bridge-collect.md` (Requirements vs Collection-status ownership; the Sense A/B line), `wiki/bridge-a2ui-edge.md` (content-not-pixels), `docs/decisions/adr-0011-contract-type-sharing.md` (shared contract types), `docs/lessons-learned.md` A3 (LLM routes, code decides). Extends the Collect contract in `agents/src/contract/models.py`.

## Context

The Bridge is **mediation, not policy**. It authoritatively decides *what a document is* — "this parsed file is a valid `gov-id`" (Sense A, always the Bridge — `bridge-collect.md`) — but it does **not** decide *whether that document matters, or why it fails to*. "A passport is not an accepted proof of address for this program," "two utility bills from the same company count as one provider" — these are **Sense B** judgments owned by the servicing agent (the app). The Bridge holds *no final word* on completeness and cannot author the domain reasoning behind a rejection or an outstanding item.

But the party (the human uploading documents through the [[bridge-a2ui-edge|A2UI edge]]) needs exactly that reasoning: *what is wrong, why it is wrong, and what to do next.* Today the Collect contract carries the *what* — `CollectionStatus.outstanding: list[str]` and `LedgerEntry.disposition` — but not the ***why***. There is no field on the wire for the app-authored explanation, so either the Bridge would have to invent domain prose it has no authority to write, or the party gets a bare status with no actionable reason.

This ADR closes that gap: it adds an **app-authored explanation** to the two owned artifacts and defines how the Bridge relays it to the party **without interpreting it** — preserving the mediation/policy split and the reusability claim ("the difference between demos is the agent, not the Bridge").

## Decision

### 1. The explanation rides the artifacts the app already owns

Per `bridge-collect.md`, the Collect loop has two versioned artifacts with two owners:

| Artifact | Owner | Carries |
|---|---|---|
| **Requirements** | **app** | *what's needed*, *is it done*, **and now: why each item is outstanding** |
| **Collection status** (classified ledger) | **Bridge** | *what we have*; per-doc disposition **+ now: the app-authored reason a doc was rejected** |

No new coordination turn is introduced — the reasoning rides the existing `app → Bridge: requirements list + done?` turn (`bridge-collect.md:24`) and the existing per-doc ledger entry. The app supplies the explanation as data; the Bridge transports it.

### 2. Two fields, split along "LLM routes, code decides" (A3)

Each outstanding requirement and each rejected ledger entry gains **two** fields:

- **`reason_code: str | None`** — a stable machine key (e.g. `unsupported-doctype`, `distinct-issuer-needed`, `illegible`). **Minted by the app's deterministic gate** — code decides *whether* there is a problem. The Bridge keys its chase on this so re-chasing the same deficiency is idempotent and auditable. It is a **free string, not a global enum**, because the vocabulary is per-skill; a shared enum would couple the domain-agnostic Bridge to one demo's domain.
- **`message: str | None`** — the human-facing prose. **Authored by the app** (a servicing agent's LLM is *allowed and expected* to compose it — this is the sanctioned place for model-generated text, since the *route/verdict* is already decided by code). The Bridge never writes or edits it.

### 3. Contract additions (`agents/src/contract/models.py`)

- New `RequirementStatus` enum — the whole status vocabulary from `bridge-collect.md:41`: `required | optional | satisfied | waived`.
- New `Requirement` model: `item`, `status`, `doctype_hint?`, `reason_code?`, `message?`.
- New `RequirementsList` model (the **app-owned** artifact): `requirements: list[Requirement]` + `done: bool`. Travels **inside** A2A parts/artifacts (canonical A2A — ADR-0001 bet 2), alongside `ExchangeTurn`; it is *not* nested in the Bridge-owned `CollectionStatus`, preserving the two-owner split.
- `LedgerEntry` gains optional `reason_code?` + `message?` for per-document rejection reasons.

All additions are **optional with defaults**, so existing `ExchangeTurn`/`CollectionStatus`/`LedgerEntry` payloads (and the eval fixtures) validate unchanged — no migration, no break to the shipped bounded Address gate.

### 4. Delivery: the Bridge maps reason → A2UI content, never pixels

The Bridge renders `{status, message, doctype_hint}` (and, per doc, `{disposition, message}`) into a **declarative A2UI turn** — the "party status" view the A2UI edge already defines: *"what you sent, what's accepted, what's still missing, what's next"* (`bridge-a2ui-edge.md`). The Bridge describes *what to show* (the explanation, an upload action, examples) but never *how it looks*; the host frontend renders it. The Bridge is transport + layout over the app's words and adds **no policy and no prose**.

The A2UI content model itself (declarative render spec) is **out of scope for this ADR** — this ADR fixes the contract that *feeds* it. The mapping is: one outstanding `Requirement` (or one rejected `LedgerEntry`) → one content block `{title from item/doctype, body from message, action from status+doctype_hint}`.

## Consequences / risks

- **The Bridge stays domain-agnostic.** It relays `message` verbatim and keys chase behavior on `reason_code`; it never needs to understand address-proof, benefits, or RFP rules. Each demo plugs its own reasoning by authoring different `reason_code`/`message` values — the A2UI renderer is generic over `{status, message, doctype_hint}`.
- **A3 is preserved and sharpened.** The deterministic gate still owns the verdict (`reason_code`); the LLM's contribution is confined to prose (`message`) that cannot change the route. A model still may **never** mint a KYC acceptance.
- **`reason_code` is an unbounded string.** This is deliberate (pluggability) but means there is no compile-time check that the Bridge's chase logic handles every code. Mitigation: the Bridge's chase behavior is driven by `status` (`required`/`optional`) — the mechanical knob — not by `reason_code`; an unrecognized `reason_code` still chases correctly, it just isn't specially handled.
- **Bounded vs emergent both fit.** The bounded Address demo can pre-author `message` templates against its fixed rule; the emergent RFP demo (`bridge-collect.md:56`) has its app compose `message` per turn via LLM. `next_requirements` remains a pure function of `(status, ledger)`, so no side sits in the loop.
- **This is a contract extension, ratified at the M1 sign-off gate (2026-08-16).** The bounded Address demo (deterministic `is_satisfied` gate returning a terminal ledger) is unaffected; the requirements-with-reasons round trip landed in **M1.9** (`bridge/src/bridge/requirements.py`, contract fields, `skills/address-proof/assets/explanations.yaml`). The A2UI content-model mapper remains follow-on work (M1.10 reference renderer is demo furniture; the declarative render spec is out of scope for this ADR, per §4).

## Cross-references

- **`wiki/bridge-collect.md`** — the two-owner artifact split and the Sense A/B line this ADR builds on; the Requirements payload shape (`item/status/doctype_hint`) that gains `reason_code`/`message`.
- **`wiki/bridge-a2ui-edge.md`** — the content-not-pixels edge that renders the relayed explanation.
- **ADR-0011** (contract-type sharing) — the shared-contract discipline these new types follow (`bridge/` and `agents/` consume the same `contract` package by construction).
- **ADR-0001** (canonical A2A) — the new domain types travel inside A2A parts/artifacts, not a bespoke REST dialect.
- **`docs/lessons-learned.md` A3** — LLM routes, code decides; this ADR is where the "code" (`reason_code`) and "LLM" (`message`) halves of an explanation are separated on the wire.
