"""Bridge edges — A2A (inbound, M1.8) and A2UI (M1.10).

Edges assemble the core behind a transport; they may import seams/adapters/core.
Never imported by core modules (the dependency direction is edges → core, never the
reverse). Kept out of ``bridge/__init__.py`` so ``import bridge`` stays cheap and the
no-agents-import guard stays clear.
"""
