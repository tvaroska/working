"""Fulfillment graph tests (M1.7).

Verify the Path-B fulfillment graph routes correctly per fixture, handles the
resubmission loop, supports HITL/escalated resume with zero compute, and enforces
the non-resumable resubmit invariant (A1).
"""

import pytest
from contract import Disposition

from bridge.adapters.local.extraction import FixtureDocument, FixtureExtractionEngine
from bridge.fulfillment import (
    RESUMABLE_PHASES,
    TERMINAL_PHASES,
    FulfillmentResult,
    Phase,
    resume_fulfillment,
    run_fulfillment,
)


@pytest.mark.anyio
async def test_gate_routes_gov_id_clean_to_auto_approve():
    """Verify gov-id-clean routes to AUTO_APPROVE (accepted, terminal)."""
    engine = FixtureExtractionEngine()
    doc = FixtureDocument(fixture_id="gov-id-clean")

    result = await run_fulfillment(doc, engine=engine)

    assert result.phase == Phase.AUTO_APPROVE
    assert result.disposition == Disposition.ACCEPTED
    assert result.terminal is True
    assert result.suspended is False
    assert result.awaiting_resubmission is False
    assert result.entry is not None
    assert result.entry.doctype == "gov-id"


@pytest.mark.anyio
async def test_gate_routes_bill_clean_to_auto_approve():
    """Verify bill-powerco-clean routes to AUTO_APPROVE (accepted, terminal)."""
    engine = FixtureExtractionEngine()
    doc = FixtureDocument(fixture_id="bill-powerco-clean")

    result = await run_fulfillment(doc, engine=engine)

    assert result.phase == Phase.AUTO_APPROVE
    assert result.disposition == Disposition.ACCEPTED
    assert result.terminal is True
    assert result.suspended is False


@pytest.mark.anyio
async def test_gate_routes_gov_id_expired_to_hitl():
    """Verify gov-id-expired routes to HITL (pending, suspended, resumable)."""
    engine = FixtureExtractionEngine()
    doc = FixtureDocument(fixture_id="gov-id-expired")

    result = await run_fulfillment(doc, engine=engine)

    assert result.phase == Phase.HITL
    assert result.disposition == Disposition.PENDING
    assert result.terminal is False
    assert result.suspended is True
    assert result.awaiting_resubmission is False
    assert result.phase in RESUMABLE_PHASES


@pytest.mark.anyio
async def test_gate_routes_bill_clear_to_hitl():
    """Verify bill-aquautil-clear routes to HITL (mid-confidence)."""
    engine = FixtureExtractionEngine()
    doc = FixtureDocument(fixture_id="bill-aquautil-clear")

    result = await run_fulfillment(doc, engine=engine)

    assert result.phase == Phase.HITL
    assert result.disposition == Disposition.PENDING
    assert result.suspended is True


@pytest.mark.anyio
async def test_gate_routes_blurry_to_resubmit():
    """Verify bill-aquautil-blurry routes to RESUBMIT (rejected, attempts=1)."""
    engine = FixtureExtractionEngine()
    doc = FixtureDocument(fixture_id="bill-aquautil-blurry")

    result = await run_fulfillment(doc, engine=engine)

    assert result.phase == Phase.RESUBMIT
    assert result.disposition == Disposition.REJECTED
    assert result.attempts == 1
    assert result.awaiting_resubmission is True
    assert result.terminal is False
    assert result.suspended is False
    # Resubmit is NOT resumable
    assert result.phase not in RESUMABLE_PHASES


@pytest.mark.anyio
async def test_gate_routes_passport_to_unsupported():
    """Verify passport-unsupported routes to UNSUPPORTED (rejected, terminal)."""
    engine = FixtureExtractionEngine()
    doc = FixtureDocument(fixture_id="passport-unsupported")

    result = await run_fulfillment(doc, engine=engine)

    assert result.phase == Phase.UNSUPPORTED
    assert result.disposition == Disposition.REJECTED
    assert result.terminal is True
    assert result.suspended is False
    assert result.phase in TERMINAL_PHASES


