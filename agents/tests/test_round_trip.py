"""M0.6 — Live round-trip test (agent → mock → agent over real HTTP sockets).

This is the M0 **validation gate**: it proves ``CollectRequest`` in /
``ExchangeTurn`` out round-trips cleanly through canonical A2A on a live socket,
with a real ADK ``LlmAgent`` driving the turn.

The test drives the **live** round-trip over **real HTTP sockets** and asserts:
1. the returned payload matches the ``wiki/evals/address/expected.json``
   ``gov-id-clean`` entry (id + key fields), i.e. the eval data survived the full
   A2A envelope; and
2. ``TASK_STATE_WORKING`` was **observed before** ``TASK_STATE_COMPLETED`` (the
   async ``message/send`` → poll ``tasks/get`` → ``COMPLETED`` path was actually
   exercised, not a blocking sleep).
"""

import asyncio
import json
import socket
import threading
import time
from pathlib import Path

import uvicorn
from a2a.types import TaskState
from google.adk.runners import InMemoryRunner
from google.genai import types

from agents.address import build_address_agent
from agents.address.agent import APP_NAME, PARTY
from agents.mock_bridge import create_app
from bridge_client import A2ABridgeClient
from tests.support.adk_stub import ScriptedToolCallModel


def _free_port() -> int:
    """Allocate a free port on 127.0.0.1."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _LiveMockServer:
    """Context manager that runs the mock Bridge in a daemon thread.

    Picks a free port, creates the app with ``hold_seconds``, runs a uvicorn
    server in a daemon thread, and waits until it is ready. On exit, signals
    shutdown and joins the thread.
    """

    def __init__(self, *, hold_seconds: float = 1.0):
        self.hold_seconds = hold_seconds
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.server: uvicorn.Server | None = None
        self.thread: threading.Thread | None = None

    def __enter__(self) -> "_LiveMockServer":
        app = create_app(self.base_url, hold_seconds=self.hold_seconds)
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
        )
        self.server = uvicorn.Server(config)

        def _run_server():
            asyncio.run(self.server.serve())

        self.thread = threading.Thread(target=_run_server, daemon=True)
        self.thread.start()

        # Poll until the server is ready.
        deadline = time.time() + 5
        while not self.server.started:
            if time.time() > deadline:
                raise RuntimeError("mock server did not start within 5s")
            time.sleep(0.01)
        return self

    def __exit__(self, *exc_info):
        if self.server is not None:
            self.server.should_exit = True
        if self.thread is not None:
            self.thread.join(timeout=5)


async def _drive(base_url: str) -> tuple[dict, list[TaskState]]:
    """Drive the agent once and return the payload + observed states.

    Args:
        base_url: The mock Bridge's base URL.

    Returns:
        A ``(payload, observed_states)`` tuple, where ``payload`` is the
        ``function_response`` dict (``collection_to_dict(turn)``) and
        ``observed_states`` is the task-state sequence from the client.
    """
    async with A2ABridgeClient(base_url, poll_interval=0.05) as client:
        agent = build_address_agent(client, model=ScriptedToolCallModel())
        runner = InMemoryRunner(agent, app_name=APP_NAME)
        session_id = "m0-6"
        await runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=PARTY,
            session_id=session_id,
        )

        captured = []
        final_text = ""
        async for event in runner.run_async(
            user_id=PARTY,
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text="Collect the address proof.")],
            ),
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "function_response", None) is not None:
                        captured.append(part.function_response.response)
                    elif part.text:
                        final_text = part.text

        if not captured:
            raise RuntimeError(f"no function_response captured; final_text={final_text!r}")
        payload = captured[0]
        return payload, client.observed_states


def test_round_trip_agent_mock_agent():
    """M0.6 — Live round-trip: agent → mock → agent over real HTTP sockets."""
    with _LiveMockServer(hold_seconds=1.0) as server:
        payload, observed = asyncio.run(_drive(server.base_url))

    # Payload assertions (against raw expected.json to avoid tautology).
    evals_path = Path(__file__).resolve().parents[2] / "wiki/evals/address/expected.json"
    evals = json.loads(evals_path.read_text())
    gov = next(d for d in evals["documents"] if d["id"] == "gov-id-clean")
    expected_key_fields = gov["extraction"]["fields"]["key_fields"]

    assert len(payload["documents"]) == 1
    doc = payload["documents"][0]
    assert doc["id"] == "gov-id-clean"
    assert doc["doctype"] == "gov-id"
    assert doc["disposition"] == "accepted"
    assert doc["key_fields"] == expected_key_fields
    # The above check includes name and address, but spell them out explicitly:
    assert doc["key_fields"]["name"] == "Jordan Lee"
    assert doc["key_fields"]["address"] == "14 Elm Row, Springfield"
    assert isinstance(payload["context_id"], str)
    assert len(payload["context_id"]) > 0

    # Async path assertions (observed states from the client).
    assert TaskState.TASK_STATE_WORKING in observed
    assert TaskState.TASK_STATE_COMPLETED in observed
    assert observed.index(TaskState.TASK_STATE_WORKING) < observed.index(
        TaskState.TASK_STATE_COMPLETED
    )
    assert observed[-1] == TaskState.TASK_STATE_COMPLETED
    # Stronger assertion: hold=1.0/interval=0.05 guarantees multiple WORKING
    # observations (not just the send response).
    assert observed.count(TaskState.TASK_STATE_WORKING) >= 2
