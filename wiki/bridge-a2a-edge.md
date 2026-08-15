---
type: atom
related:
  - "[[bridge-edges]]"
  - "[[bridge-aggregate-model]]"
  - "[[bridge-long-running]]"
tags: [bridge]
status: review
updated: 2026-08-14
---

# A2A Edge (agents)

> The Bridge's agent-facing front door — an A2A server for Path-A partner/carrier agents and the internal servicer agent.

**Surface.** The edge speaks **canonical A2A** — JSON-RPC 2.0 on the standard `a2a-sdk`, per the "as standard as possible" principle ([[bridge-adk]]) and `docs/decisions/adr-0001-stack.md`. No bespoke REST dialect.
- Spec operations: `message/send`, `message/stream`, `tasks/get` / `tasks/list` / `tasks/cancel` / `tasks/resubscribe`, with A2A `Message` / `Task` / `Artifact` / `Part` on the wire. The domain types (`CollectRequest`, `ExchangeTurn{CollectionStatus}`, `RequirementsList`, `LedgerEntry`) travel as the payload carried **inside** A2A parts/artifacts — the domain contract is unchanged; the envelope is standard.
- Dynamic **Agent Card** at the well-known discovery location, generated from installed skills' `name`/`description` ([[bridge-skills|Agent Skills format]]) — the progressive-disclosure discovery layer — so a live skill-add regenerates it with no redeploy.
- **Streaming** via `message/stream` / `tasks/resubscribe` (SSE per spec) for long-running tasks (status + artifact events, keepalives).
- Task lifecycle, **artifact versioning** (each version is a new artifact on the same task), pluggable persistence, and concurrency-safe cancellation of active tasks.

**Inbound fulfillment is the Phase-1 surface.** A party responds on the A2A edge with the exchange's context token (Path A: a structured data response), or via the portal (Path B). Because the party responds **inbound**, Phase 1 needs **no A2A client and no outbound delivery** — the party is handed the link/context out-of-band. Bridge-as-client (Agent-Card discovery, calling out) and outbound are **deferred to Phase 4**.

**What the Bridge sends back.** The deliverable to the servicer's agent is an **`ExchangeTurn`** carrying a **`CollectionStatus`** — the **classified ledger**: a tuple of `LedgerEntry` (doctype · disposition · canonical issuer · key fields), plus a best-effort "still outstanding" and a `terminal` flag. Accepted documents appear as **[[bridge-artifacts|artifact references]]** (a `FileWithUri` handle), not bytes — the agent fetches bytes on demand from the scoped endpoint. Disposition maps to A2A task status the ordinary way (`_status_for`: a PENDING item → `INPUT_REQUIRED`, otherwise `COMPLETED`), so **the app reads standard A2A task status + a ledger projection — never ADK events.** The internals are an [[bridge-adk|LlmAgent + tools]]; what crosses this edge is the domain contract plus an additive artifact reference. See [[bridge-disposition|disposition]] for how each entry's verdict is set.

**Long-running tasks (days → weeks).** An A2A task is a durable server-side resource with **no built-in TTL** — a collection can legitimately stay `WORKING`/`INPUT_REQUIRED` for weeks. Nobody holds it open: the task is persisted and woken only by a party turn, a [[bridge-proactive|clock alarm]], or an HITL resume. Clients learn of progress without a held connection via `tasks/get` (poll), `tasks/resubscribe` (re-attach after disconnect), and — pulled forward for weeks-scale — push-notification webhooks (today *[Phase 4]*). See [[bridge-long-running|long-running collection]] for the full model, the Phase-3 durability substrate, and the open expiry/token-validity questions.

**Programs (multi-party fan-out).** Each leg is its own context + party — competitors never share a context (isolation by per-leg addressing, not UI filtering). A provider-facing program context links the legs and carries the rollup. *[Aspirational — Phase 2]*

Push-notification webhooks for state changes are *[Aspirational — Phase 4]*.

## Related
- [[bridge-edges|two edges]], [[bridge-aggregate-model|aggregate model]], [[bridge-artifacts|artifacts]], [[bridge-disposition|disposition]], [[bridge-long-running|long-running collection]]
