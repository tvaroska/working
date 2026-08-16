"""Path-B fulfillment graph (M1.7).

The durable pipeline the Bridge runs when a **human** party uploads a document:
    receive → extract_with_quality_gate → confidence_gate →
    {auto_approve | hitl_review | escalate | extraction_error}

with a **resubmission loop ≤ 3** (resubmit **non-resumable** — A1) and HITL
**suspending with zero compute** (resumable phases = {hitl, escalated}).

DESIGN DECISION (load-bearing — do NOT re-derive):
This is a **deterministic Python state machine, NOT a google.adk.workflow.Workflow**.

Rationale:
- The Bridge-core sense-A pipeline is "code decides" deterministic logic (extract → gate
  → disposition). Every existing bridge/ module (disposition.py, ledger.py, aggregate.py,
  signals.py) is a pure/deterministic module, not an ADK runtime construct. Match that idiom.
- The quality gate + confidence gate + thresholds are **already** run_disposition_gate (M1.6).
  This graph must NOT re-implement thresholds — it is a thin router over the returned Gate
  plus loop/suspend/attempt state. (Single-source the gate; duplicating it breaks parity.)
- The *durable-graph-with-suspend/resume* mechanism was already proven on the **consumer**
  side in S1-6 (google.adk.workflow.Workflow + DatabaseSessionService + ResumabilityConfig,
  see agents/src/agents/address/graph.py, PLAN.md S1-6). Re-proving it inside bridge/ is
  redundant and out of proportion for this task. M1.7 depends only on M1.1 + M1.6 — **not**
  M1.2 stores / sessions — which confirms it is not meant to wire an ADK runtime.
- "Durable" and "zero compute while suspended" are naturally satisfied by a pure state
  machine: it returns a *suspended* result and nobody calls it again until an event
  (human decision, or a fresh document) arrives. Its state is designed **JSON-serializable**
  so the M1.8/M1.11 edge can carry it on the durable task (parity with how M1.4 stamps
  LedgerEntry on task.metadata via bridge.ledger.stamp_ledger_entry) — but the carry/wiring
  is the edge's job, out of M1.7 scope.
- ADK-native binding of the suspend points (HITL as LongRunningFunctionTool, uploads as
  versioned ADK artifacts, resume via webhook — platform bet 1, wiki/bridge-fulfillment-graph.md)
  happens at the **edge** (M1.8/M1.10/M1.11), not in this deterministic core.

See:
- wiki/bridge-fulfillment-graph.md (graph shape)
- ADR-0005 (extraction is a seam)
- lessons A1 (resubmit non-resumable / escalation ≠ rejection)
- bridge/tests/test_fulfillment.py (acceptance tests)

Import discipline: imports contract + bridge.disposition + bridge.skills (types only) +
bridge.seams.extraction (seam interface). Does NOT import bridge.adapters (dependency
direction is adapters → core; the graph is engine-agnostic and receives the engine by
parameter). Never imports agents. Keep it out of bridge/__init__.py (preserve cheap
import bridge + the no-agents-guard clarity).
"""

from __future__ import annotations

from enum import StrEnum

from contract import Disposition, LedgerEntry
from pydantic import BaseModel

from bridge.disposition import Gate, classify_document
from bridge.seams.extraction import ExtractionError, ExtractionSeam
from bridge.skills import DispositionThresholds

__all__ = [
    "Phase",
    "RESUMABLE_PHASES",
    "TERMINAL_PHASES",
    "FulfillmentResult",
    "run_fulfillment",
    "resume_fulfillment",
]


class Phase(StrEnum):
    """Fulfillment graph phase.

    The phase determines the next step in the Path-B pipeline:
    - AUTO_APPROVE: accepted, no human review needed.
    - HITL: pending, awaits human review (resumable).
    - RESUBMIT: rejected, party must resubmit (non-resumable — awaits fresh document).
    - ESCALATED: pending, loop exhausted (resumable).
    - EXTRACTION_ERROR: pending, engine fault (terminal, non-resumable).
    - UNSUPPORTED: rejected, doctype not in the label space (terminal).
    - REJECTED: rejected, human/escalation decision (terminal).

    Values chosen to read cleanly in the read-model; hitl/escalated match A1's
    vocabulary.
    """

    AUTO_APPROVE = "auto_approve"
    HITL = "hitl"
    RESUBMIT = "resubmit"
    ESCALATED = "escalated"
    EXTRACTION_ERROR = "extraction_error"
    UNSUPPORTED = "unsupported"
    REJECTED = "rejected"


