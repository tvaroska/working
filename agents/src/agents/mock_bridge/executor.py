"""Mock Bridge executor — simulates the async long-running collect path.

Emits WORKING immediately (so message/send with return_immediately/polling returns
Task{WORKING}), holds for a configurable duration, then attaches an ExchangeTurn
artifact and marks COMPLETED.

In ``park`` mode the first turn parks at INPUT_REQUIRED instead of completing —
the Sprint-1 pause/resume tracer (adr-0009). A resume message (same task_id, so
``context.current_task`` is populated) then completes the task. Progress and park
transitions carry a **non-empty** ``status.message`` so a native ``RemoteA2aAgent``
consumer can surface progress and turn the park into a LongRunningFunctionTool
pause.

S1-5 makes the executor **stateful per context**: each Collect round is a new A2A
task under the same ``context_id``, and the executor keeps a per-context round
counter to step through a multi-turn scenario script.
"""

import asyncio
from pathlib import Path

from a2a.helpers.proto_helpers import get_data_parts, new_data_part, new_text_message
from a2a.server.agent_execution import AgentExecutor
from a2a.server.tasks import TaskUpdater
from a2a.types import Task, TaskState, TaskStatus

from contract import LedgerEntry

from .fixtures import build_exchange_turn, load_entry
from .scenarios import MockScenario


class MockBridgeExecutor(AgentExecutor):
    """Agent executor that simulates an async document collection.

    The executor immediately emits TASK_STATE_WORKING (so message/send returns
    immediately), sleeps for hold_seconds, then attaches an ExchangeTurn artifact
    and completes. The hold_seconds is configurable specifically so M0.6 can
    shrink the ~10s hold for testing.

    With ``park=True`` the first turn ends at INPUT_REQUIRED (a pause awaiting
    input) and only a resume turn completes it — the adr-0009 park/resume tracer.

    S1-5: the executor is now **stateful per context** and drives a multi-turn
    scenario script. Each round under the same context_id advances the scenario
    step counter.
    """

    def __init__(
        self,
        scenario: MockScenario,
        *,
        evals_path: Path | None = None,
        hold_seconds: float = 10.0,
        park: bool = False,
    ) -> None:
        """Initialize the mock executor.

        Args:
            scenario: The multi-turn scenario to script.
            evals_path: Explicit path to expected.json (for testing).
            hold_seconds: How long to hold in WORKING state before completing.
            park: If True, the first turn parks at INPUT_REQUIRED and a resume
                turn completes it (the Sprint-1 pause/resume tracer).
        """
        self._scenario = scenario
        self._hold_seconds = hold_seconds
        self._park = park

        # Eagerly load every distinct ledger entry across scenario steps (fail fast).
        entry_ids = {entry_id for step in scenario.steps for entry_id in step.ledger_ids}
        self._entries: dict[str, LedgerEntry] = {
            entry_id: load_entry(entry_id, evals_path) for entry_id in entry_ids
        }

        # Per-context round counter (key: context_id, value: round index).
        self._rounds: dict[str, int] = {}

        self.last_request_data: dict | None = None
        """Data part of the most recent first-turn inbound message.

        Lets the seam suite assert the outbound ``CollectRequest`` arrived as a
        structured JSON DataPart (S1-2), not free conversation text.
        """
        self.context_ids_seen: list[str] = []
        """Context id of each first-turn inbound message, in arrival order.

        Lets the S1-4 live seam test assert the **same** exchange ``context_id``
        arrives on every round (one durable exchange spans the Collect loop; no
        fresh context per round).
        """

    async def execute(self, context, event_queue):
        """Execute the mock collect.

        Default: Task -> WORKING -> hold -> faked chase progress -> artifact -> COMPLETED.
        Park mode, first turn: Task -> WORKING -> hold -> INPUT_REQUIRED (park).
        Park mode, resume turn: WORKING -> artifact -> COMPLETED.

        Args:
            context: Request context carrying task_id, context_id, and (on a
                resume message/send) the existing ``current_task``.
            event_queue: Event queue for emitting status updates.
        """
        # A resume message carries the existing task_id, so the request handler
        # populates context.current_task. A parked task being resumed completes
        # with the scenario's final step.
        current = context.current_task
        if (
            self._park
            and current is not None
            and current.status.state == TaskState.TASK_STATE_INPUT_REQUIRED
        ):
            final_step = self._scenario.steps[-1]
            await self._complete(context, event_queue, step=final_step, resume=True)
            return

        # Capture the first-turn inbound request's data part so the seam suite
        # can assert a structured CollectRequest arrived (not free text).
        message = getattr(context, "message", None)
        if message is not None:
            datas = get_data_parts(message.parts)
            if datas:
                self.last_request_data = datas[0]
        # Record the exchange context id so the S1-4 seam test can assert the same
        # context threads across the Collect loop's rounds.
        if context.context_id:
            self.context_ids_seen.append(context.context_id)

        # Compute the round: per-context round counter (S1-5).
        ctx = context.context_id
        r = self._rounds.get(ctx, 0)
        self._rounds[ctx] = r + 1
        step = self._scenario.step_for_round(r)

        # First turn. Enqueue a Task object (required by a2a-sdk for async
        # workflows) BEFORE any TaskStatusUpdateEvents.
        task = Task(
            id=context.task_id,
            context_id=context.context_id,
            status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
        )
        await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, context.task_id, context.context_id)

        # Emit WORKING with a non-empty progress message (so message/send with
        # return_immediately returns immediately), then hold. Sleeping BEFORE
        # start_work() would delay the send response and defeat the async surface.
        await updater.start_work(message=new_text_message("Collecting address proof…"))
        await asyncio.sleep(self._hold_seconds)

        # Faked chase/timeout: emit non-empty WORKING status updates (S1-5).
        for msg in step.chase_messages:
            await updater.update_status(
                TaskState.TASK_STATE_WORKING,
                message=new_text_message(msg),
            )

        if self._park:
            # Park: a pause awaiting input, not a failure (adr-0009). Carry a
            # non-empty status.message so the consumer can render the park reason.
            await updater.update_status(
                TaskState.TASK_STATE_INPUT_REQUIRED,
                message=new_text_message("Awaiting additional proof to proceed."),
            )
            return

        await self._complete(context, event_queue, step=step, resume=False)

    async def _complete(self, context, event_queue, *, step, resume: bool) -> None:
        """Attach the ExchangeTurn artifact and mark the task COMPLETED.

        Args:
            context: Request context carrying task_id and context_id.
            event_queue: Event queue for emitting status updates.
            step: The scenario step to complete with.
            resume: Whether this is a resume turn (INPUT_REQUIRED -> COMPLETED).
        """
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        if resume:
            await updater.start_work(message=new_text_message("Resuming with provided input…"))
        # Build ledger from the step's entry ids.
        ledger = [self._entries[i] for i in step.ledger_ids]
        turn = build_exchange_turn(
            context.context_id,
            ledger,
            terminal=step.terminal,
            outstanding=list(step.outstanding),
        )
        artifact_part = new_data_part(turn.model_dump(mode="json"))
        await updater.add_artifact([artifact_part])
        await updater.complete()

    async def cancel(self, context, event_queue):
        """Cancel the task (minimal implementation for M0).

        Args:
            context: Request context carrying task_id and context_id.
            event_queue: Event queue for emitting status updates.
        """
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.cancel()
