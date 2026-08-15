# S1-2 — Control-return wiring (transfer → `AgentTool`) + structured `CollectRequest` on the send path

## Context

PLAN.md Sprint-1 bullet **S1-2**. Today the address `LlmAgent` consumes the Bridge as a
`RemoteA2aAgent` **sub-agent** (`sub_agents=[...]`), delegated via ADK's injected
`transfer_to_agent` (landed in S1-1 / adr-0009 amendment). Transfer has two open consequences this
task closes:

1. **Control never returns.** A `RemoteA2aAgent` issues no transfer-back, so the turn *ends* at the
   sub-agent and the address agent can never post-process the returned `ExchangeTurn` (needed for the
   `is_satisfied` gate in S1-3 and the Collect loop in S1-4). Fix: wire the same `RemoteA2aAgent`
   as an **`AgentTool`** (call-and-return) instead of a transfer sub-agent.
2. **The typed request left the send path.** Transfer forwards *conversation content* (a text part),
   not the structured `CollectRequest` JSON DataPart. Fix: restore `CollectRequest` as a single JSON
   DataPart on the outbound `message/send`.

The card-URL swap (mock→real / local→GCP is a different Agent Card URL, not different agent code)
is **unchanged**. Cover both changes in the seam suite.

References: `docs/decisions/adr-0009-native-a2a-consumer.md` (Amendment, "Open consequence"),
`wiki/bridge-a2a-consumer.md` ("Wiring into the caller: transfer vs. call-and-return"),
`agents/src/bridge_client/wire.py` (canonical wire encoding), `agents/src/agents/address/agent.py`.

## Verified facts (read from the installed SDKs — `google-adk` 2.7.0, `a2a-sdk` 1.1.x)

- **`AgentTool` (`google/adk/tools/agent_tool.py`) drops non-text result parts.** `run_async`
  builds its return value from `_part_to_text(p)` over the **last event's** content parts only;
  `_part_to_text` handles `part.text` / code-exec / executable-code — **not `inline_data`**. The
  Bridge's completed `ExchangeTurn` arrives as an `inline_data` DataPart (see next bullet), so a
  *vanilla* `AgentTool(RemoteA2aAgent)` returns an **empty string** — the `ExchangeTurn` is lost.
  This is why a plain `AgentTool` is insufficient; we need a subclass that scans all events and
  extracts the DataPart.
- **`AgentTool` runs the wrapped agent in a fresh `InMemorySessionService` + new session per call**
  (`run_async` lines ~263-288). Consequence: native `LongRunningFunctionTool` park/resume that
  relies on the peer `task_id`/`context_id` persisting on the *caller* session **does not survive
  across `AgentTool` invocations**. Irrelevant to S1-2 (single call-and-return, `park=False`); it is
  an explicit **S1-4/S1-5 concern** — note it, don't solve it here.
- **`RemoteA2aAgent._run_async_impl` early-returns on empty parts.** It calls
  `_construct_message_parts_from_session(ctx)`; if that yields **no** parts it logs a warning, emits
  an empty event, and **returns before the request interceptors run** (lines ~974-988). So the child
  session must contain at least one convertible part (a text part is fine) for the interceptor to
  fire.
- **Public send-path hook exists:** `A2aRemoteAgentConfig(request_interceptors=[RequestInterceptor(
  before_request=...)])` (`google/adk/a2a/agent/config.py`, `.../agent/utils.py`). `before_request`
  gets `(ctx, a2a_request: A2AMessage, params) -> (A2AMessage | Event, params)` and its returned
  message is what gets sent (`remote_a2a_agent.py` lines ~1000-1009). This runs for **both** the
  fresh send **and** the resume request.
- **Resume detection:** the resume request is built by
  `_create_a2a_request_for_user_function_response` and has `a2a_request.task_id` **set**
  (`remote_a2a_agent.py` lines ~660-664); a fresh send has no `task_id`. Guard the interceptor on
  this so it only rewrites the fresh send (protects the S1-4 park/resume path).
- **Canonical wire encoding already exists:** `bridge_client/wire.request_to_message(CollectRequest)`
  → a single JSON DataPart `Message` (`media_type="application/json"`, `role=ROLE_USER`). This is the
  exact shape Test A in `test_native_consumer.py` already asserts — **reuse it**, do not hand-roll a
  new encoding.
- **Inbound extraction already exists (test-only):** `tests/support/a2a_helpers.extract_exchange_turn`
  scans ADK events for an `inline_data` blob tagged `<a2a_datapart_json>…</a2a_datapart_json>` and
  JSON-parses the `ExchangeTurn`. Promote this to production code so the tool can reuse it.