@pytest.mark.anyio
async def test_resubmission_loop_escalates_after_three():
    """Verify resubmission loop escalates after 3 attempts (from policy max_resubmissions=3).

    Feed blurry repeatedly, threading attempts forward:
    resubmit(1) → resubmit(2) → resubmit(3) → ESCALATED (pending, suspended, resumable).
    """
    engine = FixtureExtractionEngine()
    doc = FixtureDocument(fixture_id="bill-aquautil-blurry")

    # First attempt (attempts=0 → 1)
    result1 = await run_fulfillment(doc, engine=engine, attempts=0, max_resubmissions=3)
    assert result1.phase == Phase.RESUBMIT
    assert result1.attempts == 1

    # Second attempt (attempts=1 → 2)
    result2 = await run_fulfillment(doc, engine=engine, attempts=1, max_resubmissions=3)
    assert result2.phase == Phase.RESUBMIT
    assert result2.attempts == 2

    # Third attempt (attempts=2 → 3)
    result3 = await run_fulfillment(doc, engine=engine, attempts=2, max_resubmissions=3)
    assert result3.phase == Phase.RESUBMIT
    assert result3.attempts == 3

    # Fourth attempt (attempts=3, loop exhausted → ESCALATED)
    result4 = await run_fulfillment(doc, engine=engine, attempts=3, max_resubmissions=3)
    assert result4.phase == Phase.ESCALATED
    assert result4.disposition == Disposition.PENDING  # A1: escalation ≠ rejection
    assert result4.attempts == 3
    assert result4.suspended is True
    assert result4.awaiting_resubmission is False
    assert result4.phase in RESUMABLE_PHASES


@pytest.mark.anyio
async def test_resubmit_is_not_resumable():
    """Verify resume_fulfillment raises on RESUBMIT phase (A1: non-resumable)."""
    engine = FixtureExtractionEngine()
    doc = FixtureDocument(fixture_id="bill-aquautil-blurry")

    result = await run_fulfillment(doc, engine=engine)
    assert result.phase == Phase.RESUBMIT

    # Attempting to resume a RESUBMIT phase should raise
    with pytest.raises(ValueError, match="Cannot resume phase"):
        resume_fulfillment(result, accept=True)


@pytest.mark.anyio
async def test_hitl_resume_accept():
    """Verify HITL resume with accept=True → AUTO_APPROVE (accepted, terminal)."""
    engine = FixtureExtractionEngine()
    doc = FixtureDocument(fixture_id="gov-id-expired")

    # Run to HITL
    result = await run_fulfillment(doc, engine=engine)
    assert result.phase == Phase.HITL

    # Resume with accept=True
    resumed = resume_fulfillment(result, accept=True)

    assert resumed.phase == Phase.AUTO_APPROVE
    assert resumed.disposition == Disposition.ACCEPTED
    assert resumed.terminal is True
    assert resumed.suspended is False
    # Verify entry disposition is updated
    assert resumed.entry is not None
    assert resumed.entry.disposition == Disposition.ACCEPTED


@pytest.mark.anyio
async def test_hitl_resume_reject():
    """Verify HITL resume with accept=False → REJECTED (terminal)."""
    engine = FixtureExtractionEngine()
    doc = FixtureDocument(fixture_id="gov-id-expired")

    # Run to HITL
    result = await run_fulfillment(doc, engine=engine)
    assert result.phase == Phase.HITL

    # Resume with accept=False
    resumed = resume_fulfillment(result, accept=False)

    assert resumed.phase == Phase.REJECTED
    assert resumed.disposition == Disposition.REJECTED
    assert resumed.terminal is True
    assert resumed.suspended is False
    # Verify entry disposition is updated
    assert resumed.entry is not None
    assert resumed.entry.disposition == Disposition.REJECTED


@pytest.mark.anyio
async def test_escalated_resume():
    """Verify escalated state's disposition is PENDING before resume.

    A1: escalation ≠ rejection.
    """
    engine = FixtureExtractionEngine()
    doc = FixtureDocument(fixture_id="bill-aquautil-blurry")

    # Run to escalation (4th blurry attempt)
    result = await run_fulfillment(doc, engine=engine, attempts=3, max_resubmissions=3)
    assert result.phase == Phase.ESCALATED
    assert result.disposition == Disposition.PENDING  # A1: not rejected

    # Resume with accept=True
    resumed_accept = resume_fulfillment(result, accept=True)
    assert resumed_accept.phase == Phase.AUTO_APPROVE
    assert resumed_accept.disposition == Disposition.ACCEPTED

    # Resume with accept=False
    resumed_reject = resume_fulfillment(result, accept=False)
    assert resumed_reject.phase == Phase.REJECTED
    assert resumed_reject.disposition == Disposition.REJECTED


