"""Disposition + classification gate (M1.6).

**Deterministic, pure** sense-A verdict per artifact: classify the doctype against the
hard-coded label space, read the extraction-derived signals, route on the skill-policy
confidence thresholds, and produce a Disposition + a routing Gate + flags. **A model
never mints this verdict** — it is code, exposed as an authoritative function (lessons
A3, ADR-0001).

The gate routing algorithm (ORDER MATTERS — see acceptance tests):
1. **type_match** — if doctype ∉ candidate set → gate=unsupported, disposition=rejected.
   (Must be first: passport is legible/high-conf but must be unsupported, not auto_approve.)
2. **quality gate** — if legible is False OR overall_confidence < resubmit_below (0.55) →
   gate=resubmit, disposition=rejected.
3. **confidence gate** — if overall_confidence >= auto_approve_at (0.85) AND no flags →
   gate=auto_approve, disposition=accepted.
4. **else** → gate=hitl_review, disposition=pending. (Catches: 0.55 ≤ conf < 0.85 with
   no flags, e.g. bill-aquautil-clear 0.72; and conf ≥ 0.85 WITH flags, e.g.
   gov-id-expired flagged expiry.)

Thresholds come from the skill policy (ADR-0002). The extraction engine (M1.7)
pre-computes legible and flagged_fields (the "unexpired?" rule already surfaces as
flagged_fields=["expiry"]) — M1.6 does NOT parse dates or run validation.yaml date math.

Issuer canonicalization (M1.5): classify_document calls canonicalize_issuer when
building the LedgerEntry. The fixture extractions already carry canonical fields.issuer
("power-co"), but the real flow (M1.7) will produce raw issuers; idempotency makes this
safe for both.

See:
- ADR-0002 (disposition thresholds: 0.55 resubmit / 0.85 auto-approve)
- ADR-0004 (four-signal contract)
- lessons A3 (code decides, model never mints acceptance)
- lessons A8 (hard-coded label space)

Import discipline: imports contract + bridge.{canonical, signals, skills} only.
Never imports agents or seams. Keep it out of bridge/__init__.py (preserve cheap
import bridge + the no-agents-guard clarity).
"""

from __future__ import annotations

from enum import StrEnum

from contract import Disposition, Extraction, LedgerEntry
from pydantic import BaseModel, Field

from bridge.canonical import canonicalize_issuer
from bridge.signals import DispositionSignals, ExtractionDerivedSignalProvider, SignalProvider
from bridge.skills import DispositionThresholds

__all__ = [
    "DispositionResult",
    "Gate",
    "classify_document",
    "run_disposition_gate",
]


class Gate(StrEnum):
    """Routing gate outcome for a disposition verdict.

    The gate determines the next step in the fulfillment graph (M1.7):
    - AUTO_APPROVE: accepted, no human review needed.
    - HITL_REVIEW: pending, awaits human review.
    - RESUBMIT: rejected, party must resubmit (quality issue).
    - UNSUPPORTED: rejected, doctype not in the label space.

    Values MUST match the expected_gate strings in wiki/evals/address/expected.json.
    """

    AUTO_APPROVE = "auto_approve"
    HITL_REVIEW = "hitl_review"
    RESUBMIT = "resubmit"
    UNSUPPORTED = "unsupported"


class DispositionResult(BaseModel, frozen=True):
    """The disposition verdict: disposition + gate + flags + signals.

    Returned by run_disposition_gate and classify_document. The gate is used for M1.7
    routing; the disposition is stamped into the LedgerEntry; flags and signals are
    preserved for debugging and future enhancements.
    """

    model_config = {"extra": "forbid"}

    disposition: Disposition
    gate: Gate
    flags: list[str] = Field(default_factory=list)
    signals: DispositionSignals