- `bridge_client/` may import only `contract` + stdlib + `a2a-sdk` + `httpx` + `google-adk`, and
  **must never import `agents.*`** (CLAUDE.md invariant). `AgentTool`, `Runner`, `contract`,
  `wire`, `httpx` are all allowed there.
- Tests resolve `agents` / `contract` / `bridge_client` / `tests.support` via the editable install
  (`_editable_impl_*.pth`); run from `agents/`.

## Approach

### 1. Send path — inject the structured `CollectRequest` DataPart (public interceptor)
`agents/src/bridge_client/remote_consumer.py`

- Add a factory that builds a `RequestInterceptor` whose `before_request` **replaces** the outbound
  message parts with the canonical `CollectRequest` DataPart:
  - If `a2a_request.task_id` is truthy (resume — see verified facts) → return `(a2a_request, params)`
    unchanged. (Belt-and-suspenders for S1-4; a no-op in S1-2's single-shot path.)
  - Else build `msg = request_to_message(collect_request)` (reuse `wire.py`), then **copy the live
    `context_id`/`message_id` conventions**: set `msg.context_id = a2a_request.context_id` when the
    remote is stateful (preserves an ongoing exchange), and keep the fresh `message_id`. Return
    `(msg, params)`.
  - a2a-sdk 1.x proto note: build/read with kwargs / `.field` / `.HasField`, never `.model_dump()`
    (see `wire.py` header). For the `task_id` guard use `a2a_request.HasField("task_id")` if it is a
    proto optional, else a truthiness check — confirm against the installed 1.1.x type.
- Extend `build_bridge_remote_agent(...)` with an optional `collect_request: CollectRequest | None =
  None`. When provided, construct `A2aRemoteAgentConfig(request_interceptors=[<the interceptor>])`
  and pass it as `config=` to `RemoteA2aAgent`. When `None`, behavior is **unchanged** (no config) —
  this keeps S1-1's `test_native_consumer.py` and any existing callers green.
- Keep `use_legacy=True` (adr-0009 §5 pin) and the `httpx_client` passthrough as today. Note:
  `RemoteA2aAgent.__init__` appends the new-integration interceptor to `config.request_interceptors`
  only when `use_legacy=False`; with `use_legacy=True` our interceptor is the only one — fine.

### 2. Control return — `BridgeAgentTool` (call-and-return that surfaces the `ExchangeTurn`)
`agents/src/bridge_client/bridge_tool.py` (new), exported from `bridge_client/__init__.py`

- Promote the inbound extractor to production: add `extract_exchange_turn(events) -> dict | None` to
  `bridge_client/wire.py` (identical logic to `tests/support/a2a_helpers.extract_exchange_turn`:
  scan `event.content.parts`, find the `inline_data` blob, strip the `<a2a_datapart_json>` tags if
  present, `json.loads`, return the dict whose `status.ledger` is non-empty). Re-point
  `tests/support/a2a_helpers.py` to re-export it (keep the import path stable for existing tests).
- `class BridgeAgentTool(AgentTool)` overriding `run_async` so it:
  1. Reuses the parent's Runner-setup boilerplate (fresh `Runner` with `ForwardingArtifactService`,
     `InMemorySessionService`, session seeded from filtered `tool_context.state`), and feeds a
     **non-empty text** `new_message` (e.g. `"Collect the requested proof."`) — content value is
     irrelevant because the §1 interceptor overwrites the parts, but it must be non-empty so
     `RemoteA2aAgent` does not early-return (verified fact).
  2. Accumulates **all** yielded events (not just `last_content`) and forwards `state_delta` to the
     parent (as the parent does).
  3. After the loop, calls `extract_exchange_turn(events)`; returns the `ExchangeTurn` **dict** if
     found (JSON-serializable → valid ADK tool result), else falls back to the parent's
     text/error behavior. Optionally validate via `contract.ExchangeTurn.model_validate(...)` and
     return `.model_dump(mode="json")` for a guaranteed-clean shape.
  4. Sets `skip_summarization=True` by default (the structured dict is the answer; no LLM re-narration
     of the ledger) and calls `runner.close()` in a `finally`.
