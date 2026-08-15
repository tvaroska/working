# ADR-0009 — Native A2A consumer (`RemoteA2aAgent`) + wait/progress expressed on the wire

- **Status:** Accepted (amended 2026-08-15 — port removed, see Amendment)
- **Date:** 2026-08-15
- **Supersedes (consumer side):** the hand-rolled `BridgeClient` port + `A2ABridgeClient` + `FunctionTool` consumer introduced for the M0 tracer bullet (`agents/src/bridge_client/`, M0.3/M0.5). Originally retained for M0; **now removed** (see Amendment).
- **Context:** `docs/decisions/adr-0001-stack.md`, `docs/decisions/adr-0008-long-running-collection-lifecycle.md`, `wiki/bridge-adk.md`, `wiki/bridge-a2a-edge.md`, `wiki/bridge-long-running.md`; installed `google-adk == 2.7.0` (`google/adk/agents/remote_a2a_agent.py`), `a2a-sdk` 1.1.x.

## Context

ADR-0001 fixes the governing principle: **prefer the platform-native construct over bespoke plumbing, every time; a custom layer needs a specific, recorded justification.** For an ADK agent that *calls another A2A agent*, ADK ships a native construct — `RemoteA2aAgent` — that resolves the peer's Agent Card, manages the client, converts A2A `Message`/`Task`/`Part` to ADK events, and (crucially) maps A2A task lifecycle onto ADK's own pause/resume.

The M0 tracer bullet instead consumes the Bridge through a hand-rolled seam: a `BridgeClient` port with an `A2ABridgeClient` adapter whose `collect()` does `message/send` → **blocking poll loop** on `tasks/get` until terminal, wrapped in a `FunctionTool`. That was the right *tracer-bullet* choice (hermetic, tiny, validates the wire contract). But as the target consumer it has three problems the native construct solves:

1. **It only ever holds.** `collect()` blocks in its poll loop for the whole wait. It gets no zero-compute suspend, so it cannot reach the days/weeks scale ADR-0008 commits the Bridge to.
2. **No progress visibility.** A single terminal snapshot; nothing surfaces intermediate `working` status to the caller.
3. **It hand-rolls what ADK already does.** Card resolution, client lifecycle, part conversion, and pause/resume are re-implemented — exactly the bespoke plumbing ADR-0001 forbids without a recorded justification, and there is none for the consumer side.

Reading the installed `RemoteA2aAgent` (ADK 2.7.0) confirms it supports long-running work through two standard mechanisms, and that the Bridge's *contract shape* is what determines which one a caller gets. This ADR adopts the native consumer **and** fixes the wire vocabulary the Bridge must emit so the durable path is reachable.

## Decision

### 1. `RemoteA2aAgent` is the canonical way our agents consume the Bridge

Agent-side callers of the Bridge (the demo processing agents — Address, Benefits, RFP — and any internal agent that calls the Bridge over A2A) consume it via ADK's **`RemoteA2aAgent`**, configured with the Bridge's Agent Card. We do **not** hand-roll an A2A client, poll loop, or `FunctionTool` wrapper for this direction.

- The reusability claim is preserved: "the difference between demos is the agent, not the Bridge." Each demo instantiates its own `RemoteA2aAgent` against the same unchanged Bridge card; the Bridge core does not change per demo.
- The seam is preserved by *substitution, not wrapping*: the mock→real and local→GCP swaps are a different Agent Card URL, not different agent code. There is no `BridgeClient.collect()` abstraction to maintain.

### 2. The Bridge expresses **waiting** as `input-required` (durable, zero-compute pause) — not a prolonged `WORKING`

When a collection parks to await an external event (a party turn, a clock alarm, an HITL decision), the Bridge's A2A task returns **`input-required`** (or `auth-required` where a credential is the blocker), **not** an indefinite `WORKING` hold.

- On `input-required`/`auth-required`, `RemoteA2aAgent` synthesizes a **mock `LongRunningFunctionTool` call** locally (`remote_a2a_agent.py` `_add_mock_function_call`). The caller's invocation **ends** with zero compute; the peer `task_id` + `context_id` persist in the event's `custom_metadata`, riding the `SessionService` backend (InMemory local / Vertex deploy).
- Resume is native: a later `FunctionResponse` triggers `_create_a2a_request_for_user_function_response`, which re-sends to the **same `task_id`/`context_id`**. This is the *same* durability substrate ADR-0001/0008 already bet on for HITL (`LongRunningFunctionTool` + id-matched `FunctionResponse`) — now reused for the caller↔Bridge edge for free.
- **Semantic note (deliberate):** `input-required` here means "durably parked; resume to continue," and the input may come from a *third party*, not the caller — the caller's resume is often an empty ack ("check again") rather than new data. We accept this overload of `input-required` because it is the only state that unlocks the native zero-compute pause. See risks.

