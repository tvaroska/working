"""Dual-path dispatch for the A2A edge (M1.11).

Path dispatch is decided **only by what kind of Part arrives** (wiki/bridge-dual-path.md):
- **Path A** (structured): agent → Extraction JSON DataPart → validate-only, no extract.
- **Path B** (portal/operator): human/operator → file/text/form → extraction graph.

Both paths converge through the shared route_disposition (bridge.fulfillment), so the
requester cannot tell the path apart — same terminal outcomes (terminal-outcome parity, A2).

Import discipline: imports contract + a2a + core (fulfillment). Never imports agents.
Keep it out of bridge/__init__.py (preserve cheap import bridge + no-agents-guard clarity).
"""

from __future__ import annotations

from enum import StrEnum

from a2a.helpers.proto_helpers import get_data_parts
from contract import Extraction

from bridge.fulfillment import FulfillmentResult, run_fulfillment, validate_only
from bridge.seams.extraction import ExtractionSeam
from bridge.skills import DispositionThresholds

__all__ = ["PathKind", "classify_arrival", "looks_like_extraction", "route_arrival"]


class PathKind(StrEnum):
    """Dual-path fulfillment mode (wiki/bridge-dual-path.md)."""

    A = "path_a"  # structured Extraction response → validate-only, no extract
    B = "path_b"  # file / text / form → extraction graph (run_fulfillment)


def _is_file_part(part) -> bool:
    """Check if an a2a Part is a FilePart (defensive probe).

    The a2a proto Part wraps a oneof; check via HasField if available, else
    getattr fallback (guarded against attribute errors).
    """
    # Try HasField first (proto method)
    if hasattr(part, "HasField"):
        try:
            return part.HasField("file")
        except (ValueError, AttributeError):
            pass
    # Fallback to getattr
    return hasattr(part, "file") and getattr(part, "file", None) is not None


def _is_text_part(part) -> bool:
    """Check if an a2a Part is a TextPart (defensive probe).

    The a2a proto Part wraps a oneof; check via HasField if available, else
    getattr fallback (guarded against attribute errors).
    """
    # Try HasField first (proto method)
    if hasattr(part, "HasField"):
        try:
            return part.HasField("text")
        except (ValueError, AttributeError):
            pass
    # Fallback to getattr
    return hasattr(part, "text") and getattr(part, "text", None) is not None


def looks_like_extraction(data: object) -> bool:
    """A DataPart is a Path-A structured response iff it schema-shapes as Extraction.

    An Extraction DataPart has a top-level 'fields' key. A CollectRequest DataPart
    (party/skill, no 'fields') is NOT an Extraction.

    Args:
        data: The decoded data part (dict from get_data_parts).

    Returns:
        True iff the data looks like an Extraction (has 'fields' key).
    """
    return isinstance(data, dict) and "fields" in data


def classify_arrival(parts, *, operator: bool = False) -> PathKind:
    """Dispatch by the arriving A2A Part(s) (wiki/bridge-dual-path).

    - operator-fulfilled → Path B (an internal human upload; lessons/wiki dual-path).
    - any FilePart or TextPart present (raw doc / free text) → Path B.
    - a structured DataPart that shapes as Extraction → Path A.
    - otherwise (no recognizable structured response) → Path B (default: extract).

    Args:
        parts: The a2a message parts.
        operator: Whether this is an operator-fulfilled upload (default False).

    Returns:
        PathKind.A for structured Extraction, PathKind.B otherwise.

    Note:
        Operator-fulfilled uploads are always Path B (an internal human upload on
        the party's behalf; the priority/queue nuance is a scheduler concern — M1.12).
    """
    if operator:
        return PathKind.B

    # Check for file/text parts (raw doc / free text → Path B)
    if any(_is_file_part(p) or _is_text_part(p) for p in parts):
        return PathKind.B

    # Check for a structured Extraction DataPart (top-level 'fields' → Path A)
    for data in get_data_parts(parts):
        if looks_like_extraction(data):
            return PathKind.A

    # Default: Path B (extraction graph)
    return PathKind.B


async def route_arrival(
    path: PathKind,
    *,
    extraction: Extraction | None = None,
    document: object | None = None,
    engine: ExtractionSeam,
    thresholds: DispositionThresholds | None = None,
    attempts: int = 0,
    max_resubmissions: int = 3,
) -> FulfillmentResult:
    """Converged dual-path entrypoint.

    Path A → validate_only (no engine); Path B → run_fulfillment (engine). Both
    return the same FulfillmentResult shape so callers (and the requester) cannot
    distinguish the fulfillment mode.

    Args:
        path: The path kind (A or B).
        extraction: The validated Extraction payload (required for Path A).
        document: The document to extract (required for Path B).
        engine: The extraction engine (ExtractionSeam).
        thresholds: Disposition thresholds. Defaults to DispositionThresholds().
        attempts: Resubmissions requested so far (threaded forward across resubmissions).
        max_resubmissions: Max resubmissions before escalation (from SkillPolicy).

    Returns:
        A FulfillmentResult with the phase, disposition, and state flags.

    Raises:
        ValueError: If the required argument for the path is missing (extraction for
            Path A, document for Path B).
    """
    thr = thresholds or DispositionThresholds()

    if path is PathKind.A:
        if extraction is None:
            raise ValueError("Path A requires a validated Extraction")
        return validate_only(
            extraction, thresholds=thr, attempts=attempts, max_resubmissions=max_resubmissions
        )

    # Path B
    if document is None:
        raise ValueError("Path B requires a document")
    return await run_fulfillment(
        document,
        engine=engine,
        thresholds=thr,
        attempts=attempts,
        max_resubmissions=max_resubmissions,
    )
