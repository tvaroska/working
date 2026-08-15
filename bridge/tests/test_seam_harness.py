"""Placeholder parametrized test exercising the seam harness convention.

These tests lock the convention established in S0.3:
- The `adapter` fixture yields "local" always and "gcp" only under BRIDGE_TEST_GCP=1
- The six seam names are enumerated and stable
- The @pytest.mark.seam(...) marker is wired and validated

Sprint 1 will replace these placeholders with real seam tests as interfaces land.
"""

import pytest

from bridge.seams import ALL_SEAMS, Seam


@pytest.mark.seam("sessions")
def test_adapter_fixture_yields_local_always(adapter):
    """Verify adapter fixture parametrization: local always, gcp opt-in.

    This runs twice (ids: local, gcp). In CI (BRIDGE_TEST_GCP unset), the gcp id
    skips and local passes, proving the two-adapter parametrization + skip wiring.
    """
    assert adapter in {"local", "gcp"}


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


@pytest.mark.parametrize("seam", list(ALL_SEAMS))
def test_seam_enum_roundtrip(seam):
    """Verify each seam enum value is a valid string (composes with marker)."""
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
