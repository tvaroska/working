"""A2UI edge — content-not-pixels human surface (M1.10).

The Bridge's **human-facing edge**: the party-status view + Path-B intake feed.
This is the end-user/provider portal surface (wiki/bridge-a2ui-edge.md), one of
several A2UI surfaces (HITL review / internal dashboard are others, future).

Four capabilities:
1. **Emit declarative view/intake models** — content-not-pixels (what to show /
   what comes back), JSON-serializable, consumed by any host renderer.
2. **Ingest structured response** — A2uiResponse + mapper to Path-B intake document.
3. **Feed Path-B intake into the extraction graph** — pass to run_fulfillment (M1.7),
   threading attempts for the resubmission loop.
4. **Render the party-status view** — projection over CollectionStatus (M1.4) +
   RequirementsList (M1.9), plus a reference text renderer (demo furniture).

The view models are **bridge-local** (not contract/) — the A2A edge keeps
plan.py/trust.py/executor bridge-local; the A2UI edge keeps its declarative
shapes here. The frontend consumes JSON, not the Python types, so there is no
cross-language sharing pressure.

The reference renderer is **demo furniture, not the product** — it proves the
content-not-pixels contract without a real frontend. Any host renders the same
A2uiScreen in its own design system (wiki/bridge-a2ui-edge.md).

Import discipline: imports contract + bridge.fulfillment + bridge.requirements +
bridge.seams.extraction + bridge.adapters.local.extraction (edges may import
adapters — see bridge/src/bridge/edges/__init__.py docstring; the A2A edge
already imports bridge.adapters.local.*). Never imports agents/. Keep this out
of bridge/__init__.py (preserve cheap import bridge + no-agents-guard clarity).
"""

from .intake import A2uiResponse, IntakeMode, intake_to_document, submit_intake
from .renderer import render_screen
from .views import (
    A2uiScreen,
    DocStatus,
    IntakeSpec,
    PartyStatusView,
    ResponseField,
    build_screen,
    party_status_view,
)

__all__ = [
    # View models + projection
    "DocStatus",
    "ResponseField",
    "IntakeSpec",
    "PartyStatusView",
    "A2uiScreen",
    "party_status_view",
    "build_screen",
    # Intake + feed
    "IntakeMode",
    "A2uiResponse",
    "intake_to_document",
    "submit_intake",
    # Renderer (demo furniture)
    "render_screen",
]