- Rationale for a subclass over a vanilla `AgentTool`: the vanilla tool drops the `inline_data`
  DataPart (verified fact), so it would return `""`. The subclass is the smallest construct that
  keeps the native `RemoteA2aAgent` underneath (streaming/pause machinery intact) while returning the
  typed payload. **Gotcha:** this copies `AgentTool.run_async`'s Runner boilerplate — it is coupled
  to ADK internals; the seam suite (below) is what catches drift on an SDK bump (adr-0001 SDK-risk).
  - *Lighter alternative, if the subclass proves brittle:* pass a custom `a2a_part_converter` in
    `A2aRemoteAgentConfig` that renders an inbound DataPart as a genai **text** part (JSON string);
    then a vanilla `AgentTool(bridge, skip_summarization=True)` returns it as text. Rejected as
    primary because `AgentTool` still only reads the **last** event's content, which is fragile if a
    trailing empty status event follows the artifact. Document the choice made.

### 3. Address agent wiring — transfer → tool
`agents/src/agents/address/agent.py`

- In `build_address_agent`, build the consumer with the CollectRequest baked in:
  `bridge = build_bridge_remote_agent(card_url, name=BRIDGE_SUBAGENT_NAME,
  collect_request=CollectRequest(party=PARTY, skill=SKILL))`, then wire it as a **tool**, not a
  sub-agent: `tools=[BridgeAgentTool(bridge)]`, and **remove** `sub_agents=[bridge]`.
- Update `INSTRUCTION`: replace "delegate/transfer to the `document_bridge` sub-agent" with "call the
  `document_bridge` **tool** to collect the address-proof document for `jordan-lee`; when it returns
  the collected `ExchangeTurn`, present the document id and its structured fields." Rename or keep
  `BRIDGE_SUBAGENT_NAME`; if renamed to `BRIDGE_TOOL_NAME`, update `test_address_agent.py` and any
  imports. The tool name equals the wrapped agent name (`AgentTool.__init__` sets
  `name=agent.name`), so it stays `document_bridge`.
- Keep `PARTY = "jordan-lee"`, `SKILL = "address-proof"`, `output_key`, `_default_card_url`,
  `run_once`, and the module-level `root_agent = build_address_agent()` unchanged (build stays
  side-effect-free — no network until a turn runs).

### 4. Scripted test model — tool call instead of transfer
`agents/tests/support/adk_stub.py`

- Add `ScriptedToolCallModel(BaseLlm)` (mirror `ScriptedTransferModel`): call #1 emits a
  `function_call` to `document_bridge` with args `{}` (or `{"request": "..."}` — args are ignored;
  the interceptor supplies the CollectRequest); later calls emit fixed final text. Keep
  `ScriptedTransferModel` if any other test still needs it; otherwise the round-trip test switches
  to the new stub.
- Note: with `skip_summarization=True` on the tool, the model may not be re-invoked after the tool
  returns; the scripted stub's later-call branch is a safety net. Assert on the **tool result** /
  event stream, not on model re-narration.

### 5. Tests — seam coverage
`agents/tests/test_control_return.py` (new) and updates to `test_round_trip.py` /
`test_address_agent.py`

- **Send-path DataPart (live):** make the mock capture the received request so the test can assert a
  structured `CollectRequest` arrived (not free text). Minimal change to the mock:
  `MockBridgeExecutor` records the first-turn inbound message parts (e.g. `self.last_request_data`)
  from `context.message`; expose via the app or a module-level capture. Then a live test
  (`LiveMockServer`) drives the address agent (or `BridgeAgentTool` directly) once and asserts the
  captured part is a **DataPart** decoding to `{"party": "jordan-lee", "skill": "address-proof"}`.
  - *If mutating the mock is undesirable:* add a unit test that runs the §1 interceptor directly —
    feed it a fresh `A2AMessage` (no `task_id`) and assert the returned message carries exactly one
    JSON DataPart equal to `CollectRequest(...).model_dump(mode="json")`; feed it a message **with**
    `task_id` and assert pass-through unchanged. This locks the send contract without touching the
    mock. Do at least this unit test regardless.
- **Control-return (live):** drive the address agent with `ScriptedToolCallModel` against
  `LiveMockServer(hold_seconds=0.2, park=False)`; assert the `BridgeAgentTool` result is the
  gov-id-clean `ExchangeTurn` dict (`status.ledger[0].id == "gov-id-clean"`, `doctype == "gov-id"`,
  `disposition == "accepted"`, `key_fields` match `wiki/evals/address/expected.json` — mirror the
  existing assertions in `test_round_trip.py`). The key assertion vs. transfer: **control returned**
  — verify the tool `function_response` event exists in the caller's stream (i.e., the turn did not
  end inside the sub-agent).
- **Wiring shape (hermetic):** update `test_address_agent.py`: the Bridge is now wired as a **tool**
  (`len(agent.tools) == 1`, tool is a `BridgeAgentTool` wrapping a `RemoteA2aAgent` named
  `document_bridge`) and `agent.sub_agents` is empty — the inverse of the current assertions.
