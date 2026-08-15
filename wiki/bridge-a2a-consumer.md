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

## Wiring into the caller: transfer vs. call-and-return

`RemoteA2aAgent` is *what* consumes the Bridge; **how it hangs off the caller** is a second, consequential choice, because it decides whether control comes **back**:

| Wiring | Semantics | Control after the Bridge returns |
|---|---|---|
| **`sub_agents` + `transfer_to_agent`** | the caller **hands over** control to the Bridge sub-agent; the Bridge's relayed `ExchangeTurn` becomes the turn output | **does not return** to the caller — the turn ends at the sub-agent (a `RemoteA2aAgent` issues no transfer-back) |
| **`AgentTool`** | the caller **calls** the Bridge as a tool and **keeps** control; the `ExchangeTurn` comes back as the tool result | **returns** to the caller, which can post-process and loop |

The M0 tracer bullet uses **transfer** (`sub_agents`): thinnest one-shot delegation, no post-processing. But the [[bridge-collect|Collect]] loop's completeness decision (**`is_satisfied` — the app owns "done"**, Sense B) has to run **in the caller, after the Bridge returns its ledger**, then chase the next proof or stop. That post-processing loop needs control to come back — so the completeness-gated flow adopts **`AgentTool`** (or a follow-up root turn); transfer alone can't host the gate. This is a deliberate Sprint-1 switch, not the M0 default. See `adr-0009` (amendment) and [[bridge-collect]].

A second consequence of transfer: it forwards **conversation content**, not a structured `CollectRequest` DataPart — so the typed outbound request leaves the send path under M0's transfer wiring. Restoring it (carrying `CollectRequest` as a JSON part) rides along with the `AgentTool` switch.

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

## M0 note — the port was removed; the consumer is now native

The [[bridge-collect|Collect]] tracer bullet (M0) originally consumed the Bridge through a hand-rolled `BridgeClient` port + `A2ABridgeClient` (a blocking `message/send` → `tasks/get` poll loop) wrapped in a `FunctionTool`. Once the wire contract was validated the port was **removed** (not merely tracer-bullet-only): the address agent now consumes the Bridge as a native `RemoteA2aAgent` wired as a **`sub_agent`** (`agents/src/bridge_client/build_bridge_remote_agent`), and the pure A2A wire helpers survive in `bridge_client/wire.py`. This goes beyond the original `adr-0009` (which retained the port as a permanent double) — recorded in the **adr-0009 amendment (2026-08-15)**. Sprint 1 grows the Collect loop against the native consumer, switching the wiring from transfer to `AgentTool` for the completeness gate (above).

## Status

- **Decided (`adr-0009`):** `RemoteA2aAgent` is the canonical consumer; waits are `input-required` (native pause), progress is `TaskStatusUpdateEvent.status.message`, integration-extension mode pinned (`use_legacy=True` until validated).
- **Committed / already in the edge:** `_status_for` maps a pending collection → `INPUT_REQUIRED` ([[bridge-a2a-edge]]); native HITL pause/resume ([[bridge-adk]]).
- **Landed (2026-08-15):** the address agent consumes the Bridge as a native `RemoteA2aAgent` **sub-agent** (transfer); the M0 `BridgeClient` port was removed (adr-0009 amendment). Mock park (`INPUT_REQUIRED`) + non-empty `status.message` progress are covered by the seam suite.
- **Sprint 1 (remaining):** switch the wiring from transfer to **`AgentTool`** so control returns for the **`is_satisfied`** gate; restore the structured `CollectRequest` on the send path; grow the multi-turn Collect loop. See `PLAN.md`.
- **Risk:** `RemoteA2aAgent` is `@a2a_experimental` in `google-adk` 2.7.0 — pin and cover in the shared seam suite (`docs/decisions/adr-0001-stack.md`).

## Related
- [[bridge-a2a-edge|A2A edge]] (server side), [[bridge-adk|running on ADK]], [[bridge-long-running|long-running collection]], [[bridge-collect|Collect]]
- **Decision record:** `docs/decisions/adr-0009-native-a2a-consumer.md`
