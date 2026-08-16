"""Tests for disposition + classification gate (M1.6).

Golden parity tests against wiki/evals/address/expected.json are the primary acceptance
criterion. Build Extraction objects inline or from the eval JSON (do not import agents).
"""

import asyncio
import json
import os
from pathlib import Path

import pytest
from contract import Disposition, ExtractedFields, Extraction

from bridge.adapters.local import LocalSkillRegistry
from bridge.disposition import DispositionResult, Gate, classify_document, run_disposition_gate
from bridge.signals import DispositionSignals, Signal, SignalSource


class TestGateParity:
    """Golden parity tests: reproduce expected_disposition and expected_gate for all fixtures."""

    @staticmethod
    def resolve_evals_path() -> Path:
        """Resolve the path to wiki/evals/address/expected.json.

        Walks up from this file's directory to the first ancestor containing
        wiki/evals/address/expected.json. Mirrors the pattern in
        bridge/src/bridge/skills.py::resolve_default_skills_dir and
        test_canonical.py::resolve_evals_path.

        Honors an ADDRESS_EVALS_PATH env override for parity with the mock
        (agents/src/agents/mock_bridge/fixtures.py).

        Returns:
            The resolved path to the evals fixture.

        Raises:
            FileNotFoundError: If the fixture file is not found.
        """
        # Check for env override first
        if env_path := os.environ.get("ADDRESS_EVALS_PATH"):
            path = Path(env_path)
            if path.exists():
                return path
            raise FileNotFoundError(f"ADDRESS_EVALS_PATH={env_path} does not exist")

        # Walk up from this file's directory
        current = Path(__file__).resolve().parent
        for ancestor in [current] + list(current.parents):
            candidate = ancestor / "wiki" / "evals" / "address" / "expected.json"
            if candidate.exists():
                return candidate

        raise FileNotFoundError(
            "wiki/evals/address/expected.json not found in any ancestor directory"
        )

    def test_gate_parity_all_fixtures(self):
        """Assert expected_disposition AND expected_gate for all 8 fixtures (M1.6 acceptance)."""
        fixture_path = self.resolve_evals_path()

        with fixture_path.open() as f:
            data = json.load(f)

        documents = data["documents"]

        # Load thresholds from the address-proof skill policy (ADR-0002)
        registry = LocalSkillRegistry()
        skill = asyncio.run(registry.get_skill("address-proof"))
        assert skill is not None, "address-proof skill not found"
        assert skill.policy is not None, "address-proof skill has no policy"
        thresholds = skill.policy.thresholds

        # Verify the thresholds are as expected (0.55, 0.85)
        assert thresholds.resubmit_below == 0.55
        assert thresholds.auto_approve_at == 0.85

        # For each fixture, assert expected_disposition AND expected_gate
        for doc in documents:
            doc_id = doc["id"]
            extraction = Extraction.model_validate(doc["extraction"])
            expected_disposition = Disposition(doc["expected_disposition"])
            expected_gate = doc["expected_gate"]

            # Classify the document
            entry, result = classify_document(doc_id, extraction, thresholds=thresholds)

            # Assert disposition parity
            assert entry.disposition == expected_disposition, (
                f"Disposition mismatch for {doc_id}: "
                f"expected={expected_disposition}, got={entry.disposition}"
            )

            # Assert gate parity
            assert (
                result.gate.value == expected_gate
            ), f"Gate mismatch for {doc_id}: expected={expected_gate}, got={result.gate.value}"

    def test_gate_parity_individual_fixtures(self):
        """Explicitly test each fixture individually (documentation + debugging aid)."""
        fixture_path = self.resolve_evals_path()

        with fixture_path.open() as f:
            data = json.load(f)

        documents = {doc["id"]: doc for doc in data["documents"]}

        # Use the skill policy thresholds
        registry = LocalSkillRegistry()
        skill = asyncio.run(registry.get_skill("address-proof"))
        thresholds = skill.policy.thresholds

        # gov-id-clean: auto_approve → accepted
        doc = documents["gov-id-clean"]
        extraction = Extraction.model_validate(doc["extraction"])
        entry, result = classify_document("gov-id-clean", extraction, thresholds=thresholds)
        assert entry.disposition == Disposition.ACCEPTED
        assert result.gate == Gate.AUTO_APPROVE

        # gov-id-expired: hitl_review → pending (flagged expiry)
        doc = documents["gov-id-expired"]
        extraction = Extraction.model_validate(doc["extraction"])
        entry, result = classify_document("gov-id-expired", extraction, thresholds=thresholds)
        assert entry.disposition == Disposition.PENDING
        assert result.gate == Gate.HITL_REVIEW

        # bill-powerco-clean: auto_approve → accepted
        doc = documents["bill-powerco-clean"]
        extraction = Extraction.model_validate(doc["extraction"])
        entry, result = classify_document("bill-powerco-clean", extraction, thresholds=thresholds)
        assert entry.disposition == Disposition.ACCEPTED
        assert result.gate == Gate.AUTO_APPROVE

        # bill-powerco-clean-2: auto_approve → accepted
        doc = documents["bill-powerco-clean-2"]
        extraction = Extraction.model_validate(doc["extraction"])
        entry, result = classify_document("bill-powerco-clean-2", extraction, thresholds=thresholds)
        assert entry.disposition == Disposition.ACCEPTED
        assert result.gate == Gate.AUTO_APPROVE

        # bill-aquautil-clean: auto_approve → accepted
        doc = documents["bill-aquautil-clean"]
        extraction = Extraction.model_validate(doc["extraction"])
        entry, result = classify_document("bill-aquautil-clean", extraction, thresholds=thresholds)
        assert entry.disposition == Disposition.ACCEPTED
        assert result.gate == Gate.AUTO_APPROVE

        # bill-aquautil-clear: hitl_review → pending (mid-range confidence 0.72)
        doc = documents["bill-aquautil-clear"]
        extraction = Extraction.model_validate(doc["extraction"])
        entry, result = classify_document("bill-aquautil-clear", extraction, thresholds=thresholds)
        assert entry.disposition == Disposition.PENDING
        assert result.gate == Gate.HITL_REVIEW

        # bill-aquautil-blurry: resubmit → rejected (illegible)
        doc = documents["bill-aquautil-blurry"]
        extraction = Extraction.model_validate(doc["extraction"])
        entry, result = classify_document("bill-aquautil-blurry", extraction, thresholds=thresholds)
        assert entry.disposition == Disposition.REJECTED
        assert result.gate == Gate.RESUBMIT

        # passport-unsupported: unsupported → rejected (outside label space)
        doc = documents["passport-unsupported"]
        extraction = Extraction.model_validate(doc["extraction"])
        entry, result = classify_document("passport-unsupported", extraction, thresholds=thresholds)
        assert entry.disposition == Disposition.REJECTED
        assert result.gate == Gate.UNSUPPORTED


