"""Pure A2A wire helpers for the Bridge contract (no port, no ADK).

These encode/decode the domain contract inside canonical A2A envelopes and are
shared by the seam tests (the raw-client wire-contract test still sends a
``CollectRequest`` this way). They import only ``contract`` + ``a2a-sdk``; this
package must never import anything under ``agents.*``.

Wire encoding (the mock Bridge MUST emit this exact shape):

- **Outbound (client -> Bridge):** the ``CollectRequest`` is a single JSON
  DataPart in one A2A ``Message`` (``media_type="application/json"``,
  ``role=ROLE_USER``, ``context_id = request.context_id or None``), serialized
  with ``request.model_dump(mode="json")``.
- **Inbound (Bridge -> client):** on ``TASK_STATE_COMPLETED`` the full
  ``ExchangeTurn`` is a single JSON DataPart inside ``task.artifacts[0]``. If the
  decoded ``context_id`` is empty, it is backfilled from ``task.context_id``.

Notes on the installed ``a2a-sdk`` (1.1.x): types are protobuf messages (build
with kwargs, read with ``.field`` / ``.HasField``; never ``.model_dump()``).
"""

from a2a.helpers.proto_helpers import get_data_parts, new_data_message
from a2a.types import Message, Role, Task

from contract import CollectRequest, ExchangeTurn


class BridgeWireError(Exception):
    """A completed task did not carry the expected ``ExchangeTurn`` artifact."""


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

    Raises :class:`BridgeWireError` if there is no artifact with a data part.
    Backfills an empty ``context_id`` from ``task.context_id`` (A2A's
    authoritative context id).
    """
    if not task.artifacts:
        raise BridgeWireError("completed task carried no artifacts")

    datas = get_data_parts(task.artifacts[0].parts)
    if not datas:
        raise BridgeWireError("completed task artifact carried no data part")

    turn = ExchangeTurn.model_validate(datas[0])
    if not turn.context_id:
        turn = turn.model_copy(update={"context_id": task.context_id})
    return turn
