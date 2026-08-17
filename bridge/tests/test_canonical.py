"""Tests for issuer canonicalization (sense A) — M1.5."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from bridge.canonical import canonicalize_issuer


class TestCanonicalizeIssuer:
    """Unit tests for the core canonicalization algorithm."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            # Trace cases from the plan
            ("PowerCo", "power-co"),
            ("Power Co.", "power-co"),
            ("PowerCo Ltd", "power-co"),
            ("AquaUtil", "aqua-util"),
            ("Gov", "gov"),
            ("Foo GmbH", "foo"),
            # Null and whitespace
            (None, None),
            ("   ", None),
            ("", None),
            # Additional suffix cases
            ("Example Inc", "example"),
            ("Test Corporation", "test"),
            ("Acme LLC", "acme"),
            ("Global AG", "global"),
            ("MegaCorp PLC", "mega"),  # both "corp" and "plc" are suffixes
            # Multi-token cases
            ("Big Energy Corp", "big-energy"),
            ("Super Utility Ltd", "super-utility"),
            # Edge case: suffix-only input (guard against over-stripping)
            ("Ltd", "ltd"),
            ("Inc", "inc"),
            ("LLC", "llc"),
        ],
    )
    def test_canonicalize_issuer_traces(self, raw: str | None, expected: str | None):
        """Test the canonicalize_issuer function against trace cases."""
        assert canonicalize_issuer(raw) == expected

    def test_co_is_not_a_suffix(self):
        """Regression test: "co" is preserved, not stripped (lessons A4)."""
        # The whole point of M1.5 is that "co" is NOT a suffix
        assert canonicalize_issuer("Power Co") == "power-co"
        assert canonicalize_issuer("Power Co.") == "power-co"
        assert canonicalize_issuer("PowerCo") == "power-co"

        # "company" is also not a suffix
        assert canonicalize_issuer("Power Company") == "power-company"

    def test_camelcase_suffix_fragmentation(self):
        """Test that camelCase fragmentation + re-joining works for suffixes."""
        # "GmbH" fragments to "Gmb H" via camelCase split, then rejoins to "gmbh"
        # which matches the suffix set, so both tokens are dropped
        assert canonicalize_issuer("Foo GmbH") == "foo"
        assert canonicalize_issuer("FooGmbH") == "foo"

        # Other fragmented suffixes
        assert canonicalize_issuer("BarPLC") == "bar"
        assert canonicalize_issuer("BazLLC") == "baz"

    def test_idempotence(self):
        """Test that canonicalize_issuer is idempotent."""
        # Canonical forms should remain unchanged when re-canonicalized
        canonical_forms = [
            "power-co",
            "aqua-util",
            "gov",
            "foo",
            "test",
        ]

        for canonical in canonical_forms:
            assert canonicalize_issuer(canonical) == canonical

        # Round-trip test: canonicalize(canonicalize(x)) == canonicalize(x)
        raw_forms = [
            "PowerCo",
            "Power Co.",
            "AquaUtil",
            "Foo GmbH",
            "Example Inc",
        ]

        for raw in raw_forms:
            once = canonicalize_issuer(raw)
            twice = canonicalize_issuer(once)
            assert twice == once

    def test_over_stripping_guard(self):
        """Test that we don't return None/empty when input is purely a suffix."""
        # If stripping would remove all tokens, keep the original
        assert canonicalize_issuer("Ltd") == "ltd"
        assert canonicalize_issuer("Inc") == "inc"
        assert canonicalize_issuer("LLC") == "llc"
        # GmbH gets camelCase-split to ["Gmb", "H"], which would be stripped entirely,
        # so the guard keeps the split tokens and joins them
        assert canonicalize_issuer("GmbH") == "gmb-h"


class TestEvalParity:
    """Shared-suite / eval-fixture parity test (M1.5 acceptance criterion)."""

    @staticmethod
    def resolve_evals_path() -> Path:
        """Resolve the path to wiki/evals/address/expected.json.

        Walks up from this file's directory to the first ancestor containing
        ``wiki/evals/address/expected.json``. Mirrors the pattern in
        ``bridge/src/bridge/skills.py::resolve_default_skills_dir``.

        Honors an ``ADDRESS_EVALS_PATH`` env override for parity with the mock
        (``agents/src/agents/mock_bridge/fixtures.py``).

        Returns:
            The resolved path to the evals fixture.

        Raises:
            FileNotFoundError: If the fixture file is not found.
        """
        # Check for env override first
        if env_path := os.environ.get("ADDRESS_EVALS_PATH"):
            path = Path(env_path)
            if path.exists():
                return path
            raise FileNotFoundError(f"ADDRESS_EVALS_PATH={env_path} does not exist")

        # Walk up from this file's directory
        current = Path(__file__).resolve().parent
        for ancestor in [current] + list(current.parents):
            candidate = ancestor / "wiki" / "evals" / "address" / "expected.json"
            if candidate.exists():
                return candidate

        raise FileNotFoundError(
            "wiki/evals/address/expected.json not found in any ancestor directory"
        )

    def test_eval_fixture_parity(self):
        """Assert parity with wiki/evals/address/expected.json (issuer_raw → issuer)."""
        fixture_path = self.resolve_evals_path()

        with fixture_path.open() as f:
            data = json.load(f)

        # The fixture has a "documents" array with issuer_raw and issuer fields
        documents = data["documents"]

        for doc in documents:
            raw = doc["issuer_raw"]
            expected = doc["issuer"]
            actual = canonicalize_issuer(raw)

            assert actual == expected, (
                f"Canonicalization mismatch for document {doc['id']}: "
                f"issuer_raw={raw!r} → expected={expected!r}, got={actual!r}"
            )

    def test_eval_fixture_examples(self):
        """Explicitly test the known examples from the fixture (documentation)."""
        # From the plan, the fixture contains:
        # - null → null
        # - "PowerCo" → "power-co"
        # - "Power Co." → "power-co"
        # - "AquaUtil" → "aqua-util"
        # - "Gov" → "gov"

        examples = [
            (None, None),
            ("PowerCo", "power-co"),
            ("Power Co.", "power-co"),
            ("AquaUtil", "aqua-util"),
            ("Gov", "gov"),
        ]

        for raw, expected in examples:
            assert canonicalize_issuer(raw) == expected
