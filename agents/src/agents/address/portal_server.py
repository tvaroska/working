"""Provider Portal BFF (Frontend-v1, port 8012, REST) — A2UI Path-B.

The external-zone surface across the trust boundary: the party uploads a document
(a fixture id in local/demo) and sees its disposition + what is still outstanding.
A thin wrapper over the M1.10 A2UI edge (``build_screen`` / ``submit_intake``):
**content-not-pixels** — the server emits the declarative ``A2uiScreen`` and the
React portal renders it in MUI (the reference ``render_screen`` stays demo furniture).

Wire shape (snake_case — the TS ``provider-portal/src/domain/outstanding.ts`` maps
to camel, lessons B3):

- ``GET /portal/screen?context=<id>`` → ``build_screen(status, requirements)`` JSON.
- ``POST /portal/intake`` body ``{"context", "mode", "fixture_id", "text?", "fields?"}``
  → ``submit_intake(...)`` → ``{"fulfillment": FulfillmentResult, "screen": A2uiScreen}``.
  ``attempts`` are threaded per-context for the non-resumable resubmit loop (A1).

Demo furniture (A9): imports the A2UI edge + fixture engine from ``bridge``.
"""

from __future__ import annotations

from bridge.adapters.local.extraction import FixtureExtractionEngine
from bridge.adapters.local.skill_registry import LocalSkillRegistry
from bridge.edges.a2ui import A2uiResponse, IntakeMode, build_screen, submit_intake
from bridge.requirements import SkillExplanations, load_explanations, propose_requirements
from contract import CollectionStatus, LedgerEntry
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ._bff import cors_middleware, health_route, json_response

__all__ = ["create_app", "app"]

DEFAULT_CONTEXT = "portal-demo"


def _explanations() -> SkillExplanations:
    """Load the address-proof skill's verbatim explanations (M1.9 relay)."""
    skill = LocalSkillRegistry()._skills.get("address-proof")
    return load_explanations(skill) if skill is not None else SkillExplanations()


class _PortalContext:
    """Per-context portal state: the submitted ledger + resubmission attempts (A1)."""

    def __init__(self) -> None:
        self.ledger: list[LedgerEntry] = []
        self.attempts: int = 0

    def upsert(self, entry: LedgerEntry) -> None:
        for i, existing in enumerate(self.ledger):
            if existing.id == entry.id:
                self.ledger[i] = entry
                return
        self.ledger.append(entry)

    def status(self) -> CollectionStatus:
        return CollectionStatus(ledger=list(self.ledger))


def create_app() -> Starlette:
    """Create the Provider Portal BFF app (A2UI Path-B wrapper)."""
    engine = FixtureExtractionEngine()
    explanations = _explanations()
    contexts: dict[str, _PortalContext] = {}

    def _context(context_id: str) -> _PortalContext:
        return contexts.setdefault(context_id, _PortalContext())

    def _screen_json(ctx: _PortalContext) -> dict:
        status = ctx.status()
        requirements = propose_requirements(status, explanations=explanations)
        return build_screen(status, requirements).model_dump(mode="json")

    async def _screen(request: Request) -> JSONResponse:
        context_id = request.query_params.get("context") or DEFAULT_CONTEXT
        return json_response(_screen_json(_context(context_id)))

    async def _intake(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return json_response({"error": "invalid JSON body"}, status_code=400)

        context_id = body.get("context") or DEFAULT_CONTEXT
        ctx = _context(context_id)

        try:
            response = A2uiResponse(
                mode=IntakeMode(body.get("mode", "upload")),
                fixture_id=body.get("fixture_id"),
                text=body.get("text"),
                fields=body.get("fields") or {},
            )
        except Exception as exc:  # bad mode / shape
            return json_response({"error": f"invalid intake: {exc}"}, status_code=400)

        try:
            result = await submit_intake(response, engine=engine, attempts=ctx.attempts)
        except ValueError as exc:  # e.g. missing fixture_id in Phase-1 local
            return json_response({"error": str(exc)}, status_code=400)

        # Record the classified entry into the context ledger so the refreshed screen
        # reflects it. Thread attempts forward on the non-resumable resubmit loop (A1).
        if result.entry is not None:
            ctx.upsert(result.entry)
        if result.awaiting_resubmission:
            ctx.attempts = result.attempts

        payload = {
            "fulfillment": result.model_dump(mode="json"),
            "screen": _screen_json(ctx),
        }
        return json_response(payload)

    routes = [
        health_route(),
        Route("/portal/screen", _screen, methods=["GET"]),
        Route("/portal/intake", _intake, methods=["POST"]),
    ]
    app = Starlette(routes=routes, middleware=cors_middleware())
    app.state.contexts = contexts
    return app


# Module-level app so ``uvicorn agents.address.portal_server:app`` works (C2).
app = create_app()
