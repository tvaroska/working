# ADR-0012 — Experimental-surface register (ADK 2.7.0 surfaces + spike gates)

- **Status:** Accepted
- **Date:** 2026-08-15
- **Ratified at:** S0.8 (stack + open-decision sign-off gate)
- **Context:** `docs/decisions/adr-0001-stack.md` (SDK-risk + pin discipline), `docs/decisions/adr-0009-native-a2a-consumer.md`, `docs/decisions/adr-0010-durable-consumer-construct.md`, `docs/lessons-learned.md` C5; installed `google-adk == 2.7.0`, `a2a-sdk` 1.1.x.

## Context

ADR-0001 fixes the governing principle: **prefer the platform-native construct over bespoke plumbing, every time.** For the A2A Document Bridge, that principle commits the build to three ADK surfaces carrying `[EXPERIMENTAL]` or `@a2a_experimental` decorators in the installed 2.7.0 release:

1. **`RemoteA2aAgent`** (`@a2a_experimental`) — the native agent→agent A2A consumer (ADR-0009).
2. **`ResumabilityConfig(is_resumable=True)`** (`@experimental`) — the durable pause/resume configuration for long-running HITL (ADR-0010).
3. The **new A2A integration extension path** (`_NEW_A2A_ADK_INTEGRATION_EXTENSION`, `use_legacy=False`) — an alternative wiring inside `RemoteA2aAgent` not yet validated against our contract.

Additionally, the **durable consumer construct** (ADR-0010, S1-6) targeted `google.adk.workflow.Workflow` (a *public, not experimental* graph primitive) as the host-orchestrated Collect loop, gated by **two spike gates**:

1. Can a `RemoteA2aAgent` (a non-`LlmAgent` `BaseAgent`) be a graph **node**? Only `@node`, `FunctionNode`, and `LlmAgent`-as-node are confirmed in 2.7.0 documentation.
2. Does an `INPUT_REQUIRED` pause **propagate and resume cleanly inside a `Workflow`**? This is verified inside `LoopAgent` (deprecated), not yet inside `Workflow`.

**Resolved at S1-6:** both gates pass on `Workflow`; the durable Collect loop **ships as a `Workflow` conditional cycle** — the deprecated `LoopAgent` was **not** taken. (An earlier S1-6 attempt fell back to `LoopAgent` on a *misdiagnosis* — that a `Workflow` loop-back edge cannot re-enter a completed node; this was empirically refuted, see the resolved spike-gate section below.) The genuine `Workflow`-specific obstacle was narrower — `RemoteA2aAgent`'s resume detection is incompatible with the graph's event ordering — and is handled by our send-path interceptor. No deprecation risk burdens this path.

This ADR establishes the **canonical register** of these experimental surfaces and spike gates, recording what is pinned, what mode is selected, what validation status each surface holds, and how we track them as the SDK evolves.

## Decision

### The experimental-surface register

| Surface | Decorator (ADK 2.7.0) | Our pin / mode | Validation status | Source |
|---|---|---|---|---|
| `RemoteA2aAgent` (native Bridge consumer) | `@a2a_experimental` | `google-adk >=2.7.0,<3` pinned; mode `use_legacy=True` until the new integration extension is validated against the mock | Exercised by seam suite / native-consumer tests (S1-1); mode not yet flipped | `adr-0009` §1/§5, C5 |
| `ResumabilityConfig(is_resumable=True)` | `@experimental` | `google-adk >=2.7.0,<3` pinned; enable only on the durable path (S1-6) | **Seam-covered (S1-6):** exercised by `tests/test_durable_graph.py` — a parked leg on `DatabaseSessionService` + `DatabaseTaskStore` survives a process restart and resumes to the same state (lives on `App`, not a bare Runner) | `adr-0010` §4, C5 |
| `_NEW_A2A_ADK_INTEGRATION_EXTENSION` path (`use_legacy=False`) | experimental integration path | **Not** adopted; `use_legacy=True` is the pinned default | Deferred until validated | `adr-0009` §5, C5 |