# Resumable phases: can be decision-resumed via resume_fulfillment (A1)
RESUMABLE_PHASES: frozenset[Phase] = frozenset({Phase.HITL, Phase.ESCALATED})

# Terminal phases: no further action needed
TERMINAL_PHASES: frozenset[Phase] = frozenset(
    {Phase.AUTO_APPROVE, Phase.UNSUPPORTED, Phase.EXTRACTION_ERROR, Phase.REJECTED}
)


class FulfillmentResult(BaseModel, frozen=True):
    """The durable state of a Path-B fulfillment attempt.

    JSON-serializable so the M1.8/M1.11 edge can stamp it on the durable task
    (parity with how M1.4 stamps LedgerEntry on task.metadata).

    Note:
        Resubmission is non-resumable: awaits a *fresh document*, not a human decision.
        The caller threads `attempts` forward across resubmissions by calling
        run_fulfillment(new_document, ..., attempts=prior_state.attempts).
    """

    model_config = {"extra": "forbid"}

    phase: Phase
    disposition: Disposition | None  # None only on EXTRACTION_ERROR (no extraction produced)
    attempts: int = 0  # resubmissions requested so far
    entry: LedgerEntry | None = None  # None only on EXTRACTION_ERROR
    suspended: bool  # True iff phase in RESUMABLE_PHASES
    terminal: bool  # True iff phase in TERMINAL_PHASES
    awaiting_resubmission: bool  # True iff phase == RESUBMIT


async def run_fulfillment(
    document: object,
    doctype_skill: object = None,
    *,
    engine: ExtractionSeam,
    thresholds: DispositionThresholds = DispositionThresholds(),
    max_resubmissions: int = 3,
    doc_id: str | None = None,
    attempts: int = 0,
) -> FulfillmentResult:
    """Run the Path-B fulfillment graph: extract → gate → route.

    The graph shape:
        receive → extract_with_quality_gate → confidence_gate →
        {auto_approve | hitl_review | escalate | extraction_error}

    Resubmission loop: if gate=RESUBMIT and attempts < max_resubmissions, increment
    attempts and return a RESUBMIT phase (awaiting_resubmission=True). When the caller
    provides a fresh document, it calls run_fulfillment again with the carried attempts.
    If gate=RESUBMIT and attempts == max_resubmissions, escalate (ESCALATED phase,
    disposition=PENDING, suspended=True).

    HITL and ESCALATED phases suspend with zero compute (no re-extraction on resume).

    Args:
        document: The document to extract (engine-specific type, e.g., FixtureDocument).
        doctype_skill: Per-doctype skill context (passed to engine).
        engine: The extraction engine (ExtractionSeam).
        thresholds: Disposition thresholds (resubmit_below, auto_approve_at).
            Defaults to DispositionThresholds() (0.55, 0.85).
        max_resubmissions: Max resubmissions before escalation (from SkillPolicy).
            Defaults to 3.
        doc_id: Document identifier. Defaults to getattr(document, "fixture_id", None)
            or "doc" if neither is available.
        attempts: Resubmissions requested so far (threaded forward across resubmissions).
            Defaults to 0 (initial extraction).

    Returns:
        A FulfillmentResult with the phase, disposition, and state flags.

    Note:
        This function is engine-agnostic: it passes document straight through to
        engine.extract. Only the fixture adapter and its tests know about FixtureDocument.
    """
    # Step 1: receive — accept document
    # (no-op step, here for clarity against the wiki/bridge-fulfillment-graph.md diagram)

    # Step 2: extract_with_quality_gate — try to extract
    try:
        extraction = await engine.extract(document, doctype_skill)
    except ExtractionError:
        # Engine fault (illegible-beyond-recovery or unknown document)
        # → EXTRACTION_ERROR, disposition=PENDING, terminal + non-resumable
        return FulfillmentResult(
            phase=Phase.EXTRACTION_ERROR,
            disposition=Disposition.PENDING,
            attempts=attempts,
            entry=None,
            terminal=True,
            suspended=False,
            awaiting_resubmission=False,
        )

    # Step 3: classify the document and run the disposition gate
    # Derive doc_id if not provided
    if doc_id is None:
        doc_id = getattr(document, "fixture_id", None) or "doc"

    entry, result = classify_document(doc_id, extraction, thresholds=thresholds)

    # Step 4: route on result.gate
    gate = result.gate

    if gate == Gate.AUTO_APPROVE:
        # Accepted, terminal
        return FulfillmentResult(
            phase=Phase.AUTO_APPROVE,
            disposition=Disposition.ACCEPTED,
            attempts=attempts,
            entry=entry,
            terminal=True,
            suspended=False,
            awaiting_resubmission=False,
        )

    elif gate == Gate.HITL_REVIEW:
        # Pending, suspended (awaits human review)
        return FulfillmentResult(
            phase=Phase.HITL,
            disposition=Disposition.PENDING,
            attempts=attempts,
            entry=entry,
            terminal=False,
            suspended=True,
            awaiting_resubmission=False,
        )

    elif gate == Gate.UNSUPPORTED:
        # Rejected, terminal (doctype not in label space)
        return FulfillmentResult(
            phase=Phase.UNSUPPORTED,
            disposition=Disposition.REJECTED,
            attempts=attempts,
            entry=entry,
            terminal=True,
            suspended=False,
            awaiting_resubmission=False,
        )

    elif gate == Gate.RESUBMIT:
        # Quality issue: resubmit or escalate
        if attempts < max_resubmissions:
            # Request resubmission (non-resumable: awaits a fresh document)
            return FulfillmentResult(
                phase=Phase.RESUBMIT,
                disposition=Disposition.REJECTED,  # this attempt is rejected
                attempts=attempts + 1,
                entry=entry,
                terminal=False,
                suspended=False,
                awaiting_resubmission=True,
            )
        else:
            # Loop exhausted → escalate (A1: escalation ≠ rejection, disposition=PENDING)
            return FulfillmentResult(
                phase=Phase.ESCALATED,
                disposition=Disposition.PENDING,  # not rejected (A1)
                attempts=attempts,
                entry=entry,
                terminal=False,
                suspended=True,
                awaiting_resubmission=False,
            )

    else:
        # Unreachable (all gates covered)
        raise ValueError(f"Unknown gate: {gate}")


