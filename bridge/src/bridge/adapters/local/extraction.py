"""Fixture extraction engine adapter (deterministic, local).

Deterministic fixture-based extraction engine for the local development environment.
Maps a Path-B intake (keyed to an eval fixture) to an Extraction loaded from
wiki/evals/address/expected.json. No Gemini, no network.

Satisfies the ExtractionSeam protocol. Gemini is Sprint 2; DocAI is Phase 4.
See ADR-0005 for the capability-axis contract.
"""

import json
import os
from functools import lru_cache
from pathlib import Path

from contract import Extraction
from pydantic import BaseModel

from bridge.seams.extraction import ExtractionError, ExtractionSeam

__all__ = ["FixtureDocument", "FixtureExtractionEngine", "resolve_extraction_engine"]


class FixtureDocument(BaseModel, frozen=True):
    """A Path-B intake keyed to a deterministic eval fixture.

    The fixture engine's concretization of the abstract `document` parameter.
    Real Path-B intake (M1.10/M1.11) will be a different type; the fixture engine
    and its tests are the only code that knows about FixtureDocument.
    """

    model_config = {"extra": "forbid"}

    fixture_id: str
    extraction: Extraction | None = None  # inline extraction for test convenience
    fail: bool = False  # force ExtractionError (drives extraction_error path in tests)


def _resolve_evals_path() -> Path:
    """Resolve the path to wiki/evals/address/expected.json.

    Resolution order:
    1. ADDRESS_EVALS_PATH env var (if set)
    2. Walk up from this file to the first ancestor containing wiki/evals/address/
    3. Fallback: raise ValueError

    Returns:
        Path to expected.json.

    Raises:
        ValueError: If the file cannot be found.

    Note:
        Reuses the walk-up pattern from bridge.skills.resolve_default_skills_dir
        and bridge/tests/test_disposition.py::TestGateParity.resolve_evals_path.
        Does NOT import agents.mock_bridge.fixtures (bridge/ never imports agents/).
    """
    if "ADDRESS_EVALS_PATH" in os.environ:
        path = Path(os.environ["ADDRESS_EVALS_PATH"])
        if path.exists():
            return path
        raise ValueError(f"ADDRESS_EVALS_PATH points to non-existent file: {path}")

    # Walk up from __file__ to the first ancestor containing wiki/evals/address/
    current = Path(__file__).resolve().parent
    while current != current.parent:
        expected_path = current / "wiki" / "evals" / "address" / "expected.json"
        if expected_path.exists():
            return expected_path
        current = current.parent

    raise ValueError(
        "Cannot find wiki/evals/address/expected.json. "
        "Set ADDRESS_EVALS_PATH or run from within the repository."
    )


@lru_cache(maxsize=1)
def _load_expected_json() -> dict:
    """Load and cache the expected.json fixture data.

    Returns:
        Parsed JSON data (dict with "party" and "documents" keys).

    Raises:
        ValueError: If the file cannot be loaded or parsed.
    """
    path = _resolve_evals_path()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e
    except Exception as e:
        raise ValueError(f"Cannot read {path}: {e}") from e


class FixtureExtractionEngine:
    """Fixture (deterministic) extraction engine adapter.

    Maps a FixtureDocument to an Extraction loaded from wiki/evals/address/expected.json.
    Deterministic, no Gemini, no randomness. Satisfies ExtractionSeam.

    This is the LOCAL capability adapter (deterministic for testing). Gemini is
    Sprint 2; DocAI is Phase 4. See ADR-0005 for the capability-axis contract.
    """

    async def extract(self, document: object, doctype_skill: object) -> Extraction:
        """Extract structured data from a document (fixture-based).

        Args:
            document: A FixtureDocument instance (or compatible).
            doctype_skill: Ignored (fixture engine doesn't need skill context).

        Returns:
            An Extraction loaded from the eval fixture.

        Raises:
            ExtractionError: If the fixture_id is unknown, or fail=True, or the
                document type is unrecognized.
        """
        # Check fail flag first
        if getattr(document, "fail", False):
            raise ExtractionError("Fixture document has fail=True")

        # Check for inline extraction (test convenience / real Path-A-ish passthrough)
        inline_extraction = getattr(document, "extraction", None)
        if inline_extraction is not None:
            return inline_extraction

        # Resolve fixture_id
        fixture_id = getattr(document, "fixture_id", None)
        if fixture_id is None:
            raise ExtractionError("Document must be a FixtureDocument with a fixture_id attribute")

        # Load expected.json
        data = _load_expected_json()
        documents = data.get("documents", [])

        # Find matching fixture
        for doc in documents:
            if doc.get("id") == fixture_id:
                extraction_data = doc.get("extraction")
                if extraction_data is None:
                    raise ExtractionError(f"Fixture {fixture_id} has no extraction data")
                return Extraction.model_validate(extraction_data)

        # Unknown fixture_id
        raise ExtractionError(f"No fixture found for id: {fixture_id}")


def resolve_extraction_engine(
    doctype_skill: object = None, *, mode: str = "fixture"
) -> ExtractionSeam:
    """Resolve an extraction engine by mode (ADR-0005 engine resolution).

    For Phase-1 local, only the fixture engine is live. Gemini/DocAI modes are
    Sprint 2 / Phase 4.

    Args:
        doctype_skill: Per-doctype skill (unused in Phase 1).
        mode: Engine mode ("fixture", "gemini", "docai"). Defaults to "fixture".

    Returns:
        An extraction engine conforming to ExtractionSeam.

    Raises:
        NotImplementedError: For gemini/docai modes (Sprint 2 / Phase 4).

    Note:
        ADR-0005 resolution order (config mode → per-doctype capability → Gemini
        fallback) is the full Sprint 2 contract; Phase 1 ships only the fixture
        branch. The structure documents the seam; do not over-build multi-engine
        resolution now.
    """
    if mode == "fixture":
        return FixtureExtractionEngine()
    elif mode == "gemini":
        raise NotImplementedError(
            "Gemini extraction engine is Sprint 2 (ADR-0005 resolution order)"
        )
    elif mode == "docai":
        raise NotImplementedError(
            "Document AI extraction engine is Phase 4 (ADR-0005 resolution order)"
        )
    else:
        raise ValueError(f"Unknown extraction mode: {mode}")
