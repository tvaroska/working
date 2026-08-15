"""Deterministic Address completeness gate (sense B) — the code that decides "done".

LLM routes, code decides: this is the authoritative satisfaction function the model
may call but never override (docs/lessons-learned.md A3). Address rule: proof of
address is satisfied by one accepted gov-id OR two accepted utility-bills from
distinct (already-canonical) issuers.

State-key convention: the ADK tool wrapper reads the latest CollectionStatus/ExchangeTurn
from session state under COLLECTION_STATUS_STATE_KEY = "collection_status". S1-4 writes
the Bridge tool's returned ExchangeTurn under the same key.
"""

from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel, ConfigDict, Field

from contract import CollectionStatus, Disposition, ExchangeTurn

GOV_ID = "gov-id"
UTILITY_BILL = "utility-bill"
REQUIRED_DISTINCT_ISSUERS = 2
COLLECTION_STATUS_STATE_KEY = "collection_status"


class SatisfactionResult(BaseModel):
    """Result of the completeness gate check."""

    model_config = ConfigDict(extra="forbid")

    done: bool
    outstanding: list[str] = Field(default_factory=list)
    accepted_issuers: list[str] = Field(default_factory=list)  # sorted canonical set (parity, A2)


def is_satisfied(status: CollectionStatus) -> SatisfactionResult:
    """Pure function: check if the address proof requirement is satisfied.

    Args:
        status: CollectionStatus containing the classified ledger.

    Returns:
        SatisfactionResult with:
        - done: True if one accepted gov-id OR ≥2 accepted utility-bills from
          distinct canonical issuers
        - outstanding: ["gov-id", "utility-bill"] if not done, [] if done
        - accepted_issuers: sorted list of canonical issuers from accepted bills

    Notes:
        - Only ACCEPTED disposition counts toward completeness
        - Bills with None/empty issuer are excluded from distinct-issuer count
        - The ledger's issuer is already canonical (sense A); do not re-canonicalize
    """
    accepted = [e for e in status.ledger if e.disposition == Disposition.ACCEPTED]

    gov_id_ok = any(e.doctype == GOV_ID for e in accepted)

    bill_issuers = sorted(
        {
            e.issuer
            for e in accepted
            if e.doctype == UTILITY_BILL and e.issuer  # exclude None/empty (Decision 4)
        }
    )

    done = gov_id_ok or len(bill_issuers) >= REQUIRED_DISTINCT_ISSUERS
    outstanding = [] if done else [GOV_ID, UTILITY_BILL]

    return SatisfactionResult(done=done, outstanding=outstanding, accepted_issuers=bill_issuers)


def _coerce_status(raw: dict | CollectionStatus | ExchangeTurn) -> CollectionStatus:
    """Coerce various shapes to CollectionStatus.

    Args:
        raw: A CollectionStatus, ExchangeTurn, or dict of either.

    Returns:
        A CollectionStatus instance.

    Notes:
        If coercion fails, returns an empty CollectionStatus (not-done) rather
        than raising — a tool that raises would surface as an error event and
        could stall the loop.
    """
    if isinstance(raw, CollectionStatus):
        return raw
    if isinstance(raw, ExchangeTurn):
        return raw.status

    # Try dict coercion: ExchangeTurn first, then CollectionStatus
    try:
        if isinstance(raw, dict):
            # If it has a 'status' key, it's likely an ExchangeTurn
            if "status" in raw:
                turn = ExchangeTurn.model_validate(raw)
                return turn.status
            else:
                return CollectionStatus.model_validate(raw)
    except Exception:
        # Fall back to empty status
        pass

    # Could not coerce — return empty (not done)
    return CollectionStatus(ledger=[], outstanding=[], terminal=False)


def check_completeness(tool_context: ToolContext) -> dict:
    """Authoritative completeness gate. Reads the classified ledger from session
    state (never from the model) and returns {done, outstanding, accepted_issuers}.
    The model may call this to route; it can never fabricate "done".

    Args:
        tool_context: ADK ToolContext (injected, not surfaced to model).

    Returns:
        Dict representation of SatisfactionResult.
    """
    raw = tool_context.state.get(COLLECTION_STATUS_STATE_KEY)
    if not raw:
        # No collection yet -> not done, both alternatives outstanding.
        return SatisfactionResult(done=False, outstanding=[GOV_ID, UTILITY_BILL]).model_dump()

    status = _coerce_status(raw)
    return is_satisfied(status).model_dump()
