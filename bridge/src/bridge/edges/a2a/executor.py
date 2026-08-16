"""Real-Bridge collect executor for the inbound A2A edge (M1.8).

Mirrors the mock's ``MockBridgeExecutor`` assembly (the a2a-sdk emission sequence the
native ``RemoteA2aAgent`` consumer requires) but drives the ledger through **core**:
each arrived document is classified by M1.6 ``classify_document`` and recorded as an
M1.2 leg task; the outbound ``ExchangeTurn`` is the M1.4 projection over those tasks —
real disposition, not the mock's canned fixtures.

Emission sequence (load-bearing — see docs/lessons-learned A11/A12):
- enqueue a ``Task(SUBMITTED)`` **first** (a2a-sdk requires the Task before any
  status-update events);
- ``start_work`` / ``update_status`` carry a **non-empty** ``status.message`` (an empty
  proto ``Message`` collapses to ``None`` and is silently dropped — A11);
- the ``ExchangeTurn`` artifact is emitted ``last_chunk=True`` **even for a partial,
  pre-park collection** (a durable consumer only persists non-partial events — A12);
- park via ``INPUT_REQUIRED`` with a non-empty message, emitting the collected-so-far
  artifact **before** parking; resume detected by a re-sent ``task_id`` populating
  ``context.current_task`` at ``INPUT_REQUIRED``.

Scope (M1.8): this is the inbound edge only. Document intake routing (Path A vs B) is
M1.11; the fulfillment graph (M1.7) is NOT wired here — the arrived documents come from
an injectable :class:`~bridge.edges.a2a.plan.CollectPlan` fixture stand-in. The final
"done" is the consumer's sense-B decision — the edge supplies only ``outstanding``
(advisory) + a ``terminal`` flag; it does **not** compute ``is_satisfied``.

Import discipline: imports ``contract`` + ``a2a`` + core (``aggregate``/``ledger``/
``disposition``/``skills``) + the edge's own ``plan``/``trust`` + the extraction seam
(via the injected engine). Never imports ``agents``.
"""

from __future__ import annotations

import asyncio

from a2a.helpers.proto_helpers import get_data_parts, new_data_part, new_text_message
from a2a.server.agent_execution import AgentExecutor
from a2a.server.tasks import TaskUpdater
from a2a.types import Task, TaskState, TaskStatus
from contract import CollectRequest, Disposition

from bridge.adapters.local.extraction import FixtureDocument
from bridge.adapters.local.skill_registry import LocalSkillRegistry
from bridge.aggregate import create_leg_task, next_ordinal
from bridge.disposition import classify_document
from bridge.ledger import build_exchange_turn, ledger_entry_of, stamp_ledger_entry
from bridge.requirements import (
    SkillExplanations,
    advisory_satisfaction,
    explain_rejection,
    load_explanations,
    propose_requirements,
)
from bridge.seams.extraction import ExtractionSeam
from bridge.skills import DispositionThresholds

from .plan import CollectPlan, plan_for_skill
from .trust import authorize_leg

__all__ = ["BridgeExecutor", "_status_for"]


def _status_for(disposition: Disposition) -> TaskState:
    """Map an exchange-level disposition to the A2A task state (M1.8).

    ``PENDING`` → ``INPUT_REQUIRED`` (park, still collecting); ``ACCEPTED``/``REJECTED``
    → ``COMPLETED`` (a rejected-terminal collection still *completes* the A2A task; the
    ledger carries the rejection).
    """
    if disposition == Disposition.PENDING:
        return TaskState.TASK_STATE_INPUT_REQUIRED
    return TaskState.TASK_STATE_COMPLETED


