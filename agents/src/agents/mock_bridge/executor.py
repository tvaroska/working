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
"""

import asyncio

from a2a.helpers.proto_helpers import new_data_part, new_text_message
from a2a.server.agent_execution import AgentExecutor
from a2a.server.tasks import TaskUpdater
from a2a.types import Task, TaskState, TaskStatus

from contract import LedgerEntry

from .fixtures import build_exchange_turn


class MockBridgeExecutor(AgentExecutor):
    """Agent executor that simulates an async document collection.

    The executor immediately emits TASK_STATE_WORKING (so message/send returns
    immediately), sleeps for hold_seconds, then attaches an ExchangeTurn artifact
    and completes. The hold_seconds is configurable specifically so M0.6 can
    shrink the ~10s hold for testing.

    With ``park=True`` the first turn ends at INPUT_REQUIRED (a pause awaiting
    input) and only a resume turn completes it — the adr-0009 park/resume tracer.
    """

    def __init__(
        self,
        ledger_entry: LedgerEntry,
        *,
        hold_seconds: float = 10.0,
        park: bool = False,
    ) -> None:
        """Initialize the mock executor.

        Args:
            ledger_entry: The preloaded ledger entry to return (gov-id-clean).
            hold_seconds: How long to hold in WORKING state before completing.
            park: If True, the first turn parks at INPUT_REQUIRED and a resume
                turn completes it (the Sprint-1 pause/resume tracer).
        """
        self._ledger_entry = ledger_entry
        self._hold_seconds = hold_seconds
        self._park = park

    async def execute(self, context, event_queue):
        """Execute the mock collect.

        Default: Task -> WORKING -> hold -> artifact -> COMPLETED.
        Park mode, first turn: Task -> WORKING -> hold -> INPUT_REQUIRED (park).
        Park mode, resume turn: WORKING -> artifact -> COMPLETED.

        Args:
            context: Request context carrying task_id, context_id, and (on a
                resume message/send) the existing ``current_task``.
            event_queue: Event queue for emitting status updates.
        """
        # A resume message carries the existing task_id, so the request handler
        # populates context.current_task. A parked task being resumed completes.
        current = context.current_task
        if (
            self._park
            and current is not None
            and current.status.state == TaskState.TASK_STATE_INPUT_REQUIRED
        ):
            await self._complete(context, event_queue, resume=True)
            return

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
        await updater.start_work(
            message=new_text_message("Collecting address proof…")
        )
        await asyncio.sleep(self._hold_seconds)

        if self._park:
            # Park: a pause awaiting input, not a failure (adr-0009). Carry a
            # non-empty status.message so the consumer can render the park reason.
            await updater.update_status(
                TaskState.TASK_STATE_INPUT_REQUIRED,
                message=new_text_message("Awaiting additional proof to proceed."),
            )
            return

        await self._complete(context, event_queue, resume=False)

    async def _complete(self, context, event_queue, *, resume: bool) -> None:
        """Attach the ExchangeTurn artifact and mark the task COMPLETED."""
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        if resume:
            await updater.start_work(
                message=new_text_message("Resuming with provided input…")
            )
        turn = build_exchange_turn(context.context_id, self._ledger_entry)
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
