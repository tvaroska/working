"""Isolation guard: `bridge` must never import the `agents` package (CLAUDE.md invariant)."""

import sys


def test_bridge_does_not_import_agents():
    import bridge  # noqa: F401

    offenders = [m for m in sys.modules if m == "agents" or m.startswith("agents.")]
    assert not offenders, f"bridge pulled in agents modules: {sorted(offenders)}"
