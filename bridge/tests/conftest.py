"""Shared pytest fixtures and configuration."""

import pytest

from bridge.seams import Seam

# Re-export seam fixtures so tests can use them without importing from support
from tests.support.seams import adapter, gcp_test_enabled  # noqa: F401


def pytest_configure(config):
    """Validate seam marker usage at collection time."""
    # Register valid seam names for runtime validation
    config.addinivalue_line(
        "markers", "seam(name): marks test as covering a specific managed-service seam"
    )


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    """Guard: assert every seam(...) marker uses a value in Seam enum."""
    valid_seams = {s.value for s in Seam}

    for item in items:
        for marker in item.iter_markers(name="seam"):
            if marker.args:
                seam_name = marker.args[0]
                if seam_name not in valid_seams:
                    raise ValueError(
                        f"Invalid seam marker '{seam_name}' on {item.nodeid}. "
                        f"Valid seams: {sorted(valid_seams)}"
                    )
