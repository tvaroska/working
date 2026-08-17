"""Tests for the requirements + completeness + explanation relay (M1.9).

Validates:
- Parity suite: advisory_satisfaction terminal-outcome parity with agents' is_satisfied
- propose_requirements: RequirementsList artifact shape + reason_code/message relay
- explain_rejection: per-doc reason_code + message stamping for rejected entries
- load_explanations: skill asset loading + missing-file tolerance

Parity by discipline (bridge/ never imports agents/): this suite re-implements the
test fixtures from agents/tests/test_satisfaction.py, building LedgerEntry explicitly
from wiki/evals/address/expected.json.
"""

import json
from pathlib import Path

import pytest
from contract import (
    CollectionStatus,
    Disposition,
    Extraction,
    LedgerEntry,
    RequirementStatus,
)

from bridge.adapters.local.extraction import FixtureExtractionEngine
from bridge.adapters.local.skill_registry import LocalSkillRegistry
from bridge.disposition import classify_document
from bridge.requirements import (
    DISTINCT_ISSUER_NEEDED,
    GOV_ID,
    ILLEGIBLE,
    PROOF_REQUIRED,
    UNSUPPORTED_DOCTYPE,
    UTILITY_BILL,
    advisory_satisfaction,
    explain_rejection,
    load_explanations,
    propose_requirements,
)


def _load_evals() -> dict:
    """Load the address evals fixture."""
    eval_path = Path(__file__).resolve().parents[2] / "wiki" / "evals" / "address" / "expected.json"
    with eval_path.open() as f:
        return json.load(f)


def _entries(*ids: str) -> list[LedgerEntry]:
    """Build LedgerEntry instances from eval fixture IDs.

    Re-implements _entries from agents/tests/test_satisfaction.py (parity by discipline).

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


# --------------------------------------------------------------------------- #
# Parity suite (the acceptance anchor — terminal-outcome equality with agents)
# --------------------------------------------------------------------------- #


def test_advisory_gov_id_clean_satisfies():
    """One accepted gov-id satisfies (gov-id OR branch). Parity: done=True, no bills."""
    ledger = _entries("gov-id-clean")
    status = CollectionStatus(ledger=ledger)

    result = advisory_satisfaction(status)

    assert result.done is True
    assert result.outstanding == []
    assert result.accepted_issuers == []  # No bills


def test_advisory_gov_id_expired_pending_does_not_satisfy():
    """Pending gov-id does not satisfy (only ACCEPTED counts). Parity: done=False."""
    ledger = _entries("gov-id-expired")
    status = CollectionStatus(ledger=ledger)

    result = advisory_satisfaction(status)

    assert result.done is False
    assert sorted(result.outstanding) == [GOV_ID, UTILITY_BILL]
    assert result.accepted_issuers == []


def test_advisory_two_powerco_bills_are_one_issuer():
    """Two PowerCo bills = 1 distinct issuer. Parity: done=False, 1 issuer."""
    ledger = _entries("bill-powerco-clean", "bill-powerco-clean-2")
    status = CollectionStatus(ledger=ledger)

    result = advisory_satisfaction(status)

    assert result.done is False  # Only 1 distinct issuer
    assert sorted(result.outstanding) == [GOV_ID, UTILITY_BILL]
    assert result.accepted_issuers == ["power-co"]


def test_advisory_two_distinct_issuers_satisfy():
    """Two accepted bills from distinct issuers satisfy. Parity: done=True, 2 issuers."""
    ledger = _entries("bill-powerco-clean", "bill-aquautil-clean")
    status = CollectionStatus(ledger=ledger)

    result = advisory_satisfaction(status)

    assert result.done is True
    assert result.outstanding == []
    assert result.accepted_issuers == ["aqua-util", "power-co"]


def test_advisory_powerco_plus_aquautil_pending_does_not_satisfy():
    """One accepted + one pending bill = 1 distinct accepted issuer. Parity: done=False."""
    ledger = _entries("bill-powerco-clean", "bill-aquautil-clear")
    status = CollectionStatus(ledger=ledger)

    result = advisory_satisfaction(status)

    assert result.done is False
    assert sorted(result.outstanding) == [GOV_ID, UTILITY_BILL]
    assert result.accepted_issuers == ["power-co"]


def test_advisory_powerco_plus_aquautil_rejected_does_not_satisfy():
    """One accepted + one rejected bill = 1 distinct accepted issuer. Parity: done=False."""
    ledger = _entries("bill-powerco-clean", "bill-aquautil-blurry")
    status = CollectionStatus(ledger=ledger)

    result = advisory_satisfaction(status)

    assert result.done is False
    assert sorted(result.outstanding) == [GOV_ID, UTILITY_BILL]
    assert result.accepted_issuers == ["power-co"]


def test_advisory_gov_id_plus_rejected_bill_satisfies():
    """Gov-id branch wins regardless of a rejected bill. Parity: done=True."""
    ledger = _entries("gov-id-clean", "bill-aquautil-blurry")
    status = CollectionStatus(ledger=ledger)

    result = advisory_satisfaction(status)

    assert result.done is True
    assert result.outstanding == []
    assert result.accepted_issuers == []  # Blurry bill is rejected


def test_advisory_passport_unsupported_does_not_satisfy():
    """Rejected non-bill doesn't count. Parity: done=False."""
    ledger = _entries("passport-unsupported")
    status = CollectionStatus(ledger=ledger)

    result = advisory_satisfaction(status)

    assert result.done is False
    assert sorted(result.outstanding) == [GOV_ID, UTILITY_BILL]
    assert result.accepted_issuers == []


