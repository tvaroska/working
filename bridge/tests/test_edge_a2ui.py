"""A2UI edge tests (M1.10).

Validates:
- party_status_view: buckets mixed ledger + requirements into sent/accepted/outstanding/next/done
- build_screen: emits declarative A2uiScreen with intake affordances (None when done)
- intake_to_document: maps A2uiResponse to FixtureDocument
- submit_intake: feeds Path-B intake into run_fulfillment, threads attempts for resubmission
- render_screen: reference/demo renderer (smoke test)
- JSON-serializable: A2uiScreen round-trips via model_dump(mode="json")

Acceptance anchor (parity with M1.7): submit_intake reaches the **same** FulfillmentResult
(phase/disposition/flags) as run_fulfillment for every eval fixture — the A2UI intake is
a no-op wrapper over the extraction graph.

Build ledgers realistically: drive fixtures through core (FixtureExtractionEngine →
classify_document → explain_rejection → propose_requirements) so M1.9 → M1.10 is
wired end-to-end.
"""

import pytest
from contract import (
    CollectionStatus,
    Disposition,
)

from bridge.adapters.local.extraction import FixtureDocument, FixtureExtractionEngine
from bridge.adapters.local.skill_registry import LocalSkillRegistry
from bridge.disposition import classify_document
from bridge.edges.a2ui import (
    A2uiResponse,
    A2uiScreen,
    build_screen,
    intake_to_document,
    party_status_view,
    render_screen,
    submit_intake,
)
from bridge.fulfillment import Phase, run_fulfillment
from bridge.requirements import (
    explain_rejection,
    load_explanations,
    propose_requirements,
)


async def _build_ledger_and_requirements(*fixture_ids: str):
    """Build a realistic ledger + requirements by driving fixtures through core.

    This is the M1.9 → M1.10 wiring: extract each fixture → classify → explain
    rejection → assemble CollectionStatus → propose_requirements. Mirrors the
    real Bridge pipeline.

    Args:
        *fixture_ids: One or more fixture IDs to process.

    Returns:
        A tuple of (CollectionStatus, RequirementsList).
    """
    engine = FixtureExtractionEngine()
    explanations = load_explanations(LocalSkillRegistry()._skills["address-proof"])
    ledger = []

    for fid in fixture_ids:
        doc = FixtureDocument(fixture_id=fid)
        extraction = await engine.extract(doc, None)
        entry, result = classify_document(fid, extraction)

        # Stamp message for rejected entries (mirrors executor.py)
        if entry.disposition == Disposition.REJECTED:
            reason_code, message = explain_rejection(entry, result.gate, explanations=explanations)
            entry = entry.model_copy(update={"reason_code": reason_code, "message": message})

        ledger.append(entry)

    status = CollectionStatus(ledger=ledger)
    requirements = propose_requirements(status, explanations=explanations)
    return status, requirements


# --------------------------------------------------------------------------- #
# party_status_view — projection tests
# --------------------------------------------------------------------------- #


@pytest.mark.anyio
async def test_party_status_view_mixed_ledger():
    """Mixed ledger: one accepted bill + one rejected passport → correct buckets."""
    status, requirements = await _build_ledger_and_requirements(
        "bill-powerco-clean", "passport-unsupported"
    )

    view = party_status_view(status, requirements)

    # sent: 2 docs
    assert len(view.sent) == 2
    assert {doc.id for doc in view.sent} == {"bill-powerco-clean", "passport-unsupported"}

    # accepted: 1 (bill-powerco-clean only)
    assert len(view.accepted) == 1
    assert view.accepted[0].id == "bill-powerco-clean"
    assert view.accepted[0].disposition == Disposition.ACCEPTED

    # rejected doc carries verbatim message (ADR-0013)
    rejected = next(doc for doc in view.sent if doc.id == "passport-unsupported")
    assert rejected.disposition == Disposition.REJECTED
    assert rejected.message is not None  # verbatim relay from explain_rejection
    # The message should be the unsupported-doctype prose from explanations.yaml
    # (we don't hard-code the prose here — just verify it's relayed)

    # outstanding: non-empty (not done)
    assert len(view.outstanding) > 0

    # next: the requirement's message (verbatim)
    assert view.next is not None

    # done: False (only 1 accepted bill, need 2 distinct issuers or a gov-id)
    assert view.done is False


