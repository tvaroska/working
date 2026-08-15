"""The ``a2a-sdk`` adapter for the :class:`BridgeClient` port.

Implements ``collect`` over the canonical A2A JSON-RPC surface:
``message/send`` (return-immediately) -> poll ``tasks/get`` until the task is
terminal -> decode the returned :class:`~contract.ExchangeTurn`.

Wire encoding (DECISION — the M0.4 mock server MUST emit this exact shape):

- **Outbound (client -> Bridge):** the ``CollectRequest`` is a single JSON
  DataPart in one A2A ``Message`` (``media_type="application/json"``,
  ``role=ROLE_USER``, ``context_id = request.context_id or None``), serialized
  with ``request.model_dump(mode="json")``.
- **Inbound (Bridge -> client):** on ``TASK_STATE_COMPLETED`` the full
  ``ExchangeTurn`` is a single JSON DataPart inside ``task.artifacts[0]``. If the
  decoded ``context_id`` is empty, it is backfilled from ``task.context_id``.

Notes on the installed ``a2a-sdk`` (1.1.x): types are protobuf messages (build
with kwargs, read with ``.field`` / ``.HasField``; never ``.model_dump()``);
``send_message`` is an async generator even in the non-streaming path; the
JSONRPC transport requires an ``httpx.AsyncClient`` in ``ClientConfig``.
"""

import asyncio

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.helpers.proto_helpers import get_data_parts, new_data_message
from a2a.types import (
    GetTaskRequest,
    Message,
    Role,
    SendMessageRequest,
    Task,
    TaskState,
)

from contract import CollectRequest, ExchangeTurn

from .port import (
    BridgeClient,
    BridgeClientError,
    BridgeParkedError,
    BridgeTimeoutError,
)

# Terminal states that are not a successful completion.
_TERMINAL_FAILURE_STATES: frozenset[TaskState] = frozenset(
    {
        TaskState.TASK_STATE_FAILED,
        TaskState.TASK_STATE_CANCELED,
        TaskState.TASK_STATE_REJECTED,
    }
)

# Park states: a pause awaiting input, NOT a failure (adr-0009). The M0 port has
# no resume path, so it raises BridgeParkedError instead of counting these as a
# generic failure or looping until the poll deadline. Parked collections require
# the native RemoteA2aAgent consumer.
_PARK_STATES: frozenset[TaskState] = frozenset(
    {
        TaskState.TASK_STATE_INPUT_REQUIRED,
        TaskState.TASK_STATE_AUTH_REQUIRED,
    }
)


def request_to_message(request: CollectRequest) -> Message:
    """Encode a ``CollectRequest`` as a single-DataPart A2A ``Message``."""
    return new_data_message(
        request.model_dump(mode="json"),
        media_type="application/json",
        context_id=request.context_id or None,
        role=Role.ROLE_USER,
    )


def task_to_exchange_turn(task: Task) -> ExchangeTurn:
    """Decode the ``ExchangeTurn`` carried in a completed task's first artifact.

    Raises :class:`BridgeClientError` if there is no artifact with a data part.
    Backfills an empty ``context_id`` from ``task.context_id`` (A2A's
    authoritative context id).
    """
    if not task.artifacts:
        raise BridgeClientError("completed task carried no artifacts")

    datas = get_data_parts(task.artifacts[0].parts)
    if not datas:
        raise BridgeClientError("completed task artifact carried no data part")

    turn = ExchangeTurn.model_validate(datas[0])
    if not turn.context_id:
        turn = turn.model_copy(update={"context_id": task.context_id})
    return turn


class A2ABridgeClient(BridgeClient):
    """A :class:`BridgeClient` backed by the canonical A2A JSON-RPC surface.

    ``poll_interval`` / ``poll_timeout`` are configurable specifically so M0.6
    can shrink the mock's ~10s hold and keep the poll loop tight.
    """

    def __init__(
        self,
        base_url: str,
        *,
        httpx_client: httpx.AsyncClient | None = None,
        poll_interval: float = 0.5,
        poll_timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url
        self._poll_interval = poll_interval
        self._poll_timeout = poll_timeout
        if httpx_client is None:
            self._httpx = httpx.AsyncClient()
            self._owns_httpx = True
        else:
            self._httpx = httpx_client
            self._owns_httpx = False
        # Adapter impl detail (deliberately NOT on the BridgeClient port): the
        # sequence of task states observed during a collect. M0.6 asserts that
        # TASK_STATE_WORKING was seen before TASK_STATE_COMPLETED, proving the
        # async poll path ran rather than a blocking sleep.
        self.observed_states: list[TaskState] = []

    async def collect(self, request: CollectRequest) -> ExchangeTurn:
        self.observed_states = []
        try:
            card = await A2ACardResolver(self._httpx, self._base_url).get_agent_card()
            factory = ClientFactory(
                ClientConfig(httpx_client=self._httpx, streaming=False, polling=True)
            )
            client = factory.create(card)

            msg = request_to_message(request)
            task: Task | None = None
            async for resp in client.send_message(SendMessageRequest(message=msg)):
                if not resp.HasField("task"):
                    raise BridgeClientError("send_message returned a message, not a task")
                task = resp.task
                break
        except BridgeClientError:
            raise
        except Exception as exc:  # httpx / a2a transport errors -> stable port error
            raise BridgeClientError(f"failed to send collect request: {exc}") from exc

        if task is None:
            raise BridgeClientError("send_message yielded no task")
        self.observed_states.append(task.status.state)

        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._poll_timeout
        while True:
            state = task.status.state
            if state == TaskState.TASK_STATE_COMPLETED:
                break
            if state in _PARK_STATES:
                raise BridgeParkedError(
                    f"collect parked at {state}; the M0 BridgeClient port cannot "
                    "resume — use the native RemoteA2aAgent consumer (adr-0009)"
                )
            if state in _TERMINAL_FAILURE_STATES:
                raise BridgeClientError(f"task reached terminal non-completed state: {state}")
            if loop.time() >= deadline:
                raise BridgeTimeoutError(
                    f"collect timed out after {self._poll_timeout}s; last state: {state}"
                )
            await asyncio.sleep(self._poll_interval)
            try:
                task = await client.get_task(GetTaskRequest(id=task.id))
            except Exception as exc:
                raise BridgeClientError(f"failed to poll task: {exc}") from exc
            self.observed_states.append(task.status.state)

        return task_to_exchange_turn(task)

    async def aclose(self) -> None:
        """Close the httpx client if this adapter created it."""
        if self._owns_httpx:
            await self._httpx.aclose()

    async def __aenter__(self) -> "A2ABridgeClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