def test_advisory_empty_ledger_not_satisfied():
    """Empty ledger is not satisfied. Parity: done=False."""
    status = CollectionStatus(ledger=[])

    result = advisory_satisfaction(status)

    assert result.done is False
    assert sorted(result.outstanding) == [GOV_ID, UTILITY_BILL]
    assert result.accepted_issuers == []


def test_advisory_full_corpus_satisfies():
    """Full corpus with gov-id-clean → satisfied. Parity: done=True, 2 issuers."""
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

    result = advisory_satisfaction(status)

    assert result.done is True  # gov-id-clean present
    assert result.outstanding == []
    assert result.accepted_issuers == ["aqua-util", "power-co"]


# --------------------------------------------------------------------------- #
# propose_requirements
# --------------------------------------------------------------------------- #


@pytest.mark.seam("skill_registry")
def test_propose_requirements_done_ledger():
    """Done ledger → RequirementsList.done=True, single SATISFIED requirement, no reason/message."""
    registry = LocalSkillRegistry()
    skill = registry._skills.get("address-proof")
    assert skill is not None, "address-proof skill must be loaded"
    explanations = load_explanations(skill)

    ledger = _entries("gov-id-clean")
    status = CollectionStatus(ledger=ledger)

    req_list = propose_requirements(status, explanations=explanations)

    assert req_list.done is True
    assert len(req_list.requirements) == 1
    req = req_list.requirements[0]
    assert req.item == "proof of address"
    assert req.status == RequirementStatus.SATISFIED
    assert req.doctype_hint == "gov-id"
    assert req.reason_code is None
    assert req.message is None


@pytest.mark.seam("skill_registry")
def test_propose_requirements_empty_ledger():
    """Empty ledger → done=False, reason_code=proof-required, message from yaml."""
    registry = LocalSkillRegistry()
    skill = registry._skills.get("address-proof")
    assert skill is not None
    explanations = load_explanations(skill)

    status = CollectionStatus(ledger=[])

    req_list = propose_requirements(status, explanations=explanations)

    assert req_list.done is False
    assert len(req_list.requirements) == 1
    req = req_list.requirements[0]
    assert req.status == RequirementStatus.REQUIRED
    assert req.reason_code == PROOF_REQUIRED
    assert req.message == (
        "Send a government-issued photo ID, or two utility bills from two different providers."
    )


@pytest.mark.seam("skill_registry")
def test_propose_requirements_one_accepted_bill():
    """One accepted bill → reason_code=distinct-issuer-needed, message from yaml."""
    registry = LocalSkillRegistry()
    skill = registry._skills.get("address-proof")
    assert skill is not None
    explanations = load_explanations(skill)

    ledger = _entries("bill-powerco-clean")
    status = CollectionStatus(ledger=ledger)

    req_list = propose_requirements(status, explanations=explanations)

    assert req_list.done is False
    assert len(req_list.requirements) == 1
    req = req_list.requirements[0]
    assert req.status == RequirementStatus.REQUIRED
    assert req.reason_code == DISTINCT_ISSUER_NEEDED
    assert req.message == (
        "We have one utility bill on file. Send a second bill from a different provider, "
        "or a government-issued photo ID."
    )


