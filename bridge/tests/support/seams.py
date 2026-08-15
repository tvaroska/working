"""Seam test harness: one shared suite, two adapters.

Convention for testing managed-service seams with both local and GCP adapters.
The `adapter` fixture yields `local` always (runs in every env) and `gcp` only
when BRIDGE_TEST_GCP=1 is set (skips otherwise, e.g. in CI without credentials).

The same test asserts both adapters, locking parity: the mock→real and local→GCP
swaps must be no-ops for the agent.

See wiki/bridge-seams.md for the full rule and invariants.

Sprint 1 extends the `adapter` fixture to build actual adapter instances per seam;
S0.3 yields the mode string to lock the convention and CI skip wiring first.
"""

import os

import pytest

__all__ = ["adapter", "gcp_test_enabled"]

ADAPTER_MODES = ("local", "gcp")


def gcp_test_enabled() -> bool:
    """Return True if GCP seam adapters should be tested (credentials present)."""
    return os.environ.get("BRIDGE_TEST_GCP") == "1"


@pytest.fixture(params=ADAPTER_MODES, ids=ADAPTER_MODES)
def adapter(request) -> str:
    """Yield each seam-adapter mode. `local` always; `gcp` only under BRIDGE_TEST_GCP=1.

    Sprint 1 extends this to build the actual adapter instance per seam+mode;
    S0.3 yields the mode string so the convention (and the CI skip) is locked first.

    NOTE (Sprint-1 extension point): This fixture will grow a per-seam dispatch
    (read the `seam` marker off `request.node`, build the matching local/GCP adapter)
    once interfaces exist; today it returns the mode string only.
    """
    mode = request.param
    if mode == "gcp" and not gcp_test_enabled():
        pytest.skip("GCP seam adapter requires BRIDGE_TEST_GCP=1 (+ credentials)")
    return mode
