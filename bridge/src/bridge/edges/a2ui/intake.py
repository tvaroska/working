"""A2UI intake: ingest structured response + feed the Path-B graph (M1.10).

Receives structured responses from the A2UI host renderer, maps them to Path-B
intake documents, and feeds them into the M1.7 fulfillment graph. Threads
`attempts` forward for the resubmission loop (the caller carries attempts
across resubmissions).

In Phase-1 local, intake is fixture-based (A2uiResponse carries a `fixture_id`
that maps to a FixtureDocument). Real blob/text→Gemini intake is Sprint-2/Phase-4.

Import discipline: contract (via run_fulfillment) + bridge.fulfillment +
bridge.seams.extraction + bridge.adapters.local.extraction + bridge.skills +
stdlib enum. Never agents. Keep this out of bridge/__init__.py.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from bridge.adapters.local.extraction import FixtureDocument
from bridge.fulfillment import FulfillmentResult, run_fulfillment
from bridge.seams.extraction import ExtractionSeam
from bridge.skills import DispositionThresholds

__all__ = [
    "IntakeMode",
    "A2uiResponse",
    "intake_to_document",
    "submit_intake",
]


class IntakeMode(StrEnum):
    """A2UI intake mode (what kind of response arrived)."""

    UPLOAD = "upload"
    TEXT = "text"
    FORM = "form"


class A2uiResponse(BaseModel, frozen=True):
    """Structured response from the A2UI host renderer.

    In Phase-1 local, `fixture_id` selects a deterministic eval fixture (demo
    furniture) — the same value object M1.7's fixture engine already uses. Real
    blob/text→Gemini intake is Sprint-2/Phase-4.

    Fields:
        mode: Intake mode (upload/text/form). Defaults to UPLOAD.
        fixture_id: Fixture document ID (Phase-1 local, required). Selects a
            deterministic FixtureDocument from wiki/evals/address/expected.json.
            Real blob handling is Sprint-2/Phase-4.
        text: Inline text content (mode=TEXT; unused in Phase-1 local).
        fields: Form fields (mode=FORM; unused in Phase-1 local).
    """

    model_config = {"extra": "forbid"}

    mode: IntakeMode = IntakeMode.UPLOAD
    fixture_id: str | None = None
    text: str | None = None
    fields: dict[str, str] = {}


def intake_to_document(response: A2uiResponse) -> FixtureDocument:
    """Map an A2uiResponse to a Path-B intake document (Phase-1 local).

    In Phase-1 local, the intake is fixture-based: a `fixture_id` selects a
    deterministic FixtureDocument. Real blob/text→Gemini intake is Sprint-2/Phase-4.

    Args:
        response: The structured response from the A2UI host renderer.

    Returns:
        A FixtureDocument instance.

    Raises:
        ValueError: If fixture_id is None (Phase-1 local requires a fixture_id).

    Notes:
        Real blob intake (Sprint-2/Phase-4) will accept a blob/text and call the
        Gemini extraction engine. The fixture engine is deterministic demo furniture.
    """
    if response.fixture_id:
        return FixtureDocument(fixture_id=response.fixture_id)

    # Missing fixture_id in Phase-1 local
    raise ValueError(
        "A2UI intake requires a fixture_id in Phase-1 local "
        "(real blob intake is Sprint-2/Phase-4)"
    )


async def submit_intake(
    response: A2uiResponse,
    *,
    engine: ExtractionSeam,
    thresholds: DispositionThresholds | None = None,
    max_resubmissions: int = 3,
    attempts: int = 0,
) -> FulfillmentResult:
    """Feed Path-B intake into the M1.7 fulfillment graph.

    Maps the A2uiResponse to a document, then runs the fulfillment graph. Threads
    `attempts` forward for the resubmission loop: the caller passes
    `attempts=prior.attempts` on a resubmitted upload (the non-resumable resubmit
    loop, A1).

    Args:
        response: The structured response from the A2UI host renderer.
        engine: The extraction engine (ExtractionSeam).
        thresholds: Disposition thresholds. Defaults to DispositionThresholds().
        max_resubmissions: Max resubmissions before escalation. Defaults to 3.
        attempts: Resubmissions requested so far (threaded forward across
            resubmissions). Defaults to 0 (initial extraction).

    Returns:
        A FulfillmentResult from run_fulfillment.

    Notes:
        Resubmission threading (A1): the caller carries `attempts` forward across
        resubmissions. When a FulfillmentResult has `awaiting_resubmission=True`,
        the caller prompts for a fresh upload and calls `submit_intake` again with
        `attempts=prior.attempts` (the graph increments attempts internally).
    """
    document = intake_to_document(response)

    return await run_fulfillment(
        document,
        engine=engine,
        thresholds=thresholds or DispositionThresholds(),
        max_resubmissions=max_resubmissions,
        attempts=attempts,
    )
