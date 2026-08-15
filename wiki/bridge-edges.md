---
type: concept
down:
  - "[[bridge-a2a-edge]]"
  - "[[bridge-a2ui-edge]]"
  - "[[bridge-dual-path]]"
related:
  - "[[bridge]]"
  - "[[bridge-zones]]"
tags: [bridge]
status: review
updated: 2026-08-05
---

# Two Edges

> The Bridge is **not a pure A2A server** — it meets parties at their level of digital maturity through two edges: an **A2A edge for agents** and an **A2UI edge for humans**.

Parties vary. Some run their own agent; some are a person with a PDF. Rather than force everyone onto one protocol, the Bridge exposes two front doors and normalizes both into the same internal task/artifact model — so the servicer's agent gets a uniform interface regardless of who's on the other end.

- **[[bridge-a2a-edge|A2A edge]]** — for agent counterparties (and the internal servicer agent). Task lifecycle, artifact versioning, event streaming, a dynamic Agent Card.
- **[[bridge-a2ui-edge|A2UI edge]]** — for parties without an agent. The Bridge emits declarative A2UI and ingests a structured response back. It owns **content and protocol, not pixels** — any host renders it; the reference renderer is demo furniture.

The choice is invisible to the requester: a party responds indistinguishably in one of two fulfillment modes, decided only by what kind of Part arrives — see [[bridge-dual-path|dual-path fulfillment]].

Both edges enter through the same trust boundary — [[bridge-zones|Agent Gateway ingress]] — and the Bridge stays the source of truth for exchange identity on both.

## Read next
- [[bridge-a2a-edge|A2A edge]] — the agent-facing server
- [[bridge-a2ui-edge|A2UI edge]] — the human-facing declarative surface
- [[bridge-dual-path|dual-path fulfillment]] — Path A validate-only vs Path B extract

## Related
- [[bridge|the Bridge]], [[bridge-zones|network zones]]