### 3. In-connection **progress** is standard `TaskStatusUpdateEvent.status.message`

While a caller is connected, the Bridge emits progress as standard **`TaskStatusUpdateEvent`s carrying a non-empty `status.message`** over `message/stream`. `RemoteA2aAgent` consumes these and renders `submitted`/`working` states as ADK *thought* events (`part.thought = True`) — progress, never promoted to the final answer.

- **a2a-sdk 1.x gotcha (must honor):** the SDK carries an always-present *empty* proto `Message`; ADK collapses it to `None` (`_compat.normalize_message`) and only surfaces a status update when a **real, non-empty** `Message` is attached. A status update with no parts is silently dropped — the mock and real Bridge must attach real parts.
- This is the *connected* progress channel only. It is bounded by the client `timeout` (`DEFAULT_TIMEOUT = 600.0`s) and does not survive disconnects — it does not replace (2) or the weeks-scale wakeup.

### 4. Weeks-scale wakeup stays ADR-0008's push; poll/`resubscribe` are the interim

The three mechanisms compose and each keeps its ADR-0008 role:

- **Connected, seconds–minutes:** streamed status updates (§3).
- **Parked, hours–weeks, zero compute:** `input-required` pause + resume (§2), woken by ADR-0008's `PushNotificationConfig` (Phase 3) — or, interim, the servicer polls `tasks/get` / re-attaches with `tasks/resubscribe`.
- **Terminal:** the `ExchangeTurn` artifact on `completed`, unchanged.

### 5. Integration-extension mode is chosen explicitly

`RemoteA2aAgent` has a legacy path and a newer `_NEW_A2A_ADK_INTEGRATION_EXTENSION` path (`use_legacy` flag, `_handle_a2a_response` vs `_handle_a2a_response_v2`). Sprint 1 picks one deliberately and pins it; the choice is recorded in the seam suite so mock and real behave identically. Default to `use_legacy=True` until the new extension is validated against our mock.

## Rationale

