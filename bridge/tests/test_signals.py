"""Tests for disposition signal contract and providers (M1.6).

Pure unit tests (no async, no fixtures beyond inline construction). Build Extraction
objects inline using contract models (do not import agents).
"""

import pytest
from contract import ExtractedFields, Extraction

from bridge.signals import (
    CANDIDATE_DOCTYPES,
    DispositionSignals,
    ExtractionDerivedSignalProvider,
    Signal,
    SignalSource,
)


class TestExtractionDerivedProvider:
    """Tests for the extraction-derived signal provider."""

    def test_extraction_derived_provider_maps_signals(self):
        """ExtractionDerivedProvider maps type_match/legibility/confidence/fields_needing_review."""
        extraction = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            overall_confidence=0.96,
            legible=True,
            flagged_fields=["expiry"],
        )

        provider = ExtractionDerivedSignalProvider()
        signals = provider.signals(None, None, extraction)

        # type_match: gov-id is in CANDIDATE_DOCTYPES → 1.0
        assert signals.type_match is not None
        assert signals.type_match.value == 1.0
        assert signals.type_match.source == SignalSource.EXTRACTED
        assert signals.type_match.detail == "gov-id"

        # legibility: legible=True → 1.0
        assert signals.legibility is not None
        assert signals.legibility.value == 1.0
        assert signals.legibility.source == SignalSource.EXTRACTED

        # confidence: overall_confidence=0.96
        assert signals.confidence is not None
        assert signals.confidence.value == 0.96
        assert signals.confidence.source == SignalSource.EXTRACTED

        # fields_needing_review: flagged_fields=["expiry"]
        assert signals.fields_needing_review == ["expiry"]

        # completeness: sense B (app-owned), left None
        assert signals.completeness is None

    def test_type_match_uses_hardcoded_label_space(self):
        """Type_match uses the hard-coded CANDIDATE_DOCTYPES (locks lessons A8)."""
        # passport → type_match.value == 0.0 (not in candidate set)
        extraction_passport = Extraction(
            fields=ExtractedFields(doctype="passport"),
            overall_confidence=0.94,
            legible=True,
        )
        provider = ExtractionDerivedSignalProvider()
        signals_passport = provider.signals(None, None, extraction_passport)

        assert signals_passport.type_match is not None
        assert signals_passport.type_match.value == 0.0
        assert signals_passport.type_match.detail == "passport"

        # gov-id → type_match.value == 1.0 (in candidate set)
        extraction_govid = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            overall_confidence=0.96,
            legible=True,
        )
        signals_govid = provider.signals(None, None, extraction_govid)

        assert signals_govid.type_match is not None
        assert signals_govid.type_match.value == 1.0
        assert signals_govid.type_match.detail == "gov-id"

        # utility-bill → type_match.value == 1.0 (in candidate set)
        extraction_bill = Extraction(
            fields=ExtractedFields(doctype="utility-bill", issuer="power-co"),
            overall_confidence=0.97,
            legible=True,
        )
        signals_bill = provider.signals(None, None, extraction_bill)

        assert signals_bill.type_match is not None
        assert signals_bill.type_match.value == 1.0
        assert signals_bill.type_match.detail == "utility-bill"

    def test_legibility_signal(self):
        """Legibility signal maps from extraction.legible."""
        provider = ExtractionDerivedSignalProvider()

        # legible=True → signal.value=1.0
        extraction_legible = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            legible=True,
        )
        signals_legible = provider.signals(None, None, extraction_legible)
        assert signals_legible.legibility is not None
        assert signals_legible.legibility.value == 1.0

        # legible=False → signal.value=0.0
        extraction_illegible = Extraction(
            fields=ExtractedFields(doctype="utility-bill", issuer="aqua-util"),
            legible=False,
        )
        signals_illegible = provider.signals(None, None, extraction_illegible)
        assert signals_illegible.legibility is not None
        assert signals_illegible.legibility.value == 0.0

        # legible=None → signal=None (not evaluated)
        extraction_no_legibility = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            legible=None,
        )
        signals_no_legibility = provider.signals(None, None, extraction_no_legibility)
        assert signals_no_legibility.legibility is None

    def test_confidence_signal(self):
        """Confidence signal maps from extraction.overall_confidence."""
        provider = ExtractionDerivedSignalProvider()

        # overall_confidence=0.96 → signal.value=0.96
        extraction_high = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            overall_confidence=0.96,
        )
        signals_high = provider.signals(None, None, extraction_high)
        assert signals_high.confidence is not None
        assert signals_high.confidence.value == 0.96

        # overall_confidence=0.30 → signal.value=0.30
        extraction_low = Extraction(
            fields=ExtractedFields(doctype="utility-bill", issuer="aqua-util"),
            overall_confidence=0.30,
        )
        signals_low = provider.signals(None, None, extraction_low)
        assert signals_low.confidence is not None
        assert signals_low.confidence.value == 0.30

        # overall_confidence=None → signal=None (not evaluated)
        extraction_no_confidence = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            overall_confidence=None,
        )
        signals_no_confidence = provider.signals(None, None, extraction_no_confidence)
        assert signals_no_confidence.confidence is None

    def test_fields_needing_review(self):
        """fields_needing_review maps from extraction.flagged_fields."""
        provider = ExtractionDerivedSignalProvider()

        # flagged_fields=["expiry"] → fields_needing_review=["expiry"]
        extraction_flagged = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            flagged_fields=["expiry"],
        )
        signals_flagged = provider.signals(None, None, extraction_flagged)
        assert signals_flagged.fields_needing_review == ["expiry"]

        # flagged_fields=[] → fields_needing_review=[]
        extraction_no_flags = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            flagged_fields=[],
        )
        signals_no_flags = provider.signals(None, None, extraction_no_flags)
        assert signals_no_flags.fields_needing_review == []

    def test_completeness_is_none(self):
        """Completeness is None (sense B excluded — app-owned, not Bridge-owned)."""
        extraction = Extraction(
            fields=ExtractedFields(doctype="gov-id"),
            overall_confidence=0.96,
            legible=True,
        )

        provider = ExtractionDerivedSignalProvider()
        signals = provider.signals(None, None, extraction)

        # completeness: sense B (app-owned), left unpopulated
        assert signals.completeness is None


class TestSignalsShape:
    """Tests for the signal shape and immutability (ADR-0004)."""

    def test_signals_frozen_extra_forbid(self):
        """DispositionSignals(bogus=1) raises; instances are immutable."""
        # extra="forbid" — adding unknown fields raises
        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            DispositionSignals(bogus=1)

        # frozen=True — instances are immutable
        signals = DispositionSignals()
        with pytest.raises(ValueError, match="Instance is frozen"):
            signals.legibility = Signal(value=1.0, source=SignalSource.MOCK)

    def test_signal_frozen(self):
        """Signal instances are immutable (frozen=True)."""
        signal = Signal(value=1.0, source=SignalSource.EXTRACTED)
        with pytest.raises(ValueError, match="Instance is frozen"):
            signal.value = 0.5

    def test_candidate_doctypes_hardcoded(self):
        """CANDIDATE_DOCTYPES is a tuple of exactly 2 strings (gov-id, utility-bill)."""
        assert CANDIDATE_DOCTYPES == ("gov-id", "utility-bill")
        assert isinstance(CANDIDATE_DOCTYPES, tuple)
