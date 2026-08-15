"""Tests for the Address completeness gate (S1-3).

Validates the deterministic satisfaction function against eval fixtures:
- Gov-id OR branch
- Distinct-issuer utility-bill counts
- Only ACCEPTED counts (not pending/rejected)
- Authoritative tool wrapper reads from session state
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from agents.address.satisfaction import (
    COLLECTION_STATUS_STATE_KEY,
    GOV_ID,
    UTILITY_BILL,
    SatisfactionResult,
    check_completeness,
    is_satisfied,
)
from contract import CollectionStatus, Disposition, ExchangeTurn, Extraction, LedgerEntry


def _load_evals() -> dict[str, Any]:
    """Load the address evals fixture."""
    eval_path = Path(__file__).resolve().parents[2] / "wiki" / "evals" / "address" / "expected.json"
    with eval_path.open() as f:
        return json.load(f)


def _entries(*ids: str) -> list[LedgerEntry]:
    """Build LedgerEntry instances from eval fixture IDs.

    Args:
        *ids: One or more entry IDs to load from expected.json.

    Returns:
        List of LedgerEntry instances.
    """
    data = _load_evals()
    result = []

    for entry_id in ids:
        raw_entry = next((e for e in data["documents"] if e["id"] == entry_id), None)
        if not raw_entry:
            raise ValueError(f"Entry ID {entry_id} not found in eval fixture")

        # Build LedgerEntry explicitly (raw has extra keys that fail extra="forbid")
        ledger_entry = LedgerEntry(
            id=raw_entry["id"],
            doctype=raw_entry["doctype"],
            issuer=raw_entry["issuer"],
            disposition=Disposition(raw_entry["expected_disposition"]),
            extraction=Extraction.model_validate(raw_entry["extraction"]),
        )
        result.append(ledger_entry)

    return result


# Pure function tests


def test_gov_id_clean_satisfies():
    """One accepted gov-id satisfies (gov-id OR branch)."""
    ledger = _entries("gov-id-clean")
    status = CollectionStatus(ledger=ledger)

    result = is_satisfied(status)

    assert result.done is True
    assert result.outstanding == []
    assert result.accepted_issuers == []  # No bills


def test_gov_id_expired_pending_does_not_satisfy():
    """Pending gov-id does not satisfy (only ACCEPTED counts)."""
    ledger = _entries("gov-id-expired")
    status = CollectionStatus(ledger=ledger)

    result = is_satisfied(status)

    assert result.done is False
    assert sorted(result.outstanding) == [GOV_ID, UTILITY_BILL]
    assert result.accepted_issuers == []


def test_two_powerco_bills_are_one_issuer():
    """Canonicalization equivalence: both PowerCo variants → 1 distinct issuer."""
    ledger = _entries("bill-powerco-clean", "bill-powerco-clean-2")
    status = CollectionStatus(ledger=ledger)

    result = is_satisfied(status)

    assert result.done is False  # Only 1 distinct issuer
    assert sorted(result.outstanding) == [GOV_ID, UTILITY_BILL]
    assert result.accepted_issuers == ["power-co"]


def test_two_distinct_issuers_satisfy():
    """Two accepted utility-bills from distinct issuers satisfy."""
    ledger = _entries("bill-powerco-clean", "bill-aquautil-clean")
    status = CollectionStatus(ledger=ledger)

    result = is_satisfied(status)

    assert result.done is True
    assert result.outstanding == []
    assert result.accepted_issuers == ["aqua-util", "power-co"]


def test_powerco_plus_aquautil_pending_does_not_satisfy():
    """One accepted bill + one pending bill = only 1 distinct accepted issuer."""
    ledger = _entries("bill-powerco-clean", "bill-aquautil-clear")
    status = CollectionStatus(ledger=ledger)

    result = is_satisfied(status)

    assert result.done is False
    assert sorted(result.outstanding) == [GOV_ID, UTILITY_BILL]
    assert result.accepted_issuers == ["power-co"]


def test_powerco_plus_aquautil_rejected_does_not_satisfy():
    """One accepted bill + one rejected bill = only 1 distinct accepted issuer."""
    ledger = _entries("bill-powerco-clean", "bill-aquautil-blurry")
    status = CollectionStatus(ledger=ledger)

    result = is_satisfied(status)

    assert result.done is False
    assert sorted(result.outstanding) == [GOV_ID, UTILITY_BILL]
    assert result.accepted_issuers == ["power-co"]


def test_gov_id_plus_rejected_bill_satisfies():
    """Gov-id branch wins regardless of a rejected bill."""
    ledger = _entries("gov-id-clean", "bill-aquautil-blurry")
    status = CollectionStatus(ledger=ledger)

    result = is_satisfied(status)

    assert result.done is True
    assert result.outstanding == []
    assert result.accepted_issuers == []  # Blurry bill is rejected, not accepted


def test_passport_unsupported_does_not_satisfy():
    """Rejected non-bill doesn't count."""
    ledger = _entries("passport-unsupported")
    status = CollectionStatus(ledger=ledger)

    result = is_satisfied(status)

    assert result.done is False
    assert sorted(result.outstanding) == [GOV_ID, UTILITY_BILL]
    assert result.accepted_issuers == []


