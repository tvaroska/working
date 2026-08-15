# ADR-0007 — The A2A edge speaks canonical A2A (adopt the a2a-sdk), not a bespoke REST mapping

- **Status:** Accepted
- **Date:** 2026-08-14
- **Resolves:** the deferred-hardening notes in `.claude/plans/S1-core-3-a2a-a2ui-edges.md` (gotcha #2, "keep the existing plain-JSON REST mapping … Full JSON-RPC A2A envelope fidelity … deferred") and `.claude/plans/S1-agent-2-mock-document-bridge.md` ("Full A2A-protocol fidelity … out of scope; there is no `a2a-sdk` in this repo"); adds a tech-debt record (`docs/tech-debt.md` §9)
- **Context:** `wiki/bridge-adk.md` (principle), `wiki/bridge-a2a-edge.md`, `docs/decisions/adr-0001-stack.md`, `docs/decisions/adr-0006-adk-native-runtime.md`

## Context

The A2A edge is the Bridge's agent-facing front door — how the servicer's app opens an exchange
(`POST /a2a/exchanges`), how each servicer turn is posted (`POST /a2a/exchanges/{context}/turns`),
and how a Path-A party responds inbound. Today that surface is a **hand-rolled plain-JSON REST
mapping on FastAPI**: bespoke routes carrying the project's own `CollectRequest` / `ExchangeTurn` /
`RequirementsList` types, task get/list/cancel as ad-hoc REST paths, and hand-rolled SSE. It is
**not** the A2A wire protocol: no JSON-RPC 2.0 envelopes, no spec method names
(`message/send`, `message/stream`, `tasks/get`, `tasks/cancel`, `tasks/resubscribe`), no A2A
`Message`/`Task`/`Artifact`/`Part` objects. The one genuinely spec-conformant piece is the Agent
Card served at the well-known path (`/.well-known/agent-card.json`).

This deviation was **never a recorded decision**. It accreted from the agent-side mock and was
carried forward with "out of scope / deferred hardening" notes in two *plan* files — never an ADR.

That is the problem. The repo's governing principle (`wiki/bridge-adk.md:20`) is:

> **Prefer the … native construct over bespoke plumbing — every time.** … A wrapper we write
> ourselves both *hides* the platform we are showcasing and becomes ours to maintain. So the default
> is always the stock construct; **a custom layer needs a specific, recorded justification.**

ADR-0006 applied exactly this principle to the *runtime*: it deleted the hand-rolled ADK plumbing in
favour of stock ADK constructs because "using the platform natively *is* the demonstration." The A2A
edge is the same situation one layer out: A2A is a published protocol with stable SDKs
(ADR-0001:39 — "A2A has stable SDKs"), and a custom REST dialect that merely *borrows* A2A concepts
is precisely the "bespoke plumbing … that becomes ours to maintain" the principle forbids — carried
without the "specific, recorded justification" the principle requires. A servicer or partner agent
built against the real A2A spec cannot talk to our `/a2a/…` routes; the `a2a/` prefix signals intent,
not conformance.

## Decision

**The A2A edge conforms to the canonical A2A protocol, implemented on the standard `a2a-sdk`, not a
bespoke REST mapping.** Concretely:

| Concern | Decision |
|---|---|
| **Transport** | JSON-RPC 2.0 over the A2A-standard HTTP surface, served by the **`a2a-sdk`** — not hand-rolled FastAPI routes. Add `a2a-sdk` as a real dependency (it is named as rationale in ADR-0001:32 but depended on nowhere). |
| **Methods** | The spec methods — `message/send`, `message/stream`, `tasks/get`, `tasks/list`, `tasks/cancel`, `tasks/resubscribe` — replace the ad-hoc `POST /a2a/exchanges`, `.../turns`, `GET /a2a/tasks/{id}`, `.../events` routes. |
| **Objects** | A2A `Message` / `Task` / `Artifact` / `Part` on the wire. The domain types (`CollectRequest`, `ExchangeTurn{CollectionStatus}`, `RequirementsList`, `LedgerEntry`) become the **payload carried inside** A2A parts/artifacts — the domain contract is unchanged; only its envelope becomes standard. |
| **Streaming** | A2A `message/stream` / `tasks/resubscribe` (SSE per spec) replace the hand-rolled `/events` SSE. |
| **Agent Card** | Unchanged — `/.well-known/agent-card.json` is already spec-conformant (ADR-0006, S2-core-1). It stays skill-generated. |
| **Exchange identity** | Unchanged — Exchange **is** the A2A `context` (ADR-0003, `wiki/bridge-aggregate-model.md`); the Bridge still mints it at `open_exchange`. Canonical A2A is a natural fit: `context` is a first-class A2A concept. |
| **Document transfer** | Unchanged — by reference via `FileWithUri` in both directions (ADR-0006). This already uses A2A message types; conforming the envelope makes them first-class rather than hand-mapped. |

Phase 1's **inbound-only** posture (`wiki/bridge-a2a-edge.md:21`) is unchanged: the Bridge is the
A2A **server** for both the servicer's open-request and the party's inbound response. Bridge-as-A2A-**client**
(Agent-Card *discovery*, calling out) and outbound delivery remain deferred to Phase 4 — this ADR is
about the server surface speaking the spec, not about adding an outbound client.

## Rationale

- **The principle, applied consistently.** "As standard as possible" drove ADR-0006 to stock ADK; it
  drives this to stock A2A. A showcase that hand-rolls the very protocol it advertises undercuts its
  own pitch — and the deviation had no recorded justification, which the principle explicitly requires.
- **Interoperability is the point of A2A.** The value of the edge is that *any* A2A-conformant agent
  can talk to the Bridge. A bespoke REST dialect defeats that: it only interoperates with our own
  client. Spec conformance is what makes "one shared Bridge, many apps over A2A" (ADR-0006) real
  beyond our own fleet.
- **The domain contract survives intact.** The redesign is at the *envelope*, not the *content*. The
  app still opens an exchange, posts requirements turns, and reads `ExchangeTurn{CollectionStatus}`
  with a `LedgerEntry` tuple — those types just travel as A2A parts/artifacts. This mirrors ADR-0006's
  "extended, not broken" send-back contract: internals change, what the app *means* does not.
- **Less to maintain.** The SDK owns envelope framing, task lifecycle, and streaming/keepalive
  mechanics we currently hand-roll.

## Consequences / risks

- **This is a wire-breaking change for existing clients.** The agent's `HttpBridgeClient` and the
  agent-side mock both target the bespoke routes; both must move to the `a2a-sdk` client. The
  seam-parity discipline helps — the domain contract is unchanged, so golden-run and parity tests
  pin behaviour while the transport is swapped.
- **SDK maturity / version pinning.** `a2a-sdk` becomes a load-bearing dependency; its release
  cadence and any `[EXPERIMENTAL]` surfaces must be tracked, as ADR-0006 does for adk's
  `ResumabilityConfig`.
- **The A2UI edge is out of scope here.** ADR-0001:39 flags A2UI as newer and possibly lacking a
  mature library; the portal (Path B) keeps its current transport until a comparable decision is
  made for A2UI. This ADR governs the **A2A** edge only.
- **Migration is not yet scheduled as done.** This ADR records the decision and target; the
  implementation is tracked as a task (see `PLAN.md` → Deferred hardening, and `docs/tech-debt.md` §9).
  Until it lands, the edge remains the plain-JSON REST mapping and docs must say so.

## Alternatives considered

- **Keep the bespoke REST mapping (status quo).** Rejected: violates "as standard as possible" with
  no recorded justification, and defeats A2A interoperability — the whole reason to have an A2A edge.
- **Adapter/shim in front of the REST routes** (translate JSON-RPC ↔ our REST). Rejected: keeps the
  bespoke core alive behind a translation layer — more plumbing to own, not less; the opposite of the
  principle.
- **Wait for Phase 4 (when the outbound A2A client lands).** Rejected: the *inbound server* is the
  Phase-1 surface real agents already integrate against; conforming it is independent of, and more
  urgent than, the deferred outbound client.

## Note

This ADR narrows ADR-0001 (which named "the A2A SDK" as rationale but left the edge hand-rolled) and
completes ADR-0006's platform-native direction on the transport layer. The Agent Card, exchange-as-context
identity, and by-reference document transfer are already spec-aligned and carry over unchanged.
