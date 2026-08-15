"""Mock Bridge executor — simulates the async long-running collect path.

Emits WORKING immediately (so message/send with return_immediately/polling returns
Task{WORKING}), holds for a configurable duration, then attaches an ExchangeTurn
artifact and marks COMPLETED.
"""

import asyncio

from a2a.helpers.proto_helpers import new_data_part
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
    """

    def __init__(self, ledger_entry: LedgerEntry, *, hold_seconds: float = 10.0) -> None:
        """Initialize the mock executor.

        Args:
            ledger_entry: The preloaded ledger entry to return (gov-id-clean).
            hold_seconds: How long to hold in WORKING state before completing.
        """
        self._ledger_entry = ledger_entry
        self._hold_seconds = hold_seconds

    async def execute(self, context, event_queue):
        """Execute the mock collect: Task -> WORKING -> hold -> artifact -> COMPLETED.

        Args:
            context: Request context carrying task_id and context_id.
            event_queue: Event queue for emitting status updates.
        """
        # First, enqueue a Task object (required by a2a-sdk for async workflows).
        # This must happen BEFORE any TaskStatusUpdateEvents.
        task = Task(
            id=context.task_id,
            context_id=context.context_id,
            status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
        )
        await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, context.task_id, context.context_id)

        # Emit WORKING (so message/send with return_immediately returns
        # immediately), then hold. Sleeping BEFORE start_work() would delay the
        # send response by hold_seconds and defeat the async poll surface.
        await updater.start_work()
        await asyncio.sleep(self._hold_seconds)

        # Build the ExchangeTurn from the context_id and preloaded ledger entry,
        # wrap as a single JSON DataPart, attach as an artifact, then complete.
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
