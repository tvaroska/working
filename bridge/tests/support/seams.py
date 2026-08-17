"""Seam test harness: one shared suite, two adapters.

Convention for testing managed-service seams with both local and GCP adapters.
The `adapter` fixture yields a built adapter instance, dispatched by the seam
marker on the test. `local` always runs; `gcp` only when BRIDGE_TEST_GCP=1 is set.

The same test asserts both adapters, locking parity: the mock→real and local→GCP
swaps must be no-ops for the agent.

See wiki/bridge-seams.md for the full rule and invariants.

M1.1 grew the fixture from yielding mode strings to yielding built instances;
GCP adapters land in Sprint 2.
"""

import os

import pytest

from bridge.adapters.local import build_local_adapter
from bridge.seams import Seam

__all__ = ["adapter", "gcp_test_enabled"]

ADAPTER_MODES = ("local", "gcp")


def gcp_test_enabled() -> bool:
    """Return True if GCP seam adapters should be tested (credentials present)."""
    return os.environ.get("BRIDGE_TEST_GCP") == "1"


@pytest.fixture(params=ADAPTER_MODES, ids=ADAPTER_MODES)
def adapter(request) -> object:
    """Yield a built adapter instance for the seam marker on this test.

    The test MUST have a @pytest.mark.seam(<name>) marker; this fixture reads it
    and builds the matching adapter for the current mode (local or gcp).

    `local` always runs (via build_local_adapter); `gcp` skips unless BRIDGE_TEST_GCP=1.

    Extraction axis nuance: Extraction is a capability axis (fixture|gemini|docai),
    not local↔gcp. The `local` param maps to the fixture engine; the `gcp` param
    skips with a message naming the axis nuance (no gcp adapter for extraction).

    Raises:
        pytest.fail: If the test is missing the @pytest.mark.seam(...) marker
    """
    mode = request.param

    # Read the seam from the test's marker (mandatory)
    marker = request.node.get_closest_marker("seam")
    if not marker or not marker.args:
        pytest.fail(
            "The `adapter` fixture requires a @pytest.mark.seam(<name>) marker. "
            "Use one of: sessions, task_store, exchange_store, skill_registry, "
            "scheduler, extraction."
        )

    seam = Seam(marker.args[0])

    # GCP branch: skip if not enabled; when enabled, still skip (Sprint 2)
    if mode == "gcp":
        if not gcp_test_enabled():
            pytest.skip("GCP seam adapter requires BRIDGE_TEST_GCP=1 (+ credentials)")

        # Extraction axis nuance: extraction is capability (fixture|gemini|docai),
        # not local↔gcp. Skip gcp param for extraction with a clear message.
        if seam == Seam.EXTRACTION:
            pytest.skip(
                "Extraction is a capability axis (fixture|gemini|docai), not "
                "local↔gcp. Gemini opts in via BRIDGE_TEST_GEMINI (Sprint 2). "
                "See wiki/bridge-seams.md §Axis nuance."
            )

        # All other seams: GCP adapters land in Sprint 2
        pytest.skip(f"{seam.value} GCP adapter lands in Sprint 2")

    # Local branch: build via the factory
    # Note: For extraction, this builds the fixture engine (the local capability)
    return build_local_adapter(seam)