- **§1 is a direct application of ADR-0001.** For agent→agent A2A, `RemoteA2aAgent` *is* the platform-native construct; the hand-rolled consumer is exactly the "custom layer without a recorded justification" the principle forbids. The justification that existed — a hermetic, minimal tracer bullet — applies to M0 only, not to the target.
- **§2 is the only path to weeks-scale for the caller.** ADR-0008 makes the Bridge task durable and zero-compute-when-idle; a consumer that blocks in a poll loop throws that away. Expressing waits as `input-required` is what lets the caller inherit the same native pause the Bridge already uses internally for HITL — one durability model end to end, no second one to build.
- **§3/§4 use the standard mechanisms for each timescale**, consistent with ADR-0008 §3 (push is the weeks-scale answer; poll/resubscribe interim; streams don't survive weeks). Status updates add the missing *connected* progress channel without inventing anything.
- **The seam survives without the port.** The reusability property was never "there is a `collect()` method"; it was "the agent doesn't change when the backend does." Swapping the Agent Card URL delivers that with less code.

## Consequences / risks

- **`RemoteA2aAgent` is `@a2a_experimental`.** It is decorated experimental in ADK 2.7.0. This lands squarely under ADR-0001's SDK-risk item: pin `google-adk`, track the `[EXPERIMENTAL]` surface, and cover the consumer in the shared seam suite so a breaking change is caught immediately.
- **Overloading `input-required` is a real semantic bet.** A2A conventionally reads `input-required` as "the *caller* must supply input." We use it for "parked, awaiting a third party." Consumers built by others may render it as a prompt-the-user state. Mitigation: document the convention on the Agent Card / skill description, and keep the resume tolerant of an empty ack. If this proves confusing for external A2A callers, revisit (a future A2A `working`-with-push variant, or the new integration extension, may express "parked but not caller-blocked" more precisely).
- **The `BridgeClient` port + `A2ABridgeClient` become tracer-bullet-only** — and were **subsequently removed** (see Amendment). They were no longer the target consumer; Sprint 1 grows against `RemoteA2aAgent`, not behind the port.
- **Contract redesign is now Sprint-1 scope.** The mock Bridge and real Bridge must emit `input-required` on park + `TaskStatusUpdateEvent` with non-empty `status.message` on progress, and support resume to the same `task_id`. The M0 mock (permanent contract double per CLAUDE.md) grows these behaviors; parity stays terminal-outcome, not ledger-identical.
- **Empty-message drop is a silent failure mode.** A status update with no parts vanishes with no error. The seam suite must assert a non-empty `status.message` round-trips and surfaces as a thought event.
- **`input-required` was treated as a failure by the removed port.** `A2ABridgeClient` raised `BridgeParkedError` on `INPUT_REQUIRED`/`AUTH_REQUIRED` (correct for M0's no-resume poll loop). `RemoteA2aAgent` inverts this natively — a park becomes a `LongRunningFunctionTool` pause — so with the port gone there is no failure guard to flip.

## Alternatives considered

- **Keep the hand-rolled `BridgeClient` port + poll loop (M0 status quo).** Rejected as the target: blocking-only (no weeks-scale, no zero-compute), no progress channel, and re-implements ADK-native machinery against ADR-0001. Retained for M0 only.
- **Keep the port but add streaming status updates + a hand-rolled durable pause.** Rejected: adds progress but still hand-rolls pause/resume that `RemoteA2aAgent` + `LongRunningFunctionTool` already provide — a second durability model to build and maintain alongside the Bridge's own.
- **Express long waits as a prolonged `WORKING` hold and let the client stream/poll.** Rejected: `working` never triggers the native zero-compute pause; the caller sits on a held connection bounded by `timeout` (600s) and cannot span weeks.
- **Phase it (ship M0 on the port, adopt native in Sprint 1) without an ADR now.** Considered; rejected in favor of recording the target decision now so the Sprint-1 contract redesign (input-required + status updates) is designed in, not retrofitted. The phasing still happens — this ADR is the target, M0 is the interim (see Note).

## Note

This ADR governs the **consumer side** (how our agents call the Bridge) and the **wire vocabulary** the Bridge must emit to make the native consumer effective. It does not change ADR-0001's runtime/transport choices or ADR-0008's lifecycle policy — it *uses* them: `RemoteA2aAgent` (native ADK), `input-required`+resume (native `LongRunningFunctionTool` durability), `TaskStatusUpdateEvent` and `PushNotificationConfig` (standard A2A). See `wiki/bridge-a2a-edge.md`, `wiki/bridge-long-running.md`.

## Amendment (2026-08-15) — port removed; address agent consumes the Bridge as a sub-agent

The original decision phased the switch (keep the M0 port as a permanent hermetic double, adopt the native consumer from Sprint 1). Once the wire contract was validated, the port was **removed outright** rather than retained:

- **Deleted:** `bridge_client/port.py` (`BridgeClient`, `BridgeClientError`, `BridgeParkedError`, `BridgeTimeoutError`) and `bridge_client/a2a_client.py` (`A2ABridgeClient`), plus their tests (`test_bridge_client.py`, the port-guard "Test C" in `test_native_consumer.py`). The reusable A2A wire helpers (`request_to_message`, `task_to_exchange_turn`) moved to `bridge_client/wire.py`; the raw-client wire-contract test (Test A) still exercises them.
- **Address agent wiring:** `build_address_agent(bridge_card_url)` now attaches the `RemoteA2aAgent` (`document_bridge`) as a **`sub_agent`**; the model delegates via ADK's injected `transfer_to_agent`, and the Bridge relays its `ExchangeTurn` back as the turn output. There is no `FunctionTool`/`collect()` wrapper.
- **Open consequence — structured `CollectRequest` on the send path.** Under transfer, the consumer forwards conversation content, not a JSON `CollectRequest` DataPart, so the structured outbound request no longer travels on the agent's send. The mock Bridge is content-agnostic, so the M0 round-trip still passes; carrying `CollectRequest` (and post-processing the returned ledger for the `is_satisfied` gate — which needs control to return to the address agent, e.g. via `AgentTool` or a follow-up root turn) is **Sprint-1 work**.
- **Unchanged:** the wire vocabulary (§2–§4), `use_legacy=True` pin (§5), and the experimental-surface risk all still hold.
