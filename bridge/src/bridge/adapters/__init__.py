"""Seam adapter implementations (local + GCP).

This package contains the concrete adapter implementations for each seam:
- local/: In-memory / local adapters (fast dev/test, virtual clock)
- gcp/: GCP-backed adapters (Sprint 2 — deployed, persistent)

See bridge.seams for the seam Protocol definitions and wiki/bridge-seams.md
for the full adapter contract.
"""