class TestLedgerEntryCanonicalIssuer:
    """Test that classify_document applies issuer canonicalization (M1.5)."""

    def test_ledger_entry_canonical_issuer(self):
        """LedgerEntry.issuer is the canonical issuer (M1.5 applied on record)."""
        # Feed an Extraction with fields.issuer="PowerCo" (raw)
        extraction_raw = Extraction(
            fields=ExtractedFields(doctype="utility-bill", issuer="PowerCo"),
            overall_confidence=0.97,
            legible=True,
        )

        entry, result = classify_document("doc-1", extraction_raw)

        # Assert the entry has the canonical issuer
        assert entry.issuer == "power-co"

    def test_ledger_entry_canonical_issuer_precanonical(self):
        """Canonicalization is idempotent (pre-canonical issuer → same)."""
        # Feed an Extraction with fields.issuer="power-co" (already canonical)
        extraction_canonical = Extraction(
            fields=ExtractedFields(doctype="utility-bill", issuer="power-co"),
            overall_confidence=0.97,
            legible=True,
        )

        entry, result = classify_document("doc-1", extraction_canonical)

        # Assert the entry still has the canonical issuer
        assert entry.issuer == "power-co"

    def test_ledger_entry_govid_issuer_none(self):
        """gov-id has issuer=None → canonicalize_issuer(None) returns None."""
        extraction_govid = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            overall_confidence=0.96,
            legible=True,
        )

        entry, result = classify_document("doc-1", extraction_govid)

        # Assert the entry has issuer=None
        assert entry.issuer is None


