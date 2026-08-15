"""Scaffold smoke test: verify SDK pins and package imports."""

import importlib.metadata


def test_scaffold_imports():
    """Load-bearing SDKs and local packages are importable."""
    # Load-bearing SDKs from ADR-0001
    import a2a  # noqa: F401
    import google.adk  # noqa: F401
    import pydantic  # noqa: F401

    # Local packages (two-package src layout)
    import agents  # noqa: F401
    import contract  # noqa: F401


def test_adk_version_in_range():
    """google-adk is pinned to >=2.7.0,<3 per ADR-0001."""
    version_str = importlib.metadata.version("google-adk")
    major, minor, *_ = map(int, version_str.split(".")[:2])
    assert major == 2, f"Expected google-adk major version 2, got {major}"
    assert (major, minor) >= (2, 7), f"Expected google-adk >= 2.7, got {version_str}"


def test_a2a_sdk_present():
    """a2a-sdk is installed (no upper pin, just verify presence)."""
    version_str = importlib.metadata.version("a2a-sdk")
    assert version_str, "a2a-sdk version string should be non-empty"
