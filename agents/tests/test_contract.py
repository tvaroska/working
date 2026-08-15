"""Tests for the contract models.

Validates that the domain models:
1. Round-trip through JSON serialization
2. Mirror the eval fixture field names exactly
3. Enforce extra="forbid" constraints
4. Support the M0.4 mapping path from eval entries
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contract import (
    CollectionStatus,
    CollectRequest,
    Disposition,
    ExchangeTurn,
    ExtractedFields,
    Extraction,
    LedgerEntry,
)


def test_construct_and_json_roundtrip():
    """Build a full ExchangeTurn and verify JSON round-trip."""
    turn = ExchangeTurn(
        context_id="test-ctx-001",
        status=CollectionStatus(
            ledger=[
                LedgerEntry(
                    id="gov-id-clean",
                    doctype="gov-id",
                    issuer=None,
                    disposition=Disposition.ACCEPTED,
                    extraction=Extraction(
                        fields=ExtractedFields(
                            doctype="gov-id",
                            issuer=None,
                            key_fields={
                                "name": "Jordan Lee",
                                "address": "14 Elm Row, Springfield",
                                "doc_number": "DL-8392047",
                                "issuing_authority": "State DMV",
                                "expiry": "2030-01-01",
                            },
                        ),
                        overall_confidence=0.96,
                        field_confidence={"name": 0.97, "expiry": 0.95},
                        legible=True,
                        flagged_fields=[],
                    ),
                )
            ],
            outstanding=[],
            terminal=True,
        ),
    )

    # Round-trip through JSON
    json_str = turn.model_dump_json()
    reconstructed = ExchangeTurn.model_validate_json(json_str)

    assert reconstructed == turn
    assert reconstructed.context_id == "test-ctx-001"
    assert reconstructed.status.terminal is True
    assert len(reconstructed.status.ledger) == 1
    assert reconstructed.status.ledger[0].id == "gov-id-clean"
    assert reconstructed.status.ledger[0].disposition is Disposition.ACCEPTED


def test_eval_mirror_all_entries():
    """Load the real eval fixture and validate Extraction for every entry.

    Guards the "field names mirror expected.json" invariant.
    """
    eval_path = Path(__file__).resolve().parents[2] / "wiki" / "evals" / "address" / "expected.json"
    with eval_path.open() as f:
        data = json.load(f)

    documents = data["documents"]
    assert len(documents) > 0, "Eval fixture should have at least one document"

    for entry in documents:
        # Every entry's extraction block should validate cleanly
        extraction = Extraction.model_validate(entry["extraction"])
        assert extraction.fields.doctype == entry["doctype"]


def test_eval_mirror_gov_id_clean_spot_check():
    """Spot-check the gov-id-clean entry to verify specific field values."""
    eval_path = Path(__file__).resolve().parents[2] / "wiki" / "evals" / "address" / "expected.json"
    with eval_path.open() as f:
        data = json.load(f)

    # Find the gov-id-clean entry
    gov_id_clean = next(e for e in data["documents"] if e["id"] == "gov-id-clean")

    extraction = Extraction.model_validate(gov_id_clean["extraction"])

    assert extraction.fields.doctype == "gov-id"
    assert extraction.fields.key_fields["name"] == "Jordan Lee"
    assert extraction.fields.key_fields["address"] == "14 Elm Row, Springfield"
    assert extraction.fields.key_fields["doc_number"] == "DL-8392047"
    assert extraction.overall_confidence == 0.96
    assert extraction.legible is True
    assert extraction.flagged_fields == []


def test_ledger_entry_from_eval_entry_explicit_mapping():
    """Build a LedgerEntry from a raw eval entry via explicit mapping.

    Documents the M0.4 mapping path: expected_disposition → Disposition,
    and extraction via Extraction.model_validate.
    """
    eval_path = Path(__file__).resolve().parents[2] / "wiki" / "evals" / "address" / "expected.json"
    with eval_path.open() as f:
        data = json.load(f)

    gov_id_clean = next(e for e in data["documents"] if e["id"] == "gov-id-clean")

    # M0.4 will map like this:
    ledger_entry = LedgerEntry(
        id=gov_id_clean["id"],
        doctype=gov_id_clean["doctype"],
        issuer=gov_id_clean["issuer"],
        disposition=Disposition(gov_id_clean["expected_disposition"]),
        extraction=Extraction.model_validate(gov_id_clean["extraction"]),
    )

    assert ledger_entry.id == "gov-id-clean"
    assert ledger_entry.doctype == "gov-id"
    assert ledger_entry.issuer is None
    assert ledger_entry.disposition is Disposition.ACCEPTED
    assert ledger_entry.extraction.fields.key_fields["name"] == "Jordan Lee"


def test_extra_forbid_on_ledger_entry():
    """Verify that LedgerEntry rejects a raw eval entry with extra keys.

    The raw eval entry has artifact, synthetic, note, issuer_raw, expected_*
    which are not in the LedgerEntry model, so validation must fail.
    """
    eval_path = Path(__file__).resolve().parents[2] / "wiki" / "evals" / "address" / "expected.json"
    with eval_path.open() as f:
        data = json.load(f)

    gov_id_clean = next(e for e in data["documents"] if e["id"] == "gov-id-clean")

    # Attempting to validate the whole raw entry should fail
    with pytest.raises(ValidationError) as exc_info:
        LedgerEntry.model_validate(gov_id_clean)

    # The error should mention extra fields
    error_msg = str(exc_info.value)
    assert "extra" in error_msg.lower() or "forbidden" in error_msg.lower()


def test_extra_forbid_on_collect_request():
    """Verify that CollectRequest also rejects unknown fields."""
    with pytest.raises(ValidationError) as exc_info:
        CollectRequest.model_validate(
            {"party": "jordan-lee", "skill": "address-proof", "unknown_field": "bad"}
        )

    error_msg = str(exc_info.value)
    assert "extra" in error_msg.lower() or "forbidden" in error_msg.lower()


def test_collect_request_defaults():
    """Verify CollectRequest default behavior for context_id."""
    request = CollectRequest(party="jordan-lee", skill="address-proof")

    assert request.party == "jordan-lee"
    assert request.skill == "address-proof"
    assert request.context_id is None


def test_extraction_with_missing_key_fields():
    """Verify that an extraction with missing key_fields (blurry bill) still validates."""
    eval_path = Path(__file__).resolve().parents[2] / "wiki" / "evals" / "address" / "expected.json"
    with eval_path.open() as f:
        data = json.load(f)

    # The blurry bill has no key_fields in the extraction
    blurry_bill = next(e for e in data["documents"] if e["id"] == "bill-aquautil-blurry")

    extraction = Extraction.model_validate(blurry_bill["extraction"])

    assert extraction.fields.doctype == "utility-bill"
    assert extraction.fields.issuer == "aqua-util"
    assert extraction.fields.key_fields == {}  # Empty dict, not missing
    assert extraction.overall_confidence == 0.3
    assert extraction.legible is False
