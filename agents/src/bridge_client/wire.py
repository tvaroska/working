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

import json

from a2a.helpers.proto_helpers import get_data_parts, new_data_message
from a2a.types import Message, Role, Task

from contract import CollectRequest, ExchangeTurn

_A2A_START = b"<a2a_datapart_json>"
_A2A_END = b"</a2a_datapart_json>"


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


def extract_exchange_turn(events) -> dict | None:
    """Scan an ADK event stream for the Bridge's ``ExchangeTurn`` DataPart.

    A generic A2A data part arrives from ``RemoteA2aAgent`` as an ``inline_data``
    blob wrapped in ADK's ``<a2a_datapart_json>…</a2a_datapart_json>`` tags (see
    ``convert_a2a_part_to_genai_part``). This unwraps and JSON-parses the embedded
    ``ExchangeTurn``, returning the first dict whose ``status.ledger`` is non-empty
    (the completed collection) or ``None`` if none is present.

    The Bridge's ``ExchangeTurn`` DataPart may not ride the *last* event, so this
    scans **all** events to recover the structured payload.
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


def latest_exchange_turn(events) -> dict | None:
    """Return the *most-recently* collected ``ExchangeTurn`` from a session stream.

    :func:`extract_exchange_turn` returns the *first* matching turn in scan order;
    a shared session accumulates one artifact per completed round, so scanning
    **reversed** yields the latest (freshest) turn — the one a loop gate must
    judge. Keeps the reversed-scan idiom in one place (used by the graph gate and
    the durability tests).
    """
    return extract_exchange_turn(list(reversed(list(events))))
