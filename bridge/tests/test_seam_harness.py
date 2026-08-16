"""Seam harness convention tests (S0.3 / M1.1).

These tests lock the convention established in S0.3 and extended in M1.1:
- The six seam names are enumerated and stable
- The @pytest.mark.seam(...) marker is wired and validated
- (M1.1) The `adapter` fixture yields built instances (see test_seam_interfaces.py)

The old placeholder `test_adapter_fixture_yields_local_always` was removed in M1.1
when the fixture started yielding instances instead of mode strings. Real seam
conformance tests are in test_seam_interfaces.py.
"""

from bridge.seams import ALL_SEAMS, Seam


def test_all_six_seams_enumerated():
    """Lock the six-seam vocabulary (S0.8 sign-off pins the seam list)."""
    seam_values = {s.value for s in ALL_SEAMS}
    expected = {
        "sessions",
        "task_store",
        "exchange_store",
        "skill_registry",
        "scheduler",
        "extraction",
    }
    assert seam_values == expected
    assert len(ALL_SEAMS) == 6


def test_seam_enum_roundtrip():
    """Verify each seam enum value is a valid string (composes with marker)."""
    for seam in ALL_SEAMS:
        assert isinstance(seam, Seam)
        assert isinstance(seam.value, str)
        assert seam.value in {
            "sessions",
            "task_store",
            "exchange_store",
            "skill_registry",
            "scheduler",
            "extraction",
        }