def run_disposition_gate(
    signals: DispositionSignals,
    *,
    thresholds: DispositionThresholds = DispositionThresholds(),
) -> DispositionResult:
    """Run the deterministic disposition gate over signals (pure function).

    Implements the 4-step ordered algorithm (ORDER MATTERS — type_match must be first,
    quality gate second, confidence gate third). Reads signals.type_match.value,
    signals.legibility.value, signals.confidence.value, and
    signals.fields_needing_review. Treats a None confidence conservatively: cannot
    auto-approve → falls through to hitl_review (only matters off-fixture).

    Args:
        signals: The gathered disposition signals.
        thresholds: Disposition thresholds (resubmit_below, auto_approve_at).
            Defaults to DispositionThresholds() (0.55, 0.85).

    Returns:
        The disposition result (disposition + gate + flags + signals).

    Note:
        This function is **pure** (no I/O, no randomness) — a model can never mint a
        KYC acceptance (lessons A3). Same signals in → same result out.
    """
    flags = signals.fields_needing_review.copy()

    # Step 1: type_match — unsupported doctype beats everything else
    # (Must be first: passport is legible/high-conf but must be unsupported, not auto_approve)
    if signals.type_match is not None and signals.type_match.value == 0.0:
        return DispositionResult(
            disposition=Disposition.REJECTED,
            gate=Gate.UNSUPPORTED,
            flags=flags,
            signals=signals,
        )

    # Step 2: quality gate — illegible or below resubmit threshold
    # (legible is False OR overall_confidence < resubmit_below)
    legible = True
    if signals.legibility is not None:
        legible = signals.legibility.value == 1.0

    confidence = signals.confidence.value if signals.confidence is not None else None

    if not legible or (confidence is not None and confidence < thresholds.resubmit_below):
        return DispositionResult(
            disposition=Disposition.REJECTED,
            gate=Gate.RESUBMIT,
            flags=flags,
            signals=signals,
        )

    # Step 3: confidence gate — high confidence + no flags → auto-approve
    # (overall_confidence >= auto_approve_at AND no flagged fields)
    if confidence is not None and confidence >= thresholds.auto_approve_at and not flags:
        return DispositionResult(
            disposition=Disposition.ACCEPTED,
            gate=Gate.AUTO_APPROVE,
            flags=flags,
            signals=signals,
        )

    # Step 4: else → hitl_review (catches mid-range confidence, or high conf with flags)
    # This catches:
    # - 0.55 ≤ conf < 0.85 with no flags (e.g., bill-aquautil-clear 0.72)
    # - conf ≥ 0.85 WITH flags (e.g., gov-id-expired flagged expiry)
    # - no confidence (conservatively cannot auto-approve)
    return DispositionResult(
        disposition=Disposition.PENDING,
        gate=Gate.HITL_REVIEW,
        flags=flags,
        signals=signals,
    )


def classify_document(
    doc_id: str,
    extraction: Extraction,
    *,
    thresholds: DispositionThresholds = DispositionThresholds(),
    provider: SignalProvider | None = None,
) -> tuple[LedgerEntry, DispositionResult]:
    """Classify a document and record it into the ledger with canonical issuer.

    The "record each doc into the ledger with its canonical issuer" step:
    1. Gather signals from the extraction (via provider).
    2. Run the disposition gate.
    3. Canonicalize the issuer (M1.5 — idempotent for both raw and pre-canonical).
    4. Build a LedgerEntry.
    5. Return (entry, result).

    The gate is returned via result for M1.7 routing; LedgerEntry has no gate field.

    Args:
        doc_id: The document identifier.
        extraction: The extraction payload.
        thresholds: Disposition thresholds (resubmit_below, auto_approve_at).
            Defaults to DispositionThresholds() (0.55, 0.85).
        provider: Signal provider. Defaults to ExtractionDerivedSignalProvider().

    Returns:
        A tuple of (LedgerEntry, DispositionResult).

    Note:
        Keep run_disposition_gate (routing over signals) and classify_document
        (provider + canonicalize + build entry) separate so the routing core stays
        engine-agnostic (ADR-0004).
    """
    # Step 1: gather signals
    if provider is None:
        provider = ExtractionDerivedSignalProvider()
    signals = provider.signals(None, None, extraction)

    # Step 2: run the disposition gate
    result = run_disposition_gate(signals, thresholds=thresholds)

    # Step 3: canonicalize the issuer (M1.5 — idempotent)
    issuer = canonicalize_issuer(extraction.fields.issuer)

    # Step 4: build the ledger entry
    entry = LedgerEntry(
        id=doc_id,
        doctype=extraction.fields.doctype,
        issuer=issuer,
        disposition=result.disposition,
        extraction=extraction,
    )

    # Step 5: return (entry, result)
    return (entry, result)
