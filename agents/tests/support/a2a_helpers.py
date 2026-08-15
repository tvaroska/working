"""Shared helpers for reading A2A payloads out of ADK event streams.

Generic A2A data parts arrive from ``RemoteA2aAgent`` as an inline blob wrapped in
ADK's data-part tags (see ``convert_a2a_part_to_genai_part``); these helpers
unwrap and JSON-parse the embedded ``ExchangeTurn``.
"""

import json

_A2A_START = b"<a2a_datapart_json>"
_A2A_END = b"</a2a_datapart_json>"


def extract_exchange_turn(events) -> dict | None:
    """Find a gov-id-clean ``ExchangeTurn`` embedded in any event's inline data."""
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