@pytest.mark.anyio
async def test_party_status_view_done_case():
    """Done case: accepted gov-id → done=True, outstanding=[], next=None, intake=None."""
    status, requirements = await _build_ledger_and_requirements("gov-id-clean")

    view = party_status_view(status, requirements)

    # sent: 1
    assert len(view.sent) == 1
    assert view.sent[0].id == "gov-id-clean"

    # accepted: 1
    assert len(view.accepted) == 1

    # outstanding: empty (done)
    assert view.outstanding == []

    # next: None (done)
    assert view.next is None

    # done: True
    assert view.done is True


@pytest.mark.anyio
async def test_party_status_view_distinct_issuer_case():
    """Distinct-issuer case: one accepted bill → next=distinct-issuer-needed message."""
    status, requirements = await _build_ledger_and_requirements("bill-powerco-clean")

    view = party_status_view(status, requirements)

    # Not done (need 2 distinct issuers or a gov-id)
    assert view.done is False

    # next: should be the distinct-issuer-needed message (verbatim relay)
    # The propose_requirements logic (M1.9) picks DISTINCT_ISSUER_NEEDED when
    # len(accepted_issuers) == 1
    assert view.next is not None
    # The message is verbatim from explanations.yaml — we don't hard-code it here


@pytest.mark.anyio
async def test_build_screen_done_case():
    """build_screen: done → intake is None."""
    status, requirements = await _build_ledger_and_requirements("gov-id-clean")

    screen = build_screen(status, requirements)

    assert screen.status.done is True
    assert screen.intake is None


@pytest.mark.anyio
async def test_build_screen_not_done_case():
    """build_screen: not done → intake has prompt + doctype_hint + affordances."""
    status, requirements = await _build_ledger_and_requirements("bill-powerco-clean")

    screen = build_screen(status, requirements)

    assert screen.status.done is False
    assert screen.intake is not None

    # intake.prompt == the requirement's message (verbatim)
    assert screen.intake.prompt == requirements.requirements[0].message

    # intake.doctype_hint == the requirement's doctype_hint
    assert screen.intake.doctype_hint == requirements.requirements[0].doctype_hint

    # intake.accepts: at least one affordance
    assert len(screen.intake.accepts) > 0
    # Spot-check: first affordance is a file upload
    assert screen.intake.accepts[0].key == "document"
    assert screen.intake.accepts[0].input == "file"


# --------------------------------------------------------------------------- #
# intake_to_document + submit_intake — feed the graph
# --------------------------------------------------------------------------- #


def test_intake_to_document_fixture_id():
    """intake_to_document: A2uiResponse(fixture_id=...) → FixtureDocument."""
    response = A2uiResponse(fixture_id="gov-id-clean")

    doc = intake_to_document(response)

    assert isinstance(doc, FixtureDocument)
    assert doc.fixture_id == "gov-id-clean"


def test_intake_to_document_missing_fixture_id():
    """intake_to_document: A2uiResponse(fixture_id=None) → ValueError."""
    response = A2uiResponse(fixture_id=None)

    with pytest.raises(ValueError, match="A2UI intake requires a fixture_id"):
        intake_to_document(response)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "fixture_id,expected_phase,expected_disposition",
    [
        ("gov-id-clean", Phase.AUTO_APPROVE, Disposition.ACCEPTED),
        ("bill-powerco-clean", Phase.AUTO_APPROVE, Disposition.ACCEPTED),
        ("passport-unsupported", Phase.UNSUPPORTED, Disposition.REJECTED),
        ("bill-aquautil-blurry", Phase.RESUBMIT, Disposition.REJECTED),
        ("gov-id-expired", Phase.HITL, Disposition.PENDING),
        ("bill-aquautil-clear", Phase.HITL, Disposition.PENDING),
    ],
)
async def test_submit_intake_reaches_same_result_as_run_fulfillment(
    fixture_id, expected_phase, expected_disposition
):
    """Acceptance anchor: submit_intake reaches the same FulfillmentResult as run_fulfillment.

    This is the hard acceptance criterion: the A2UI intake is a no-op wrapper over
    the M1.7 extraction graph. Same phase, same disposition, same flags.
    """
    engine = FixtureExtractionEngine()
    response = A2uiResponse(fixture_id=fixture_id)

    # submit_intake path
    result_via_submit = await submit_intake(response, engine=engine)

    # run_fulfillment path (direct)
    doc = FixtureDocument(fixture_id=fixture_id)
    result_via_run = await run_fulfillment(doc, engine=engine)

    # Parity: same phase, disposition, flags
    assert result_via_submit.phase == result_via_run.phase
    assert result_via_submit.disposition == result_via_run.disposition
    assert result_via_submit.terminal == result_via_run.terminal
    assert result_via_submit.suspended == result_via_run.suspended
    assert result_via_submit.awaiting_resubmission == result_via_run.awaiting_resubmission

    # Spot-check expected values
    assert result_via_submit.phase == expected_phase
    assert result_via_submit.disposition == expected_disposition