### The `Workflow` spike gates (RESOLVED at S1-6 — shipped on `Workflow`)

`google.adk.workflow.Workflow` itself is **public / not `@experimental`** — it is the documented graph primitive for multi-step agent flows. Two specific capabilities required by the durable Collect loop (ADR-0010, S1-6) were unverified in our context and were spiked at S1-6:

1. **Can a `RemoteA2aAgent` be a graph node? — CONFIRMED.** A `RemoteA2aAgent` (a non-`LlmAgent` `BaseAgent`) runs correctly as a `Workflow` node on a shared session (`BaseAgent` subclasses the workflow `BaseNode`, so it is a node with no adapter); its collected `ExchangeTurn` artifact is persisted to the shared session and read back by the deterministic gate. (Load-bearing detail: the artifact must be emitted with `last_chunk=True` — a `partial` artifact event streams to the caller but is *not* persisted, so the gate can't see it. See `docs/lessons-learned.md` A12.)
2. **Does an `INPUT_REQUIRED` pause propagate and resume cleanly inside a `Workflow`? — CONFIRMED.** The pause/resume *mechanism* (`LongRunningFunctionTool` + `FunctionResponse` on a shared durable session) works, iterates through the conditional loop, and survives a process restart — inside a `Workflow`. The Collect loop is a `Workflow` **conditional cycle** (`collect → gate`, `gate --[again]--> collect`, `gate --[done]--> present`) and the loop-back edge **does** re-enter and re-run the completed collect node: the graph validator (`workflow.utils._graph_validation`) *requires* loop-back edges to be conditional (routed), and the scheduler re-runs a re-triggered COMPLETED node with a fresh `NodeState` (`workflow._workflow._process_triggers`, which skips a node only while it is RUNNING or WAITING-with-interrupts).

**Misdiagnosis, corrected.** An earlier S1-6 attempt fell back to the deprecated `LoopAgent`, claiming the `Workflow` scheduler *fast-forwards any node that already COMPLETED in the current invocation* (citing `workflow.utils._replay_interceptor.check_interception` Case 1), so the not-done→collect edge could never iterate. This was **empirically refuted**: `check_interception` Case 1 is scoped to **dynamic** nodes (`ctx.run_node()`), not static-graph loop-back edges; a minimal spike (a routed self-loop counting iterations) re-runs the completed node every round; and the shipped loop iterates in `agents/tests/test_durable_graph.py`. The real `Workflow`-specific obstacle was narrower: `RemoteA2aAgent`'s resume detection (`_create_a2a_request_for_user_function_response`) requires the resolved `FunctionResponse` to be the *last* session event, which the graph orchestrator breaks by appending a workflow event after it — so the remote agent never set the parked `task_id` and re-parked. **Resolution:** the send-path `RequestInterceptor` (`bridge_client.remote_consumer`) re-detects the pending resume (independent of event ordering) and stamps the parked A2A `task_id`/`context_id`, resuming the same task. The loop **ships on `Workflow`** (`agents/address/graph.py`); `LoopAgent` was not taken and its deprecation risk does not apply.

**Note:** `Workflow` itself is **not listed in the experimental-surface register** — it is a public, non-experimental API. Its two spike gates are now resolved. The remaining `Workflow`-specific dependency is our own send-path interceptor adapter (seam-covered by `tests/test_durable_graph.py` / `tests/test_collect_loop.py`), not an SDK experimental surface.

## How we track it (the pin discipline)

1. **SDK versions pinned by ADR-0001** (`google-adk >=2.7.0,<3`), guarded in CI by `agents/tests/test_scaffold.py` (`test_adk_version_in_range`, `test_a2a_sdk_present`).
2. **Every experimental surface is covered in the shared seam suite** so a breaking SDK change is caught immediately (ADR-0001 SDK-risk item). Mock and real Bridge implementations + their consumers exercise the same experimental surfaces, locking parity.
3. **`use_legacy=True` is the pinned integration mode** until the new extension is validated against the mock. This mode is set explicitly in the consumer wiring and verified by the seam suite to ensure mock↔real parity.
4. **Each surface has an owner and a revisit trigger:**
   - **Owner:** design owner (the role responsible for tracking SDK evolution and validating new surfaces).
   - **Revisit triggers:** (a) validate the new integration extension against the mock before flipping `use_legacy=False`; (b) **`RemoteA2aAgent` resume detection** — the send-path interceptor works around `RemoteA2aAgent` assuming the resolved `FunctionResponse` is the last session event (broken by `Workflow` event ordering); re-audit on any `google-adk` bump in case the SDK fixes resume detection natively (then the workaround can be dropped) or changes the workflow event-ordering contract — drafted for upstream as Issue 1 in `docs/upstream-adk-issues.md`; (c) **A2A `DataPart` decode from an event stream** — `wire.extract_exchange_turn` string-matches ADK's `<a2a_datapart_json>` wrapper because no supported helper decodes a relayed data part from a graph node; re-audit on any `google-adk` bump for a native inverse of `convert_a2a_part_to_genai_part` — drafted for upstream as Issue 2 in `docs/upstream-adk-issues.md`; (d) on any `google-adk` minor bump, re-audit experimental surfaces for breaking changes or graduation to stable.

## Consequences / risks

- **The durable path leans on two experimental surfaces at once** (`RemoteA2aAgent` + `ResumabilityConfig`). A breaking change in either requires immediate mitigation (downgrade, pin tighter, adapt the code). The shared seam suite is the early-warning system — it exercises both surfaces across mock and real, so a failure surfaces before deploy.
- **The spike gates resolved in `Workflow`'s favor (S1-6, realized).** The durable loop ships on the non-deprecated `Workflow`, so no `LoopAgent` deprecation risk burdens this path. The residual `Workflow`-specific risk is our send-path interceptor adapter for `RemoteA2aAgent` resume detection (revisit trigger (b) above) — a small, seam-covered adapter, re-auditable on each SDK bump, not an SDK experimental surface.
- **This register is a living record** (unlike a normal one-shot ADR). As experimental surfaces are validated and graduate to stable, or as new experimental surfaces are adopted, this ADR is updated — explicitly documented here so future edits are legitimate and expected. The update discipline: any experimental-surface addition/removal/mode-flip must (a) update this register table, (b) update the corresponding source ADR (0009/0010/etc.), and (c) ensure the seam suite covers the new state.
- **Integration-extension mode (`use_legacy`) is a toggle, not a version pin.** Flipping `use_legacy=False` requires validating the new path against the mock (S1-1's contract tracer: `input-required` pause → resume → same `task_id`/`context_id`). Until validated, `use_legacy=True` is the pinned default.
- **`Workflow` itself is stable, and our usage is now validated.** The two spike gates (non-`LlmAgent` node, in-`Workflow` pause propagation through a conditional loop) were *our* validation responsibility, not an SDK experimental-decoration concern — both passed. The one gap the spike surfaced ("the API may not support what we need") was not in `Workflow` but in `RemoteA2aAgent`'s resume detection under graph event ordering, closed by the send-path interceptor.

## Cross-references

- **ADR-0001** (SDK pins + SDK-risk tracking) — this register is the concrete list ADR-0001's risk item refers to.
- **ADR-0009** (native consumer + `RemoteA2aAgent`) — §1/§5 adopt the experimental consumer; the integration-extension mode choice is recorded here.
- **ADR-0010** (durable consumer construct) — §4 adopts `ResumabilityConfig`; §2/§5 describe the `Workflow` target + spike gates (§5 Resolution records the `Workflow` outcome).
- **`docs/lessons-learned.md` C5** — the narrative rationale for the pins + the two ADK crux APIs to spike; this ADR is the canonical tabular register of what C5 describes.
- **`PLAN.md` S1-6** — the task that ran the `Workflow` spike gates and committed to `Workflow`.
