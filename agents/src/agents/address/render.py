"""Pure, network-free rendering of a collected ``ExchangeTurn``.

Deterministic ``ExchangeTurn`` -> dict / summary helpers — never free-form LLM
text. Output shape must stay stable across runs (no timestamps; dict order rides
insertion order).

These are **not** wired into the address turn any more: since adr-0009 the Bridge
sub-agent (``RemoteA2aAgent``) relays its own ``ExchangeTurn`` payload directly.
They are retained for the Sprint-1 ``is_satisfied`` gate, which will post-process
the collected ledger once control returns to the address agent, and are covered by
their own unit tests.
"""

from contract import ExchangeTurn, LedgerEntry


def _entry_summary(entry: LedgerEntry) -> dict:
    """One ledger entry as a small, flat, JSON-serializable dict."""
    return {
        "id": entry.id,
        "doctype": entry.doctype,
        "issuer": entry.issuer,
        "disposition": entry.disposition.value,
        "key_fields": dict(entry.extraction.fields.key_fields),
    }


def collection_to_dict(turn: ExchangeTurn) -> dict:
    """The JSON-serializable structured-info dict the agent's tool returns.

    ADK tool results must be dict-like; this keeps the payload small and flat:
    the exchange ``context_id`` plus one entry per collected document.
    """
    return {
        "context_id": turn.context_id,
        "documents": [_entry_summary(e) for e in turn.status.ledger],
    }


def render_collection(turn: ExchangeTurn) -> str:
    """Produce a deterministic human-readable summary of the returned ledger.

    For each ledger entry: its ``id``, ``doctype``, ``disposition``, canonical
    ``issuer`` (if any), and the extraction ``key_fields`` name/value pairs.
    Includes the exchange ``context_id``.
    """
    lines = [f"Exchange {turn.context_id}"]
    if not turn.status.ledger:
        lines.append("  (no documents collected)")
    for entry in turn.status.ledger:
        header = f"  - {entry.id} [{entry.doctype}] {entry.disposition.value}"
        if entry.issuer:
            header += f" issuer={entry.issuer}"
        lines.append(header)
        for key, value in entry.extraction.fields.key_fields.items():
            lines.append(f"      {key}: {value}")
    return "\n".join(lines)