class TestGateOrderingEdges:
    """Test gate ordering edge cases (ORDER MATTERS)."""

    def test_unsupported_beats_quality(self):
        """Unsupported doctype beats quality gate (illegible passport → unsupported)."""
        # Build an illegible passport (legible=False, conf=0.30)
        extraction = Extraction(
            fields=ExtractedFields(doctype="passport", issuer="gov"),
            overall_confidence=0.30,
            legible=False,
        )

        entry, result = classify_document("doc-1", extraction)

        # Should be unsupported (type_match beats quality)
        assert result.gate == Gate.UNSUPPORTED
        assert entry.disposition == Disposition.REJECTED

    def test_flags_block_auto_approve(self):
        """Flagged fields block auto-approve (conf 0.99 + flagged → hitl_review)."""
        # Build a high-confidence extraction with flagged fields
        extraction = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            overall_confidence=0.99,
            legible=True,
            flagged_fields=["expiry"],
        )

        entry, result = classify_document("doc-1", extraction)

        # Should be hitl_review (flags block auto-approve)
        assert result.gate == Gate.HITL_REVIEW
        assert entry.disposition == Disposition.PENDING
        assert result.flags == ["expiry"]

    def test_boundary_at_auto_approve(self):
        """Boundary at auto_approve_at (0.85): at 0.85 with no flags → auto_approve."""
        extraction = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            overall_confidence=0.85,
            legible=True,
            flagged_fields=[],
        )

        entry, result = classify_document("doc-1", extraction)

        # Should be auto_approve (at the boundary)
        assert result.gate == Gate.AUTO_APPROVE
        assert entry.disposition == Disposition.ACCEPTED

    def test_boundary_just_below_auto_approve(self):
        """Just below auto_approve_at (0.849): hitl_review."""
        extraction = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            overall_confidence=0.849,
            legible=True,
            flagged_fields=[],
        )

        entry, result = classify_document("doc-1", extraction)

        # Should be hitl_review (below the boundary)
        assert result.gate == Gate.HITL_REVIEW
        assert entry.disposition == Disposition.PENDING

    def test_boundary_at_resubmit(self):
        """Boundary at resubmit_below (0.55): at 0.55 → hitl_review, below 0.55 → resubmit."""
        # At 0.55 → hitl_review
        extraction_at = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            overall_confidence=0.55,
            legible=True,
            flagged_fields=[],
        )

        entry_at, result_at = classify_document("doc-1", extraction_at)

        # Should be hitl_review (at the boundary, not below)
        assert result_at.gate == Gate.HITL_REVIEW
        assert entry_at.disposition == Disposition.PENDING

        # Strictly below 0.55 → resubmit
        extraction_below = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            overall_confidence=0.549,
            legible=True,
            flagged_fields=[],
        )

        entry_below, result_below = classify_document("doc-1", extraction_below)

        # Should be resubmit (below the boundary)
        assert result_below.gate == Gate.RESUBMIT
        assert entry_below.disposition == Disposition.REJECTED


class TestRunDispositionGatePure:
    """Test that run_disposition_gate is pure (no I/O, no randomness)."""

    def test_run_disposition_gate_pure(self):
        """Same DispositionSignals in → same DispositionResult out (documents A3)."""
        # Build a DispositionSignals instance
        signals = DispositionSignals(
            legibility=Signal(value=1.0, source=SignalSource.EXTRACTED),
            type_match=Signal(value=1.0, source=SignalSource.EXTRACTED, detail="gov-id"),
            confidence=Signal(value=0.96, source=SignalSource.EXTRACTED),
            fields_needing_review=[],
        )

        # Run the gate multiple times
        result1 = run_disposition_gate(signals)
        result2 = run_disposition_gate(signals)

        # Should be identical
        assert result1.disposition == result2.disposition
        assert result1.gate == result2.gate
        assert result1.flags == result2.flags
        assert result1.signals == result2.signals

    def test_run_disposition_gate_no_io(self):
        """run_disposition_gate is a pure function (no I/O, no side effects)."""
        # Build signals
        signals = DispositionSignals(
            legibility=Signal(value=1.0, source=SignalSource.EXTRACTED),
            type_match=Signal(value=1.0, source=SignalSource.EXTRACTED, detail="utility-bill"),
            confidence=Signal(value=0.72, source=SignalSource.EXTRACTED),
            fields_needing_review=[],
        )

        # Run the gate
        result = run_disposition_gate(signals)

        # Should return a result (no exceptions, no I/O)
        assert result.disposition == Disposition.PENDING
        assert result.gate == Gate.HITL_REVIEW

    def test_none_confidence_conservative(self):
        """None confidence is treated conservatively (cannot auto-approve → hitl_review)."""
        signals = DispositionSignals(
            legibility=Signal(value=1.0, source=SignalSource.EXTRACTED),
            type_match=Signal(value=1.0, source=SignalSource.EXTRACTED, detail="gov-id"),
            confidence=None,  # No confidence signal
            fields_needing_review=[],
        )

        result = run_disposition_gate(signals)

        # Should be hitl_review (conservative: cannot auto-approve without confidence)
        assert result.gate == Gate.HITL_REVIEW
        assert result.disposition == Disposition.PENDING


class TestDispositionResultShape:
    """Test the DispositionResult shape (ADR-0004, extra="forbid", frozen=True)."""

    def test_disposition_result_frozen_extra_forbid(self):
        """DispositionResult(bogus=1) raises; instances are immutable."""
        signals = DispositionSignals()

        # extra="forbid" — adding unknown fields raises
        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            DispositionResult(
                disposition=Disposition.ACCEPTED,
                gate=Gate.AUTO_APPROVE,
                signals=signals,
                bogus=1,
            )

        # frozen=True — instances are immutable
        result = DispositionResult(
            disposition=Disposition.ACCEPTED,
            gate=Gate.AUTO_APPROVE,
            signals=signals,
        )
        with pytest.raises(ValueError, match="Instance is frozen"):
            result.disposition = Disposition.REJECTED