@pytest.mark.anyio
async def test_resume_does_zero_compute():
    """Verify resume never re-calls the engine (zero compute while suspended).

    Use a counting wrapper to assert the engine call count is unchanged after resume.
    """

    class CountingEngine:
        """Spy engine that counts extract calls."""

        def __init__(self, wrapped):
            self.wrapped = wrapped
            self.call_count = 0

        async def extract(self, document, doctype_skill):
            self.call_count += 1
            return await self.wrapped.extract(document, doctype_skill)

    engine = CountingEngine(FixtureExtractionEngine())
    doc = FixtureDocument(fixture_id="gov-id-expired")

    # Run to HITL
    result = await run_fulfillment(doc, engine=engine)
    assert result.phase == Phase.HITL
    call_count_after_run = engine.call_count
    assert call_count_after_run == 1  # extract was called once

    # Resume with accept=True
    resume_fulfillment(result, accept=True)

    # Verify call count unchanged (no re-extraction)
    assert engine.call_count == call_count_after_run


@pytest.mark.anyio
async def test_extraction_error_path():
    """Verify ExtractionError → EXTRACTION_ERROR phase (pending, terminal, non-resumable)."""
    engine = FixtureExtractionEngine()
    doc = FixtureDocument(fixture_id="unknown-id", fail=True)

    result = await run_fulfillment(doc, engine=engine)

    assert result.phase == Phase.EXTRACTION_ERROR
    assert result.disposition == Disposition.PENDING  # engine failure, not a judgment
    assert result.entry is None  # no extraction produced
    assert result.terminal is True
    assert result.suspended is False
    assert result.awaiting_resubmission is False
    # Not resumable
    assert result.phase not in RESUMABLE_PHASES


@pytest.mark.anyio
async def test_ledger_entry_canonical_issuer():
    """Verify LedgerEntry carries the canonical issuer (M1.5 canonicalization)."""
    engine = FixtureExtractionEngine()

    # bill-powerco-clean has issuer "power-co" in the fixture
    doc = FixtureDocument(fixture_id="bill-powerco-clean")
    result = await run_fulfillment(doc, engine=engine)

    assert result.entry is not None
    assert result.entry.issuer == "power-co"

    # bill-powerco-clean-2 has issuer_raw "Power Co." → canonical "power-co"
    doc2 = FixtureDocument(fixture_id="bill-powerco-clean-2")
    result2 = await run_fulfillment(doc2, engine=engine)

    assert result2.entry is not None
    assert result2.entry.issuer == "power-co"


def test_fulfillment_result_frozen_extra_forbid():
    """Verify FulfillmentResult is frozen and rejects extra fields."""
    # extra="forbid" test
    with pytest.raises(Exception):  # Pydantic ValidationError
        FulfillmentResult(
            phase=Phase.AUTO_APPROVE,
            disposition=Disposition.ACCEPTED,
            suspended=False,
            terminal=True,
            awaiting_resubmission=False,
            bogus_field="should-fail",  # extra field
        )

    # frozen=True test (immutability)
    result = FulfillmentResult(
        phase=Phase.AUTO_APPROVE,
        disposition=Disposition.ACCEPTED,
        suspended=False,
        terminal=True,
        awaiting_resubmission=False,
    )

    with pytest.raises(Exception):  # Pydantic ValidationError (frozen)
        result.phase = Phase.HITL  # type: ignore


@pytest.mark.anyio
async def test_max_resubmissions_from_policy():
    """Verify max_resubmissions can be read from SkillPolicy and used in the graph."""
    from bridge.adapters.local import build_local_adapter
    from bridge.seams import Seam

    # Load the skill registry
    registry = build_local_adapter(Seam.SKILL_REGISTRY)
    skill = await registry.get_skill("address-proof")

    # Verify the policy has max_resubmissions
    assert skill.policy is not None
    max_resubmissions = skill.policy.max_resubmissions
    assert max_resubmissions == 3

    # Use it in the graph
    engine = FixtureExtractionEngine()
    doc = FixtureDocument(fixture_id="bill-aquautil-blurry")

    # Run with policy max_resubmissions
    result = await run_fulfillment(
        doc, engine=engine, attempts=max_resubmissions, max_resubmissions=max_resubmissions
    )

    # Should escalate (loop exhausted)
    assert result.phase == Phase.ESCALATED
