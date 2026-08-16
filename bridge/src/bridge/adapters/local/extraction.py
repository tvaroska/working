"""Fixture extraction engine adapter (skeleton — M1.7 fills in behavior).

Deterministic fixture-based extraction engine for the local development environment.
Satisfies the ExtractionSeam protocol. Real behavior lands in M1.7.
"""

from contract import Extraction

__all__ = ["FixtureExtractionEngine"]


class FixtureExtractionEngine:
    """Fixture (deterministic) extraction engine adapter.

    Skeleton conforming to ExtractionSeam. Methods raise NotImplementedError
    until M1.7 implements the real fixture-based extraction logic.

    This is the LOCAL capability adapter (deterministic for testing). Gemini is
    Sprint 2; DocAI is Phase 4. See ADR-0005 for the capability-axis contract.
    """

    async def extract(self, document: object, doctype_skill: object) -> Extraction:
        """Extract structured data from a document (fixture-based)."""
        raise NotImplementedError("M1.7: fixture extraction engine + resolution")
