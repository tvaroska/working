"""Fixture extraction engine tests (M1.7).

Verify the FixtureExtractionEngine deterministically extracts from eval fixtures,
handles inline extractions, and raises ExtractionError on unknown/fail.
"""

import pytest
from contract import Extraction

from bridge.adapters.local.extraction import (
    FixtureDocument,
    FixtureExtractionEngine,
    resolve_extraction_engine,
)
from bridge.seams.extraction import ExtractionError


@pytest.mark.anyio
async def test_all_fixtures_extract():
    """Verify all 8 eval fixtures extract to an Extraction with matching doctype."""
    engine = FixtureExtractionEngine()

    # The 8 eval fixture IDs (from wiki/evals/address/expected.json)
    fixture_ids = [
        ("gov-id-clean", "gov-id"),
        ("gov-id-expired", "gov-id"),
        ("bill-powerco-clean", "utility-bill"),
        ("bill-powerco-clean-2", "utility-bill"),
        ("bill-aquautil-clean", "utility-bill"),
        ("bill-aquautil-clear", "utility-bill"),
        ("bill-aquautil-blurry", "utility-bill"),
        ("passport-unsupported", "passport"),
    ]

    for fixture_id, expected_doctype in fixture_ids:
        doc = FixtureDocument(fixture_id=fixture_id)
        extraction = await engine.extract(doc, None)

        # Verify it's an Extraction
        assert isinstance(extraction, Extraction)

        # Verify doctype matches
        assert extraction.fields.doctype == expected_doctype

        # Verify overall_confidence and legible round-trip (present in fixtures)
        assert extraction.overall_confidence is not None
        assert extraction.legible is not None


@pytest.mark.anyio
async def test_unknown_fixture_raises():
    """Verify unknown fixture_id raises ExtractionError."""
    engine = FixtureExtractionEngine()

    doc = FixtureDocument(fixture_id="unknown-fixture-id")
    with pytest.raises(ExtractionError, match="No fixture found for id: unknown-fixture-id"):
        await engine.extract(doc, None)


@pytest.mark.anyio
async def test_fail_flag_raises():
    """Verify fail=True raises ExtractionError."""
    engine = FixtureExtractionEngine()

    doc = FixtureDocument(fixture_id="gov-id-clean", fail=True)
    with pytest.raises(ExtractionError, match="fail=True"):
        await engine.extract(doc, None)


@pytest.mark.anyio
async def test_inline_extraction_passthrough():
    """Verify inline extraction is returned verbatim."""
    from contract import ExtractedFields

    engine = FixtureExtractionEngine()

    # Build a custom extraction
    inline_extraction = Extraction(
        fields=ExtractedFields(doctype="custom-type", issuer="custom-issuer"),
        overall_confidence=0.99,
        legible=True,
        flagged_fields=[],
    )

    doc = FixtureDocument(fixture_id="any-id", extraction=inline_extraction)
    extraction = await engine.extract(doc, None)

    # Verify it's the same extraction
    assert extraction is inline_extraction


@pytest.mark.anyio
async def test_engine_is_deterministic():
    """Verify the same document extracted twice yields equal Extraction."""
    engine = FixtureExtractionEngine()

    doc = FixtureDocument(fixture_id="gov-id-clean")
    extraction1 = await engine.extract(doc, None)
    extraction2 = await engine.extract(doc, None)

    # Verify they're equal (Pydantic model equality)
    assert extraction1 == extraction2


def test_resolve_extraction_engine_fixture():
    """Verify resolve_extraction_engine returns a FixtureExtractionEngine for mode=fixture."""
    engine = resolve_extraction_engine(mode="fixture")
    assert isinstance(engine, FixtureExtractionEngine)


def test_resolve_extraction_engine_gemini_raises():
    """Verify gemini mode raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="Gemini extraction engine is Sprint 2"):
        resolve_extraction_engine(mode="gemini")


def test_resolve_extraction_engine_docai_raises():
    """Verify docai mode raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="Document AI extraction engine is Phase 4"):
        resolve_extraction_engine(mode="docai")
