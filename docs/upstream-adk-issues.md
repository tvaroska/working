# Upstream ADK issues — drafts

Custom, non-canonical code we carry only because a platform-native path is missing
or broken. ADR-0001 requires a bespoke layer to have a recorded justification;
this file is that record **plus** the ready-to-file upstream reports so each
workaround is an explicitly-tracked stopgap, not a permanent local dialect. When a
report is filed, add its URL next to the entry and to ADR-0012's revisit triggers.

Environment for all reports: `google-adk == 2.7.0`, `a2a-sdk` 1.1.x, Python 3.12.

---

## Issue 1 — `RemoteA2aAgent` resume detection breaks inside a `Workflow`

- **Status:** draft (not yet filed)
- **Local workaround:** `agents/src/bridge_client/remote_consumer.py`
  (`_pending_resume_target` + the resume-stamping branch of the send-path
  `RequestInterceptor`)
- **Tracked by:** ADR-0012 revisit trigger (b); docs/lessons-learned.md A12

### Summary

`RemoteA2aAgent` detects the resume of a parked (`input-required`) A2A task only
when the resolved `FunctionResponse` is the **last** event on the session. Running
the agent as a node inside a `google.adk.workflow.Workflow` breaks that assumption:
the graph orchestrator appends a workflow-start/orchestration event **after** the
user `FunctionResponse` and before the collect node re-runs. As a result the remote
agent never sets the parked `task_id`, re-sends a *fresh* request, and the peer
opens (and re-parks) a **new** task instead of resuming the existing one.

### Where

`google/adk/agents/remote_a2a_agent.py` —
`_create_a2a_request_for_user_function_response` keys off
`ctx.session.events[-1].author == "user"`.

### Steps to reproduce

1. Build a `Workflow` conditional cycle whose collect node is a `RemoteA2aAgent`
   pointed at an A2A peer that parks (`INPUT_REQUIRED`) on the first turn:
   `collect -> gate`, `gate --[again]--> collect`, `gate --[done]--> present`.
2. Run one turn; the leg parks on a `LongRunningFunctionTool` call.
3. Resume by feeding the matching `FunctionResponse` to `runner.run_async`.
4. Observe the outbound `message/send`: `task_id` is empty, so the peer starts a
   new task rather than resuming the parked one.

### Expected vs. actual

- **Expected:** the resume targets the parked `task_id`/`context_id` regardless of
  whether an orchestration event was appended after the `FunctionResponse`.
- **Actual:** resume is detected only when the `FunctionResponse` is literally the
  last session event, so any orchestrator (Workflow, or any composition that
  appends after the response) defeats it.

### Suggested fix

Detect the pending resume by scanning for the most-recent user `FunctionResponse`
that has **no event authored by this agent after it**, rather than requiring it to
be the last event outright — then recover the parked `task_id`/`context_id` from
the matching function-call event's `custom_metadata` (`a2a:task_id` /
`a2a:context_id`). This is exactly what our `_pending_resume_target` does; folding
it into `RemoteA2aAgent` would let us delete the workaround.

---

## Issue 2 — no supported way to decode an A2A `DataPart` from an ADK event stream

- **Status:** draft (not yet filed)
- **Local workaround:** `agents/src/bridge_client/wire.py`
  (`extract_exchange_turn` — string-splits `<a2a_datapart_json>…</a2a_datapart_json>`
  out of an `inline_data` blob and JSON-parses it)
- **Tracked by:** this file (add an ADR-0012 revisit trigger when filed)

### Summary

When a `RemoteA2aAgent` relays a peer's structured A2A `DataPart`
(`media_type=application/json`) into the ADK event stream,
`convert_a2a_part_to_genai_part` wraps the JSON as an `inline_data` blob delimited
by literal `<a2a_datapart_json>` / `</a2a_datapart_json>` tags. A downstream graph
node (e.g. a deterministic gate) sees only ADK **events**, not the raw `a2a.Task`,
so it cannot use the canonical decoder (`a2a.helpers.proto_helpers.get_data_parts`,
which we use on the raw-task path in `task_to_exchange_turn`). The only way to
recover the structured payload from a node is to string-match those wrapper tags —
brittle against any change to the delimiter format.

### Where

`google/adk/a2a/converters/event_converter.py` — `convert_a2a_part_to_genai_part`
(the `<a2a_datapart_json>` wrapping).

### Ask

A supported, documented helper to decode an A2A data part back out of a
`genai.types.Part` / ADK event — the inverse of `convert_a2a_part_to_genai_part` —
so consumers don't depend on the private wrapper-tag string format. Alternatively,
surface relayed A2A data parts as structured parts rather than an opaque
tag-wrapped `inline_data` blob.

### Impact if unaddressed

Any ADK agent that consumes another agent's structured (non-text) A2A output from
inside a graph must re-implement this string-parsing and will silently break if the
wrapper format changes.