@pytest.mark.anyio
async def test_submit_intake_threads_attempts():
    """Resubmission threading: submit_intake threads attempts forward."""
    engine = FixtureExtractionEngine()
    blurry = A2uiResponse(fixture_id="bill-aquautil-blurry")

    # attempts=0 → RESUBMIT, attempts=1
    result = await submit_intake(blurry, engine=engine, attempts=0)
    assert result.phase == Phase.RESUBMIT
    assert result.attempts == 1
    assert result.awaiting_resubmission is True

    # attempts=1 → RESUBMIT, attempts=2
    result = await submit_intake(blurry, engine=engine, attempts=1)
    assert result.phase == Phase.RESUBMIT
    assert result.attempts == 2

    # attempts=2 → RESUBMIT, attempts=3
    result = await submit_intake(blurry, engine=engine, attempts=2)
    assert result.phase == Phase.RESUBMIT
    assert result.attempts == 3

    # attempts=3 → ESCALATED (loop exhausted)
    result = await submit_intake(blurry, engine=engine, attempts=3)
    assert result.phase == Phase.ESCALATED
    assert result.disposition == Disposition.PENDING  # escalation ≠ rejection (A1)
    assert result.suspended is True
    assert result.awaiting_resubmission is False


# --------------------------------------------------------------------------- #
# render_screen — demo furniture smoke test
# --------------------------------------------------------------------------- #


@pytest.mark.anyio
async def test_render_screen_not_done():
    """render_screen: not-done screen contains outstanding + next prose."""
    status, requirements = await _build_ledger_and_requirements("bill-powerco-clean")
    screen = build_screen(status, requirements)

    rendered = render_screen(screen)

    # Smoke checks: contains expected sections
    assert "Sent:" in rendered
    assert "Accepted:" in rendered
    assert "Outstanding:" in rendered
    assert "Next:" in rendered

    # Contains the next-action prose (verbatim relay)
    assert screen.status.next in rendered

    # Does NOT contain "Done." (not done)
    assert "Done." not in rendered


@pytest.mark.anyio
async def test_render_screen_done():
    """render_screen: done screen contains 'Done.'"""
    status, requirements = await _build_ledger_and_requirements("gov-id-clean")
    screen = build_screen(status, requirements)

    rendered = render_screen(screen)

    # Contains "Done."
    assert "Done." in rendered


@pytest.mark.anyio
async def test_render_screen_rejected_doc_carries_message():
    """render_screen: rejected doc carries verbatim message (ADR-0013)."""
    status, requirements = await _build_ledger_and_requirements("passport-unsupported")
    screen = build_screen(status, requirements)

    rendered = render_screen(screen)

    # The rejected doc should have a message (verbatim from explain_rejection)
    rejected = next(doc for doc in screen.status.sent if doc.disposition == Disposition.REJECTED)
    assert rejected.message is not None

    # The message should appear in the rendered output
    assert rejected.message in rendered


# --------------------------------------------------------------------------- #
# JSON-serializable
# --------------------------------------------------------------------------- #


@pytest.mark.anyio
async def test_a2ui_screen_json_serializable():
    """A2uiScreen is JSON-serializable (the host consumes JSON)."""
    status, requirements = await _build_ledger_and_requirements("bill-powerco-clean")
    screen = build_screen(status, requirements)

    # Round-trip via model_dump(mode="json")
    json_dict = screen.model_dump(mode="json")
    assert isinstance(json_dict, dict)
    assert "status" in json_dict
    assert "intake" in json_dict

    # Re-parse
    reloaded = A2uiScreen.model_validate(json_dict)
    assert reloaded.status.done == screen.status.done
    assert reloaded.intake is not None
    assert reloaded.intake.prompt == screen.intake.prompt