class BridgeExecutor(AgentExecutor):
    """The real Bridge's inbound collect executor (M1.8).

    Stateful per exchange ``context_id``: keeps a per-context round counter and the list
    of leg tasks minted so far, so :func:`~bridge.ledger.build_exchange_turn` can fold
    the whole exchange on every round. (Wiring this through the real ``TaskStore.list``
    via ``aggregate.tasks_for_context`` is a later refinement — M1.8 keeps it in memory.)
    """

    def __init__(
        self,
        *,
        engine: ExtractionSeam,
        collect_plan: CollectPlan | None = None,
        thresholds: DispositionThresholds | None = None,
        explanations: SkillExplanations | None = None,
        strict: bool = False,
        hold_seconds: float = 0.0,
    ) -> None:
        """Initialize the executor.

        Args:
            engine: The extraction seam driving collect content (fixture engine local).
            collect_plan: An explicit plan override applied to every request regardless
                of skill. When None, the plan is resolved per-request by skill
                (:func:`~bridge.edges.a2a.plan.plan_for_skill`).
            thresholds: Disposition thresholds. Defaults to ``DispositionThresholds()``
                (0.55/0.85 — ADR-0002).
            explanations: Skill explanations for requirements relay (M1.9). When None,
                lazily resolved from the address-proof skill via LocalSkillRegistry.
            strict: Trust boundary mode (A6). Permissive by default.
            hold_seconds: Progress hold before completing (shrinkable for tests; the
                real edge defaults to 0.0 — the mock's ~10s hold was an M0 demonstrator).
        """
        self._engine = engine
        self._collect_plan = collect_plan
        self._thresholds = thresholds or DispositionThresholds()
        self._strict = strict
        self._hold_seconds = hold_seconds

        # Explanations: lazily resolve if None (so direct-executor tests keep working).
        if explanations is None:
            registry = LocalSkillRegistry()
            # Synchronous access via the _skills dict (populated in __init__)
            skill = registry._skills.get("address-proof")
            if skill is not None:
                self._explanations = load_explanations(skill)
            else:
                self._explanations = SkillExplanations()
        else:
            self._explanations = explanations

        # Per-context state.
        self._rounds: dict[str, int] = {}
        self._tasks: dict[str, list[Task]] = {}
        self._party: dict[str, str] = {}
        self._skill: dict[str, str] = {}

        self.last_request_data: dict | None = None
        """Data part of the most recent first-turn inbound message (test introspection)."""
        self.context_ids_seen: list[str] = []
        """Context id of each first-turn inbound message, in arrival order."""

    def _plan_for(self, ctx: str) -> CollectPlan:
        """Resolve the collect plan for a context (explicit override, else per-skill)."""
        if self._collect_plan is not None:
            return self._collect_plan
        return plan_for_skill(self._skill.get(ctx, ""))

    @staticmethod
    def _caller_of(context) -> str | None:
        """Derive the caller identity from the request's ServerCallContext (A6).

        Returns the authenticated user name, else a ``caller`` claim stashed in the
        call-context state (a test hook), else ``None`` (unauthenticated → permissive).
        """
        call_context = getattr(context, "call_context", None)
        if call_context is None:
            return None
        user = getattr(call_context, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            return user.user_name
        state = getattr(call_context, "state", None)
        if state:
            return state.get("caller")
        return None

    async def execute(self, context, event_queue):
        """Drive one core-computed collect round and emit a contract-faithful turn.

        Args:
            context: The a2a-sdk ``RequestContext`` (task_id, context_id, current_task,
                message, call_context).
            event_queue: The event queue for status/artifact emission.
        """
        ctx = context.context_id
        current = context.current_task
        is_resume = (
            current is not None and current.status.state == TaskState.TASK_STATE_INPUT_REQUIRED
        )

        if is_resume:
            party = self._party.get(ctx, ctx)
            skill = self._skill.get(ctx, "")
        else:
            # Parse the inbound CollectRequest (single JSON DataPart — wire contract).
            message = getattr(context, "message", None)
            datas = get_data_parts(message.parts) if message is not None else []
            if not datas:
                raise ValueError("CollectRequest DataPart missing from inbound message")
            request = CollectRequest.model_validate(datas[0])
            self.last_request_data = datas[0]
            if ctx:
                self.context_ids_seen.append(ctx)
            party = request.party
            skill = request.skill
            self._party[ctx] = party
            self._skill[ctx] = skill

        # Trust boundary (A6): permissive no-op for an unauthenticated caller; strict
        # scoping only under strict=True.
        authorize_leg(self._caller_of(context), party, strict=self._strict)

        plan = self._plan_for(ctx)
        r = self._rounds.get(ctx, 0)
        self._rounds[ctx] = r + 1
        collect_round = plan.round_for(r)

        # a2a-sdk requires the Task object before any TaskStatusUpdateEvents.
        task = Task(
            id=context.task_id,
            context_id=ctx,
            status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
        )
        await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.start_work(message=new_text_message(f"Collecting {skill or 'proof'}…"))
        await asyncio.sleep(self._hold_seconds)

        # Drive the round through core: classify each arrived doc, record a leg task.
        legs = self._tasks.setdefault(ctx, [])
        for fid in collect_round.fixture_ids:
            extraction = await self._engine.extract(FixtureDocument(fixture_id=fid), None)
            entry, result = classify_document(fid, extraction, thresholds=self._thresholds)

            # M1.9: stamp rejected entries with reason_code + message (verbatim relay)
            if entry.disposition == Disposition.REJECTED:
                code, msg = explain_rejection(entry, result.gate, explanations=self._explanations)
                entry = entry.model_copy(update={"reason_code": code, "message": msg})

            leg = create_leg_task(
                context_id=ctx,
                ordinal=next_ordinal(legs),
                task_id=f"{context.task_id}-doc-{len(legs)}",
            )
            stamp_ledger_entry(leg, entry)
            legs.append(leg)

        terminal = plan.is_terminal(r)

        # Non-empty progress before the artifact (A11).
        collected = len(legs)
        await updater.update_status(
            TaskState.TASK_STATE_WORKING,
            message=new_text_message(f"Classified {collected} document(s) so far…"),
        )

        overall = self._overall_disposition(legs, terminal=terminal)
        next_state = _status_for(overall)

        # M1.9: compute advisory satisfaction and build the turn with the real outstanding.
        # Build a preliminary turn to get the status with the ledger (for advisory input).
        prelim_turn = build_exchange_turn(ctx, legs, outstanding=[], terminal=terminal)
        advisory = advisory_satisfaction(prelim_turn.status)

        # Rebuild the turn with the advisory outstanding.
        # NOTE: terminal flag stays plan-driven (not rewired to advisory.done) to avoid
        # perturbing M1.8's park/resume tests and _overall_disposition's PENDING-leg handling.
        turn = build_exchange_turn(ctx, legs, outstanding=advisory.outstanding, terminal=terminal)

        # M1.9: build the RequirementsList from the advisory + explanations.
        requirements = propose_requirements(turn.status, explanations=self._explanations)

        # M1.9: emit BOTH ExchangeTurn and RequirementsList in one artifact (two data parts).
        # ExchangeTurn part FIRST (critical: existing M1.8 decoders rely on datas[0]).
        await updater.add_artifact(
            [
                new_data_part(turn.model_dump(mode="json")),
                new_data_part(requirements.model_dump(mode="json")),
            ],
            last_chunk=True,
        )

        if next_state == TaskState.TASK_STATE_INPUT_REQUIRED:
            await updater.update_status(
                TaskState.TASK_STATE_INPUT_REQUIRED,
                message=new_text_message("Awaiting additional proof to proceed."),
            )
        else:
            await updater.complete()

    @staticmethod
    def _overall_disposition(legs, *, terminal: bool) -> Disposition:
        """Fold the per-leg dispositions into the exchange-level disposition (M1.8 step 7).

        ``PENDING`` if not terminal (more rounds outstanding) OR any leg is ``PENDING``;
        else ``ACCEPTED`` if any leg is accepted, else ``REJECTED``.
        """
        dispositions = [
            entry.disposition for entry in map(ledger_entry_of, legs) if entry is not None
        ]
        if not terminal:
            return Disposition.PENDING
        if Disposition.PENDING in dispositions:
            return Disposition.PENDING
        if Disposition.ACCEPTED in dispositions:
            return Disposition.ACCEPTED
        return Disposition.REJECTED

    async def cancel(self, context, event_queue):
        """Cancel the task (mirror the mock)."""
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.cancel()