# --------------------------------------------------------------------------- #
# explain_rejection
# --------------------------------------------------------------------------- #


@pytest.mark.seam("extraction")
@pytest.mark.seam("skill_registry")
@pytest.mark.anyio
async def test_explain_rejection_unsupported():
    """Passport (unsupported) → reason_code=unsupported-doctype, message from yaml."""
    registry = LocalSkillRegistry()
    skill = registry._skills.get("address-proof")
    assert skill is not None
    explanations = load_explanations(skill)

    engine = FixtureExtractionEngine()
    from bridge.adapters.local.extraction import FixtureDocument

    extraction = await engine.extract(FixtureDocument(fixture_id="passport-unsupported"), None)
    entry, result = classify_document("passport-unsupported", extraction)

    code, msg = explain_rejection(entry, result.gate, explanations=explanations)

    assert entry.disposition == Disposition.REJECTED
    assert code == UNSUPPORTED_DOCTYPE
    assert msg == (
        "That document is not an accepted proof of address for this program. "
        "Send a driver's licence / state ID, or a utility bill."
    )


@pytest.mark.seam("extraction")
@pytest.mark.seam("skill_registry")
@pytest.mark.anyio
async def test_explain_rejection_illegible():
    """Blurry bill (resubmit) → reason_code=illegible, message from yaml."""
    registry = LocalSkillRegistry()
    skill = registry._skills.get("address-proof")
    assert skill is not None
    explanations = load_explanations(skill)

    engine = FixtureExtractionEngine()
    from bridge.adapters.local.extraction import FixtureDocument

    extraction = await engine.extract(FixtureDocument(fixture_id="bill-aquautil-blurry"), None)
    entry, result = classify_document("bill-aquautil-blurry", extraction)

    code, msg = explain_rejection(entry, result.gate, explanations=explanations)

    assert entry.disposition == Disposition.REJECTED
    assert code == ILLEGIBLE
    assert msg == "This document was too blurry to read. Please resend a clearer copy."


@pytest.mark.seam("extraction")
@pytest.mark.seam("skill_registry")
@pytest.mark.anyio
async def test_explain_rejection_accepted():
    """Accepted doc → (None, None)."""
    registry = LocalSkillRegistry()
    skill = registry._skills.get("address-proof")
    assert skill is not None
    explanations = load_explanations(skill)

    engine = FixtureExtractionEngine()
    from bridge.adapters.local.extraction import FixtureDocument

    extraction = await engine.extract(FixtureDocument(fixture_id="gov-id-clean"), None)
    entry, result = classify_document("gov-id-clean", extraction)

    code, msg = explain_rejection(entry, result.gate, explanations=explanations)

    assert entry.disposition == Disposition.ACCEPTED
    assert code is None
    assert msg is None


# --------------------------------------------------------------------------- #
# load_explanations
# --------------------------------------------------------------------------- #


@pytest.mark.seam("skill_registry")
def test_load_explanations_real_file():
    """Loads the real skills/address-proof/assets/explanations.yaml."""
    registry = LocalSkillRegistry()
    skill = registry._skills.get("address-proof")
    assert skill is not None, "address-proof skill must be loaded"

    explanations = load_explanations(skill)

    assert explanations.item == "proof of address"
    assert explanations.doctype_hint == "gov-id"
    assert PROOF_REQUIRED in explanations.reasons
    assert DISTINCT_ISSUER_NEEDED in explanations.reasons
    assert UNSUPPORTED_DOCTYPE in explanations.reasons
    assert ILLEGIBLE in explanations.reasons


@pytest.mark.seam("skill_registry")
def test_load_explanations_missing_file():
    """Missing file yields empty reasons (no crash)."""
    from bridge.skills import Skill, SkillKind

    # Create a skill pointing at a missing file
    fake_skill = Skill(
        name="fake",
        description="fake",
        kind=SkillKind.PROCESS,
        metadata={},
        path=Path("/nonexistent"),
        policy=None,
        candidate_doctypes=(),
    )

    explanations = load_explanations(fake_skill)

    # Degrades gracefully: empty reasons
    assert explanations.item == ""
    assert explanations.doctype_hint is None
    assert explanations.reasons == {}
    assert explanations.message_for("anything") is None