def resume_fulfillment(state: FulfillmentResult, *, accept: bool) -> FulfillmentResult:
    """Resume a suspended fulfillment with a human decision (zero compute).

    This is the "zero compute while suspended, resume feeds a decision" step. It
    must NOT call the engine (enforced in tests via a spy engine). Only HITL and
    ESCALATED phases are resumable (A1).

    Args:
        state: The suspended FulfillmentResult to resume.
        accept: The human decision (True = accept, False = reject).

    Returns:
        A new FulfillmentResult with the decision applied.

    Raises:
        ValueError: If the phase is not resumable (resubmit/terminal phases cannot
            be decision-resumed).

    Note:
        Resubmit is NOT resumable (A1): it awaits a *fresh document*, not a human
        decision. The caller calls run_fulfillment(new_document, ..., attempts=...)
        for a resubmission.
    """
    # Guard: only resumable phases can be decision-resumed (A1)
    if state.phase not in RESUMABLE_PHASES:
        raise ValueError(
            f"Cannot resume phase {state.phase}: only {RESUMABLE_PHASES} are resumable. "
            f"Resubmit awaits a fresh document (call run_fulfillment), not a decision."
        )

    # Resolve the human decision
    if accept:
        # Accept: update entry disposition to ACCEPTED
        entry = state.entry
        if entry is not None:
            entry = entry.model_copy(update={"disposition": Disposition.ACCEPTED})

        return FulfillmentResult(
            phase=Phase.AUTO_APPROVE,
            disposition=Disposition.ACCEPTED,
            attempts=state.attempts,
            entry=entry,
            terminal=True,
            suspended=False,
            awaiting_resubmission=False,
        )
    else:
        # Reject: human/escalation reject → REJECTED phase (terminal)
        entry = state.entry
        if entry is not None:
            entry = entry.model_copy(update={"disposition": Disposition.REJECTED})

        return FulfillmentResult(
            phase=Phase.REJECTED,
            disposition=Disposition.REJECTED,
            attempts=state.attempts,
            entry=entry,
            terminal=True,
            suspended=False,
            awaiting_resubmission=False,
        )
