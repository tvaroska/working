"""Durable local stores survive a simulated process restart (M1.2, lessons A13).

Ports the S1-6 durable recipe into ``bridge/``: state written via the SQLite-backed
``Database*`` variants on a ``sqlite+aiosqlite`` file is intact after a *fresh*
store/service reopens the same file — restore is platform-DEFAULT with a durable
store ("the webhook is a doorbell, not a restore"). Also proves the factory returns
the durable variant for SESSIONS/TASK_STORE and that the in-memory default does NOT
survive.

Deviations locked in S1-6 and honored here:
- the driver is the **async** one — ``sqlite+aiosqlite:///``, not bare ``sqlite:///``;
- store/service #1 is disposed before the fresh one reopens the file, so the restart
  read does not race the write.

The real a2a ``TaskStore.save/get`` require a ``ServerCallContext`` (the M1.1
Protocol shows a simpler shape — it conforms by method name only); we pass a default
``ServerCallContext()``.
"""

import pytest
from a2a.server.context import ServerCallContext
from a2a.server.tasks import InMemoryTaskStore
from google.adk.events import Event, EventActions
from google.genai import types

from bridge.adapters.local import build_local_adapter
from bridge.aggregate import create_leg_task, ordinal_of
from bridge.seams import Seam

APP_NAME = "bridge"
USER_ID = "jordan-lee"
SESSION_ID = "s1"


@pytest.mark.seam("task_store")
@pytest.mark.anyio
async def test_task_store_survives_restart(tmp_path):
    """A task written to the durable task store is intact after a fresh reopen (A13)."""
    db_path = str(tmp_path / "tasks.db")
    ctx = ServerCallContext()

    # --- Store #1: save a task with a stamped ordinal + context_id, then tear down.
    store1 = build_local_adapter(Seam.TASK_STORE, durable=True, db_path=db_path)
    task = create_leg_task(context_id="ctx-durable", ordinal=1, task_id="task-1")
    await store1.save(task, ctx)
    # Flush sqlite handles before the fresh store reopens the file.
    await store1.engine.dispose()
    del store1

    # --- Simulated restart: a fresh durable store on the SAME file.
    store2 = build_local_adapter(Seam.TASK_STORE, durable=True, db_path=db_path)
    restored = await store2.get("task-1", ctx)

    assert restored is not None, "task did not survive the restart"
    assert restored.id == "task-1"
    assert restored.context_id == "ctx-durable"
    assert ordinal_of(restored) == 1  # the A5 sort key persisted on the task row
    await store2.engine.dispose()


def test_durable_requires_db_path():
    """durable=True for SESSIONS/TASK_STORE without a db_path is a ValueError."""
    with pytest.raises(ValueError, match="requires a db_path"):
        build_local_adapter(Seam.TASK_STORE, durable=True)
    with pytest.raises(ValueError, match="requires a db_path"):
        build_local_adapter(Seam.SESSIONS, durable=True)


@pytest.mark.anyio
async def test_in_memory_task_store_does_not_survive_restart():
    """Contrast: the in-memory default is lost when a fresh store is built."""
    ctx = ServerCallContext()
    store1 = build_local_adapter(Seam.TASK_STORE)  # non-durable default
    assert isinstance(store1, InMemoryTaskStore)
    task = create_leg_task(context_id="ctx-mem", ordinal=0, task_id="task-mem")
    await store1.save(task, ctx)

    store2 = build_local_adapter(Seam.TASK_STORE)  # a fresh in-memory store
    assert await store2.get("task-mem", ctx) is None


@pytest.mark.seam("sessions")
@pytest.mark.anyio
async def test_session_service_survives_restart(tmp_path):
    """Session state + events written durably are restored after a fresh reopen (A13)."""
    db_path = str(tmp_path / "sessions.db")

    # --- Service #1: create a session, append an event carrying a state delta.
    svc1 = build_local_adapter(Seam.SESSIONS, durable=True, db_path=db_path)
    session = await svc1.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    event = Event(
        author="user",
        content=types.Content(role="user", parts=[types.Part(text="collect")]),
        actions=EventActions(state_delta={"ledger": ["gov-id-clean"]}),
    )
    await svc1.append_event(session, event)
    # Drop the engine so the fresh service reopens a settled file.
    await svc1.db_engine.dispose()
    del svc1

    # --- Simulated restart: a fresh session service on the SAME db_url.
    svc2 = build_local_adapter(Seam.SESSIONS, durable=True, db_path=db_path)
    restored = await svc2.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)

    assert restored is not None, "session did not survive the restart"
    assert restored.state.get("ledger") == ["gov-id-clean"]
    assert any(
        e.content and e.content.parts and e.content.parts[0].text == "collect"
        for e in restored.events
    ), "appended event did not survive the restart"

    # Sanity: the factory built the durable variant, not the in-memory default.
    from google.adk.sessions import DatabaseSessionService

    assert isinstance(svc2, DatabaseSessionService)
    await svc2.db_engine.dispose()
