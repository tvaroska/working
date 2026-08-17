"""Signal contract and providers for disposition (ADR-0004, M1.6).

The four-signal disposition contract (ADR-0004) separates signal **gathering** from
**routing** so the gate logic can be tested independently of extraction engines and
stay engine-agnostic. Each signal is a named value object (value + source + detail);
signals are gathered by a provider and passed to the gate.

Phase 1 ships exactly **one** provider: ``ExtractionDerivedSignalProvider`` (populates
legibility, type_match, confidence, and fields_needing_review from an extraction; leaves
completeness unpopulated — sense B is the app's, not the Bridge's). The contract is
fixed from day one to support swappable providers (e.g., four-signal providers in
Phase 4 that add reported/computed signals).

**Hard-coded label space (lessons A8).** ``CANDIDATE_DOCTYPES`` is deliberately
hard-coded in the core, not skill-derived. The address-proof skill *also* carries
``bridge-candidate-doctypes: "gov-id utility-bill"``, but A8 is explicit: making it
skill-derived is a **separate coordinated change** that would break the sense-A tests.

Import discipline: imports ``contract`` only. Never imports ``agents`` or ``seams``.
Keep it out of ``bridge/__init__.py`` (preserve cheap ``import bridge`` + the
no-agents-guard clarity, same rule ``aggregate.py``/``ledger.py`` follow).
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from contract import Extraction

__all__ = [
    "CANDIDATE_DOCTYPES",
    "DispositionSignals",
    "ExtractionDerivedSignalProvider",
    "Signal",
    "SignalProvider",
    "SignalSource",
]

#: Hard-coded label space for Phase 1 (lessons A8 — the "honesty trap").
#: The address-proof skill also carries bridge-candidate-doctypes, but the core's
#: label space is deliberately hard-coded. Making it skill-derived is a separate
#: coordinated change.
CANDIDATE_DOCTYPES: tuple[str, ...] = ("gov-id", "utility-bill")


class SignalSource(StrEnum):
    """Provenance of a disposition signal (ADR-0004).

    EXTRACTED: derived from an extraction engine (Gemini, DocAI).
    REPORTED: self-reported by a party (Path-A structured response).
    COMPUTED: calculated by the Bridge (completeness over the ledger).
    MOCK: test/fixture value.
    """

    EXTRACTED = "extracted"
    REPORTED = "reported"
    COMPUTED = "computed"
    MOCK = "mock"


class Signal(BaseModel, frozen=True):
    """One disposition signal: value + source + optional detail (ADR-0004).

    A signal is an immutable value object carrying:
    - value: float (0.0–1.0 for legibility/type_match/confidence/completeness) or str
    - source: SignalSource (provenance)
    - detail: optional string (e.g., the classified doctype for type_match)
    """

    value: float | str
    source: SignalSource
    detail: str | None = None


class DispositionSignals(BaseModel, frozen=True):
    """The four-signal disposition contract (ADR-0004).

    Fixed shape from day one to support swappable providers. Phase 1 ships one provider
    (extraction-derived), which populates legibility/type_match/confidence and leaves
    completeness unpopulated (sense B is the app's, not the Bridge's).

    Signals:
    - legibility: can the document be read? (0.0 = illegible, 1.0 = legible)
    - type_match: does the doctype match the skill's label space? (0.0 = no, 1.0 = yes)
    - confidence: overall extraction confidence (0.0–1.0)
    - completeness: is the collection done? (sense B — app-owned, not Bridge-owned)
    - fields_needing_review: list of field names flagged for review (e.g., ["expiry"])
    - failed_rules: list of rule names that failed (e.g., ["unexpired"])

    Absent signal (None) = "not evaluated", not "failed". The gate treats absence
    conservatively (e.g., no confidence → cannot auto-approve).
    """

    model_config = {"extra": "forbid"}

    legibility: Signal | None = None
    type_match: Signal | None = None
    confidence: Signal | None = None
    fields_needing_review: list[str] = Field(default_factory=list)
    completeness: Signal | None = None
    failed_rules: list[str] = Field(default_factory=list)


class SignalProvider(Protocol):
    """Protocol for disposition signal providers (ADR-0004).

    A provider gathers signals from various sources (extraction engines, party reports,
    Bridge computations) and returns a DispositionSignals value object. Phase 1 ships
    one provider (extraction-derived); the Protocol enables swappable providers in
    later phases.

    Note: This is a plain Protocol, **not** one of the six managed-service seams
    (sessions, task_store, exchange_store, skill_registry, scheduler, extraction).
    Do not add it to bridge/seams/ or add a @pytest.mark.seam marker.
    """

    def signals(
        self,
        document: object,
        doctype_skill: object,
        extraction_result: Extraction,
    ) -> DispositionSignals:
        """Gather disposition signals from the given inputs.

        Args:
            document: The document artifact (placeholder; M1.7 concretizes it).
            doctype_skill: The doctype skill (placeholder; M1.7 concretizes it).
            extraction_result: The extraction payload.

        Returns:
            The gathered disposition signals.
        """
        ...


class ExtractionDerivedSignalProvider:
    """Extraction-derived signal provider (Phase 1).

    Populates legibility, type_match, confidence, and fields_needing_review from the
    extraction payload. Leaves completeness unpopulated (sense B — the app's "done"
    decision, not the Bridge's).

    Implements the SignalProvider protocol.
    """

    def signals(
        self,
        document: object,
        doctype_skill: object,
        extraction_result: Extraction,
    ) -> DispositionSignals:
        """Gather signals from the extraction payload.

        Args:
            document: Unused (placeholder for M1.7).
            doctype_skill: Unused (placeholder for M1.7).
            extraction_result: The extraction payload.

        Returns:
            DispositionSignals with legibility/type_match/confidence/fields_needing_review
            populated from the extraction; completeness left None (sense B).
        """
        # type_match: does the extracted doctype match the hard-coded label space?
        type_match = Signal(
            value=1.0 if extraction_result.fields.doctype in CANDIDATE_DOCTYPES else 0.0,
            source=SignalSource.EXTRACTED,
            detail=extraction_result.fields.doctype,
        )

        # legibility: can the document be read?
        legibility = None
        if extraction_result.legible is not None:
            legibility = Signal(
                value=1.0 if extraction_result.legible else 0.0,
                source=SignalSource.EXTRACTED,
            )

        # confidence: overall extraction confidence
        confidence = None
        if extraction_result.overall_confidence is not None:
            confidence = Signal(
                value=extraction_result.overall_confidence,
                source=SignalSource.EXTRACTED,
            )

        # fields_needing_review: flagged fields from extraction
        fields_needing_review = list(extraction_result.flagged_fields)

        # completeness: sense B (app-owned), left unpopulated
        completeness = None

        return DispositionSignals(
            legibility=legibility,
            type_match=type_match,
            confidence=confidence,
            fields_needing_review=fields_needing_review,
            completeness=completeness,
        )
