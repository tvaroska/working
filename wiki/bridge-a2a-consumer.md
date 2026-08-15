---
type: atom
related:
  - "[[bridge-a2a-edge]]"
  - "[[bridge-adk]]"
  - "[[bridge-long-running]]"
  - "[[bridge-collect]]"
tags: [bridge]
status: draft
updated: 2026-08-15
---

# A2A Consumer (calling the Bridge)

> The other side of the [[bridge-a2a-edge|A2A edge]]: how a servicer's (or processing) agent **consumes** the Bridge over canonical A2A. The principle is the same as everywhere else — **prefer the platform-native construct** ([[bridge-adk]]). For an ADK agent that calls another A2A agent, that construct is **`RemoteA2aAgent`**, not a hand-rolled A2A client. Decision: `docs/decisions/adr-0009-native-a2a-consumer.md`.

> **This is not the deferred outbound client.** "Bridge-as-client" (the Bridge *dialing out* to counterparties, Agent-Card discovery — Phase 4, [[bridge-a2a-edge]]) is a different direction. Here it is *our* agent calling the Bridge inbound — the pull spine the core is built around.

## The native construct

An agent consumes the Bridge by instantiating **`RemoteA2aAgent`** against the Bridge's [[bridge-a2a-edge|Agent Card]]. It resolves the card, manages the A2A client, converts `Message`/`Task`/`Part` to ADK events, and — crucially — maps the A2A task lifecycle onto ADK's own pause/resume. We hand-roll none of that.

| Concern (consumer side) | ADK-native construct | Not this |
|---|---|---|
| Calling another A2A agent | **`RemoteA2aAgent`** (card-configured) | a hand-rolled A2A client + `tasks/get` poll loop wrapped in a `FunctionTool` |
| Awaiting a long collection | native pause on `input-required` (→ `LongRunningFunctionTool`) | a blocking poll loop that holds the caller's turn |
| Learning of progress | streamed `TaskStatusUpdateEvent` (rendered as *thought*) | a bespoke status side-channel |

The reusability thesis is unchanged — *the difference between demos is the agent, not the Bridge* ([[bridge|core vs demos]]). Each demo points a `RemoteA2aAgent` at the same unchanged Bridge card; the mock→real and local→GCP swaps are a **different card URL**, not different agent code.

## Two mechanisms for long-running work

A collection runs for [[bridge-long-running|days or weeks]]. `RemoteA2aAgent` supports that through two standard mechanisms, and the **Bridge's task status is what selects which one the caller gets**:

1. **Hold and wait (seconds → minutes).** While connected, the caller consumes the task's update stream; `submitted`/`working` states surface as ADK *thought* events (progress), never the final answer. Bounded by the client timeout (ADK default 600s). Fine for the M0 ~10s hold; **cannot** span weeks.
2. **Pause and resume (hours → weeks, zero compute).** When the Bridge parks awaiting an external event, its task returns **`input-required`** (or `auth-required` for a credential blocker). `RemoteA2aAgent` turns that into a **`LongRunningFunctionTool` pause**: the caller's invocation *ends* (zero compute), the peer `task_id` + `context_id` persist on the [[bridge-aggregate-model|session]], and a later `FunctionResponse` resumes to the *same* task. This is the **same** native durability the Bridge already uses for [[bridge-adk|HITL]] — now reused across the caller↔Bridge edge for free.

## Waiting is `input-required` — and the edge already emits it

Mechanism 2 needs the Bridge to express "parked, resume later" as **`input-required`**, not a prolonged `WORKING`. The [[bridge-a2a-edge|A2A edge]] **already does this**: disposition maps a not-yet-complete collection to task status the ordinary way (`_status_for`: a `PENDING` item → `INPUT_REQUIRED`, otherwise `COMPLETED`). So the consumer change is small — **treat `INPUT_REQUIRED` as a resumable pause, not a failure.** (The M0 tracer-bullet client deliberately treats it as terminal-failure because M0 is single-turn; that inverts at adoption — see M0 note.)

## Progress is `TaskStatusUpdateEvent.status.message`

Live progress rides the standard streaming event: a **`TaskStatusUpdateEvent` carrying a non-empty `status.message`** over `message/stream`. `RemoteA2aAgent` renders it as a thought event.

- **`a2a-sdk` 1.x gotcha:** the SDK carries an always-present *empty* proto `Message`; ADK collapses it to `None` and only surfaces a status update when a **real, non-empty** `Message` is attached. **An empty `status.message` is silently dropped** — mock and real Bridge must attach real parts.

## Timescales compose

| Timescale | Mechanism | Wire |
|---|---|---|
| seconds–minutes, connected | hold + streamed status | `message/stream`, `TaskStatusUpdateEvent` |
| hours–weeks, idle | pause + resume | `input-required` → `LongRunningFunctionTool`; woken by push |
| after disconnect | re-attach / snapshot | `tasks/resubscribe`, `tasks/get` |
| weeks-scale wakeup | callback | `PushNotificationConfig` (Phase 3, `adr-0008`) |
| terminal | deliverable | `ExchangeTurn` artifact on `COMPLETED` |

## M0 note — the port is the tracer-bullet double, superseded here

The [[bridge-collect|Collect]] tracer bullet (M0) consumes the Bridge through a hand-rolled `BridgeClient` port + `A2ABridgeClient` (a blocking `message/send` → `tasks/get` poll loop) wrapped in a `FunctionTool` (`agents/src/bridge_client/`). That was the right *hermetic tracer-bullet* choice. Per `adr-0009` it is **superseded from Sprint 1** by `RemoteA2aAgent`; Sprint 1 grows the Collect loop against the native consumer, **not** behind the port. M0 itself is unchanged.

## Status

- **Decided (`adr-0009`):** `RemoteA2aAgent` is the canonical consumer; waits are `input-required` (native pause), progress is `TaskStatusUpdateEvent.status.message`, integration-extension mode pinned (`use_legacy=True` until validated).
- **Committed / already in the edge:** `_status_for` maps a pending collection → `INPUT_REQUIRED` ([[bridge-a2a-edge]]); native HITL pause/resume ([[bridge-adk]]).
- **Sprint 1 (implementation):** adopt `RemoteA2aAgent` in the demos; mock + real Bridge emit `input-required` on park + non-empty `status.message` on progress; flip the consumer's `INPUT_REQUIRED`-is-failure guard. None built yet.
- **Risk:** `RemoteA2aAgent` is `@a2a_experimental` in `google-adk` 2.7.0 — pin and cover in the shared seam suite (`docs/decisions/adr-0001-stack.md`).

## Related
- [[bridge-a2a-edge|A2A edge]] (server side), [[bridge-adk|running on ADK]], [[bridge-long-running|long-running collection]], [[bridge-collect|Collect]]
- **Decision record:** `docs/decisions/adr-0009-native-a2a-consumer.md`