- **Update `test_round_trip.py`:** it currently asserts the transfer path via `extract_exchange_turn`
  over the raw event stream. Either retarget it to the tool path (scripted tool-call model, assert
  the relayed `ExchangeTurn`) or fold it into `test_control_return.py`. Keep exactly one live
  end-to-end round-trip green.
- **Do not break S1-1:** `test_native_consumer.py` (Tests A/B) uses `build_bridge_remote_agent`
  **without** `collect_request`, so it must keep passing unchanged (the new param defaults to `None`
  = no interceptor).

### 6. Docs + tracker
- `docs/decisions/adr-0009-native-a2a-consumer.md`: the Amendment's "Open consequence — structured
  `CollectRequest` on the send path" is now **closed** — add a one-line note (AgentTool + interceptor,
  landed S1-2) without contradicting the Amendment.
- `wiki/bridge-a2a-consumer.md`: flip the "Sprint 1 (remaining)" status line — transfer→`AgentTool`
  and the `CollectRequest` DataPart are now landed; multi-turn loop remains (S1-4).
- `agents/README.md`: if it describes transfer/sub-agent wiring, update to the tool wiring.
- `PLAN.md`: mark **S1-2** `- [x]` with `_(done <date>; Plan:
  /home/boris/working/.claude/plans/S1-2-control-return-agenttool.md)_`.

## Gotchas (do not rediscover)

- **Empty-parts early return:** the child `new_message` must be non-empty text or `RemoteA2aAgent`
  returns before the interceptor runs — the CollectRequest DataPart would never be sent.
- **Interceptor runs on resume too:** guard on `task_id` or the S1-4 park/resume will send a
  CollectRequest instead of the resume ack.
- **`AgentTool` returns last-content text only:** scan **all** events for the `ExchangeTurn`
  DataPart, don't trust `last_content`.
- **Fresh child session per tool call:** cross-call native park/resume won't survive `AgentTool`;
  that's an S1-4/S1-5 problem, out of scope here (`park=False` throughout S1-2).
- **proto types:** `a2a-sdk` 1.x messages are protobuf — kwargs / `.field` / `.HasField`, never
  `.model_dump()` on A2A types (contract Pydantic models still use `model_dump`).
- **httpx cleanup:** if `BridgeAgentTool` lets `RemoteA2aAgent` create its own client, ensure
  `runner.close()` runs (finally) to avoid dangling-client ResourceWarnings in tests.
- **`bridge_client/` import rule:** the new `bridge_tool.py` may import `google-adk` + `contract` +
  `wire` only — never `agents.*`.

## Verification

- `uv run pytest` — all green: new `test_control_return.py`, updated `test_round_trip.py` /
  `test_address_agent.py`, and **unchanged** `test_native_consumer.py` (A/B), `test_mock_bridge.py`,
  `test_contract.py`, `test_scaffold.py`. (Fallback `.venv/bin/pytest` if `uv` unavailable.)
- `uv run ruff check` — clean.
- Manual (optional): `MOCK_BRIDGE_HOLD_SECONDS=2 uv run python -m agents.mock_bridge` in one
  terminal; `uv run python -m agents.address` in another — confirm the agent calls the tool, control
  returns, and the gov-id-clean id + fields render.

## Acceptance criteria

1. The address agent consumes the Bridge as an **`AgentTool`** (call-and-return), not a transfer
   sub-agent; control returns to the address agent with the `ExchangeTurn` available as the tool
   result (structured dict).
2. The outbound `message/send` carries the structured **`CollectRequest`** as a single JSON DataPart
   (`{"party":"jordan-lee","skill":"address-proof"}`), asserted in the seam suite (interceptor unit
   test at minimum; live capture preferred).
3. The card-URL swap point is unchanged (`build_bridge_remote_agent(card_url, ...)`; mock→real /
   local→GCP is still just a different card URL).
4. S1-1 coverage (`test_native_consumer.py`) stays green unchanged; full suite + ruff green.
5. adr-0009 Amendment "open consequence" is recorded as closed; `wiki/bridge-a2a-consumer.md` and
   PLAN.md updated.

## Out of scope (later Sprint-1 bullets)

`is_satisfied` completeness gate (S1-3); multi-turn Collect loop with one durable task/context across
rounds (S1-4); mock multi-turn document arrivals / chase / distinct-issuer bills (S1-5); cross-call
park/resume durability under `AgentTool`; `PushNotificationConfig` weeks-scale wakeup (Phase 3).
