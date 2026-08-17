"""Servicer Ops Dashboard BFF (Frontend-v1, port 8011, SSE).

The read-model surface: exchanges in flight, each exchange's classified ledger
filling live, disposition outcomes, and the **HITL** + **escalation** queues.
Escalation surfaces from the M1.12 scheduler ladder driven by the shared
:class:`~agents.address.__world.DemoWorld` clock — advancing the clock in
``timewarp_server`` moves an exchange ``overdue → escalated`` here.

Wire shape (snake_case — the TS ``ops-dashboard/src/domain/readModel.ts`` projects
to camel + groups by actionable state, lessons B3):

- ``GET /ops/state`` → the read-model snapshot (REST convenience for polling/tests).
- ``GET /ops/stream`` → SSE: ``event: snapshot`` (the read-model) then one
  ``event: event`` per escalated exchange, then ``event: done``.
- ``POST /ops/hitl/{doc_id}/{approve|reject}`` → resolve a HITL item; returns the
  refreshed snapshot.

The server sends *raw* ledger / queue snapshots; the grouping/projection (per
exchange, by actionable state) is the TS domain layer (B3). Demo furniture (A9).
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ._bff import cors_middleware, health_route, json_response, sse_response
from ._world import DemoWorld

__all__ = ["create_app", "app"]


def _stream_frames(world: DemoWorld) -> list[tuple[str, object]]:
    snapshot = world.read_model()
    frames: list[tuple[str, object]] = [("snapshot", snapshot)]
    for item in snapshot["escalation_queue"]:
        frames.append(("event", {"type": "followup", **item}))
    frames.append(("done", {"exchanges": len(snapshot["exchanges"])}))
    return frames


def create_app(world: DemoWorld | None = None) -> Starlette:
    """Create the Ops Dashboard BFF app.

    Args:
        world: The shared demo world (clock + scheduler + read-model). Pass the same
            instance to ``timewarp_server.create_app`` so time-warp escalations show
            up here (within one process — see ``_world`` cross-process caveat).
    """
    world = world or DemoWorld()

    async def _state(_request: Request) -> JSONResponse:
        return json_response(world.read_model())

    async def _stream(_request: Request):
        return sse_response(_stream_frames(world))

    async def _hitl(request: Request) -> JSONResponse:
        doc_id = request.path_params["doc_id"]
        action = request.path_params["action"]
        if action not in ("approve", "reject"):
            return json_response({"error": f"unknown action: {action}"}, status_code=400)
        found = world.resolve_hitl(doc_id, accept=action == "approve")
        if not found:
            return json_response({"error": f"no pending HITL item: {doc_id}"}, status_code=404)
        return json_response({"resolved": doc_id, "action": action, "state": world.read_model()})

    routes = [
        health_route(),
        Route("/ops/state", _state, methods=["GET"]),
        Route("/ops/stream", _stream, methods=["GET"]),
        Route("/ops/hitl/{doc_id}/{action}", _hitl, methods=["POST"]),
    ]
    app = Starlette(routes=routes, middleware=cors_middleware())
    app.state.world = world
    return app


# Module-level app so ``uvicorn agents.address.ops_server:app`` works (C2).
app = create_app()
