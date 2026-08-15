"""S1-1 — Native A2A consumer + park/resume contract (adr-0009).

Three layers of seam coverage for the Sprint-1 consumer switch:

- **Test A (contract-level, no ADK):** a raw a2a-sdk client proves the wire
  contract — first turn WORKING -> INPUT_REQUIRED (park) with a non-empty
  ``status.message``, then a resume ``message/send`` to the same task -> COMPLETED
  with the gov-id-clean artifact. Locks the contract regardless of ADK internals.
- **Test B (native-construct spike):** the platform-native ``RemoteA2aAgent`` run
  as a root agent turns the park into a paused ``LongRunningFunctionTool`` call,
  then a ``FunctionResponse`` resumes the same A2A task and returns the payload.
  This is the adr-0009 "spike before leaning on the experimental construct."
- **Test C (port guard):** the M0 ``BridgeClient`` port surfaces a park as
  ``BridgeParkedError`` — park is not a failure, and the port must not hang.
"""

import asyncio
import json

import httpx
import pytest
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.helpers.proto_helpers import (
    get_data_parts,
    get_message_text,
    new_text_message,
)
from a2a.types import (
    GetTaskRequest,
    SendMessageRequest,
    TaskState,
)
from google.adk.runners import InMemoryRunner
from google.genai import types

from bridge_client import (
    A2ABridgeClient,
    BridgeParkedError,
    build_bridge_remote_agent,
    request_to_message,
)
from contract import CollectRequest
from tests.support.live_server import LiveMockServer

PARTY = "jordan-lee"
SKILL = "address-proof"


# --------------------------------------------------------------------------- #
# Test A — contract-level (raw a2a-sdk client, no ADK)
# --------------------------------------------------------------------------- #


async def _drive_park_resume_raw(base_url: str) -> dict:
    """Send -> poll to INPUT_REQUIRED -> resume same task -> read completed payload.

    Returns a dict with the observed states, the park message text, and the final
    gov-id-clean payload.
    """
    async with httpx.AsyncClient() as hx:
        card = await A2ACardResolver(hx, base_url).get_agent_card()
        factory = ClientFactory(
            ClientConfig(httpx_client=hx, streaming=False, polling=True)
        )
        client = factory.create(card)

        observed: list[TaskState] = []

        # First turn: send the CollectRequest, get back a WORKING task.
        msg = request_to_message(CollectRequest(party=PARTY, skill=SKILL))
        task = None
        async for resp in client.send_message(SendMessageRequest(message=msg)):
            assert resp.HasField("task"), "send_message returned a message, not a task"
            task = resp.task
            break
        assert task is not None
        observed.append(task.status.state)

        # Poll until the task parks at INPUT_REQUIRED.
        deadline = asyncio.get_running_loop().time() + 10.0
        while task.status.state != TaskState.TASK_STATE_INPUT_REQUIRED:
            assert task.status.state not in (
                TaskState.TASK_STATE_FAILED,
                TaskState.TASK_STATE_CANCELED,
                TaskState.TASK_STATE_REJECTED,
                TaskState.TASK_STATE_COMPLETED,
            ), f"unexpected pre-park state: {task.status.state}"
            assert asyncio.get_running_loop().time() < deadline, "never parked"
            await asyncio.sleep(0.02)
            task = await client.get_task(GetTaskRequest(id=task.id))
            observed.append(task.status.state)

        park_message = get_message_text(task.status.message) if task.status.message else ""

        # Resume: send a follow-up message on the SAME task_id / context_id.
        resume = new_text_message(
            "Here is the requested proof.",
            context_id=task.context_id,
            task_id=task.id,
        )
        async for resp in client.send_message(SendMessageRequest(message=resume)):
            assert resp.HasField("task")
            task = resp.task
            break
        observed.append(task.status.state)

        # Poll until COMPLETED.
        deadline = asyncio.get_running_loop().time() + 10.0
        while task.status.state != TaskState.TASK_STATE_COMPLETED:
            assert asyncio.get_running_loop().time() < deadline, "resume never completed"
            await asyncio.sleep(0.02)
            task = await client.get_task(GetTaskRequest(id=task.id))
            observed.append(task.status.state)

        assert task.artifacts, "completed task carried no artifacts"
        datas = get_data_parts(task.artifacts[0].parts)
        assert datas, "completed artifact carried no data part"

        return {
            "observed": observed,
            "park_message": park_message,
            "payload": datas[0],
        }


