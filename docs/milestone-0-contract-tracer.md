# Milestone 0 — Contract Tracer Bullet

**Status:** 📋 Planned (0%) · **Release:** 1 (precedes Sprint 1) · **Spec:** `wiki/bridge-a2a-edge.md`, `wiki/bridge-implementation-plan.md`, `wiki/evals/address/`

> The thinnest end-to-end slice: one **address app agent** asks once, a **mock Document Bridge** accepts the request, holds it ~10s, and returns an `id` plus the structured extraction info drawn from the address evals. No Collect loop, no disposition, no extraction, no frontend, no GCP. **The single purpose is to validate the input/output design** — the agent↔Bridge contract and its long-running (async) shape — before any real logic is committed on either side.

## Why this comes first

The roadmap's Sprint 1 is *agent-first*: the agent defines the A2A contract, and a mock Bridge is the permanent contract double (`docs/features/processing-agents.md`). Milestone 0 pulls the **contract itself** out ahead of that work as a tracer bullet. If the request/response types or the long-running surface are wrong, we find out in a day — not after the multi-turn loop, satisfaction gate, and disposition are built on top of them. The mock and the contract models built here are **kept**, not thrown away — they become the Sprint 1 harness.

It is also the earliest honest proof of the three day-one platform bets (`docs/decisions/adr-0001-stack.md`): the agent is a real **ADK `LlmAgent`**, the edge speaks **canonical A2A via `a2a-sdk`**, and both run on the **local dev path** with the seam interfaces that later swap to GCP.

## What it proves (and what it deliberately does not)

**Validates:**
- The **domain contract**: `CollectRequest` in, `ExchangeTurn{CollectionStatus}` out, with `LedgerEntry` carrying the `id` + structured extraction fields — serialized **inside** A2A parts/artifacts (`wiki/bridge-a2a-edge.md`), proving the domain payload survives the standard envelope.
- The **`BridgeClient` port** — the transport-agnostic seam the agent core talks through, so the later mock→real swap is a no-op for the agent.
- The **long-running surface** — `message/send` returns a `Task{WORKING}`; the agent polls `tasks/get` until `COMPLETED`, then reads the payload. The ~10s hold is a real test of the poll path the whole system rests on, not a throwaway sleep.
- That eval data is a usable **fixture source of truth** — the returned structured info comes straight from `wiki/evals/address/expected.json`.

**Explicitly out of scope (Sprint 1 and later):**
- No multi-turn Collect loop, no `is_satisfied` gate, no requirements re-proposal.
- No disposition / classification / issuer canonicalization / confidence gates.
- No real extraction (Gemini) — the mock returns canned eval fields.
- No proactive chase, scheduler, or HITL.
- No frontend, no GCP adapters, no Terraform, no persistence (in-memory task store only).
- No skills registry — the single `address-proof` request is hard-coded for party `jordan-lee`.

## The one exchange

```
Address LlmAgent                     Mock Document Bridge (a2a-sdk server)
     |                                          |
     | message/send(CollectRequest)             |
     |----------------------------------------->| create Task -> WORKING
     |          Task{id, WORKING}               | (hold ~10s: fixed delay)
     |<-----------------------------------------|
     | tasks/get(id)   (poll)                   |
     |----------------------------------------->| still WORKING
     |          Task{WORKING}                   |
     |   ...poll until ready...                 |
     |----------------------------------------->| load wiki/evals/address/expected.json
     |   Task{COMPLETED, artifact:              |   -> COMPLETED with CollectionStatus
     |     CollectionStatus{ledger:[LedgerEntry(id, fields...)]}}
     |<-----------------------------------------|
     | render/assert id + structured info       |
```

The mock answers with a **single accepted document** for this milestone (e.g. `gov-id-clean` from the evals): one `LedgerEntry` carrying its `id`, `doctype`, canonical `issuer`, and `key_fields`. The full document corpus and multi-doc ledgers come with the Sprint 1 Collect loop.

## Task breakdown

1. **Repo + toolchain scaffold** — `uv` project, Python 3.12+, pin `google-adk >= 2.7.0,<3` and `a2a-sdk`, pytest, ruff. `agents/` package layout. (Overlaps the roadmap's Sprint 0 scaffolding; do only what this slice needs.)
2. **Contract models** (`agents/src/contract/`) — Pydantic `CollectRequest`, `ExchangeTurn`, `CollectionStatus`, `LedgerEntry`, and the extraction `fields` shape. These are the artifact under validation; mirror the field names in `wiki/evals/address/expected.json`.
3. **`BridgeClient` port** — the transport-agnostic interface the agent calls (`collect(request) -> ExchangeTurn`), with an `a2a-sdk` implementation that does `message/send` + `tasks/get` polling.
4. **Mock Document Bridge** (`agents/src/agents/mock_bridge/`) — an `a2a-sdk` server exposing `message/send` / `tasks/get`; on send, create an in-memory task, mark `WORKING`, hold ~10s, then complete it with a `CollectionStatus` whose `LedgerEntry` is loaded from `wiki/evals/address/expected.json`. Serve a minimal Agent Card at `/.well-known/agent-card.json`.
5. **Address `LlmAgent` scaffold** (`agents/src/agents/address/`) — a `google-adk` `LlmAgent` with the `BridgeClient` wired as a tool/port; one turn: request `address-proof` for `jordan-lee`, await the result via the port, render the returned `id` + structured info.
6. **Round-trip test** — one pytest that runs agent→mock→agent and asserts the returned payload matches the eval `expected.json` entry (id + key fields). Assert the agent observed `WORKING` before `COMPLETED` (the async path was exercised). Keep the 10s hold configurable so the test can shrink it.
7. **Run doc** — a short `agents/README.md`: how to start the mock and run the agent locally, and how to run the test.

## Definition of done

- `message/send` → `Task{WORKING}` → `tasks/get` poll → `Task{COMPLETED}` round-trips locally, mock holds ~10s, and the agent renders the `id` + structured info sourced from the address evals.
- The green round-trip test asserts the payload against `wiki/evals/address/expected.json` and confirms the async (poll) path ran.
- Contract Pydantic models + `BridgeClient` port committed; the mock persists as the Sprint 1 contract double.
- Agent is a real ADK `LlmAgent`; edge is canonical A2A via `a2a-sdk` — the day-one platform bets stand on the first executable slice.

## Validation checkpoint

Internal review of the **contract shape** with the design owner: are `CollectRequest` / `CollectionStatus` / `LedgerEntry` the right envelope, does the domain payload sit cleanly inside A2A parts, and is `tasks/get` polling the async surface we want before push-notifications land (Phase 3, `wiki/bridge-long-running.md`)? Sign-off here de-risks the entire Sprint 1 build.

## Feeds into

- **Sprint 1** (`wiki/bridge-implementation-plan.md`) — the mock grows the multi-turn Collect contract + fixture arrivals; the agent grows the loop + `is_satisfied` gate; the real Bridge (local) is built and the mock→real / local→GCP swap must be a no-op for the agent. **Consumer construct changes in Sprint 1:** per `docs/decisions/adr-0009-native-a2a-consumer.md` the agent adopts the native `RemoteA2aAgent` (swap = a different Agent Card URL), and the M0 `BridgeClient` port becomes tracer-bullet-only — the Collect loop grows against `RemoteA2aAgent`, not behind the port. See `wiki/bridge-a2a-consumer.md`.