def test_empty_ledger_not_satisfied():
    """Empty ledger is not satisfied."""
    status = CollectionStatus(ledger=[])

    result = is_satisfied(status)

    assert result.done is False
    assert sorted(result.outstanding) == [GOV_ID, UTILITY_BILL]
    assert result.accepted_issuers == []


def test_full_corpus_satisfies():
    """Full corpus with gov-id-clean present → satisfied."""
    # Load all entries
    ledger = _entries(
        "gov-id-clean",
        "gov-id-expired",
        "bill-powerco-clean",
        "bill-powerco-clean-2",
        "bill-aquautil-clean",
        "bill-aquautil-clear",
        "bill-aquautil-blurry",
        "passport-unsupported",
    )
    status = CollectionStatus(ledger=ledger)

    result = is_satisfied(status)

    assert result.done is True  # gov-id-clean present
    assert result.outstanding == []
    # Two distinct accepted issuers: power-co, aqua-util
    assert result.accepted_issuers == ["aqua-util", "power-co"]


# Tool wrapper tests


def test_tool_wrapper_state_absent():
    """Tool wrapper with absent state returns not-done."""
    tool_context = MagicMock()
    tool_context.state = {}

    result = check_completeness(tool_context)

    assert result["done"] is False
    assert sorted(result["outstanding"]) == [GOV_ID, UTILITY_BILL]
    assert result["accepted_issuers"] == []


def test_tool_wrapper_exchange_turn_dict_satisfied():
    """Tool wrapper with ExchangeTurn dict (satisfying) → done."""
    ledger = _entries("gov-id-clean")
    turn = ExchangeTurn(
        context_id="test-ctx",
        status=CollectionStatus(ledger=ledger, outstanding=[], terminal=True),
    )

    tool_context = MagicMock()
    tool_context.state = {COLLECTION_STATUS_STATE_KEY: turn.model_dump()}

    result = check_completeness(tool_context)

    assert result["done"] is True
    assert result["outstanding"] == []


def test_tool_wrapper_collection_status_dict_satisfied():
    """Tool wrapper with CollectionStatus dict (two distinct bills) → done."""
    ledger = _entries("bill-powerco-clean", "bill-aquautil-clean")
    status = CollectionStatus(ledger=ledger, outstanding=[], terminal=True)

    tool_context = MagicMock()
    tool_context.state = {COLLECTION_STATUS_STATE_KEY: status.model_dump()}

    result = check_completeness(tool_context)

    assert result["done"] is True
    assert result["outstanding"] == []
    assert result["accepted_issuers"] == ["aqua-util", "power-co"]


def test_tool_wrapper_garbage_state_returns_not_done():
    """Tool wrapper with uncoercible garbage → not-done (no raise)."""
    tool_context = MagicMock()
    tool_context.state = {COLLECTION_STATUS_STATE_KEY: "garbage"}

    # Should not raise; should return not-done
    result = check_completeness(tool_context)

    assert result["done"] is False
    assert sorted(result["outstanding"]) == [GOV_ID, UTILITY_BILL]


def test_satisfaction_result_extra_forbid():
    """Verify SatisfactionResult rejects extra keys."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SatisfactionResult.model_validate(
            {"done": True, "outstanding": [], "accepted_issuers": [], "extra_key": "bad"}
        )