def test_park_resume_contract_raw():
    """Test A — the park/resume wire contract holds end to end."""
    with LiveMockServer(hold_seconds=0.2, park=True) as server:
        result = asyncio.run(_drive_park_resume_raw(server.base_url))

    observed = result["observed"]
    assert TaskState.TASK_STATE_WORKING in observed
    assert TaskState.TASK_STATE_INPUT_REQUIRED in observed
    assert observed.index(TaskState.TASK_STATE_WORKING) < observed.index(
        TaskState.TASK_STATE_INPUT_REQUIRED
    )
    assert observed[-1] == TaskState.TASK_STATE_COMPLETED

    # The park carried a non-empty status.message (adr-0009 / lessons A11).
    assert result["park_message"].strip(), "park emitted an empty status.message"

    # The resume completed with the gov-id-clean ExchangeTurn payload.
    ledger = result["payload"]["status"]["ledger"]
    assert len(ledger) == 1
    doc = ledger[0]
    assert doc["id"] == "gov-id-clean"
    assert doc["doctype"] == "gov-id"
    assert doc["disposition"] == "accepted"


# --------------------------------------------------------------------------- #
# Test B — native-construct spike (RemoteA2aAgent)
# --------------------------------------------------------------------------- #


_A2A_START = b"<a2a_datapart_json>"
_A2A_END = b"</a2a_datapart_json>"


def _extract_exchange_turn(events) -> dict | None:
    """Find a gov-id-clean ExchangeTurn embedded in any event's inline data.

    Generic A2A data parts arrive as an inline blob wrapped in ADK's data-part
    tags (see ``convert_a2a_part_to_genai_part``); unwrap and JSON-parse it.
    """
    for event in events:
        if not (event.content and event.content.parts):
            continue
        for part in event.content.parts:
            blob = getattr(part, "inline_data", None)
            if blob is None or not blob.data:
                continue
            raw = blob.data
            if _A2A_START in raw and _A2A_END in raw:
                raw = raw.split(_A2A_START, 1)[1].split(_A2A_END, 1)[0]
            try:
                data = json.loads(raw)
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict) and data.get("status", {}).get("ledger"):
                return data
    return None


def _find_paused_call(events):
    """Return the (function_call) that paused the runner, or None."""
    for event in events:
        if not event.long_running_tool_ids:
            continue
        for fc in event.get_function_calls():
            if fc.id in event.long_running_tool_ids:
                return fc
    return None


async def _drive_remote_agent(card_url: str):
    """Drive RemoteA2aAgent through a park -> resume via the ADK Runner."""
    async with httpx.AsyncClient() as hx:
        agent = build_bridge_remote_agent(card_url, httpx_client=hx)
        runner = InMemoryRunner(agent, app_name="native-consumer-spike")
        user_id, session_id = PARTY, "s1-1"
        await runner.session_service.create_session(
            app_name="native-consumer-spike",
            user_id=user_id,
            session_id=session_id,
        )

        # First turn: expect the runner to pause on a long-running function call.
        first = [
            e
            async for e in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part(text="Collect the address proof.")],
                ),
            )
        ]
        paused = _find_paused_call(first)

        # Resume: answer the long-running call, re-driving the same A2A task.
        resumed = []
        if paused is not None:
            resume_msg = types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            id=paused.id,
                            name=paused.name,
                            response={"status": "provided"},
                        )
                    )
                ],
            )
            resumed = [
                e
                async for e in runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=resume_msg,
                )
            ]

        return paused, _extract_exchange_turn(first + resumed)


def test_remote_agent_park_resume_spike():
    """Test B — RemoteA2aAgent pauses on park and resumes to the payload."""
    with LiveMockServer(hold_seconds=0.2, park=True) as server:
        paused, payload = asyncio.run(_drive_remote_agent(server.card_url))

    assert paused is not None, "RemoteA2aAgent did not pause on the INPUT_REQUIRED park"
    assert payload is not None, "no ExchangeTurn returned after resume"
    assert payload["status"]["ledger"][0]["id"] == "gov-id-clean"


# --------------------------------------------------------------------------- #
# Test C — port guard (park is not a failure, and must not hang)
# --------------------------------------------------------------------------- #


def test_port_raises_parked_error_on_park():
    """Test C — the M0 port surfaces a park as BridgeParkedError."""

    async def _run():
        async with A2ABridgeClient(server.base_url, poll_interval=0.02) as client:
            await client.collect(CollectRequest(party=PARTY, skill=SKILL))

    with LiveMockServer(hold_seconds=0.2, park=True) as server:
        with pytest.raises(BridgeParkedError):
            asyncio.run(_run())
