"""Time-warp control BFF (Frontend-v1, port 8013, REST — no SSE, lessons B4).

Presenter control over the virtual clock: fast-forward an SLA window so
``overdue → escalated`` fires on cue; step / advance / reset (replay). This server
holds the shared :class:`~agents.address.__world.DemoWorld` clock + M1.12 scheduler
that ``ops_server`` reads, so advancing the clock here surfaces the escalation there
(within one process — see the ``_world`` cross-process caveat).

**No SSE, no background task** (B4): a virtual clock has no wall-clock progression,
so the clock only moves on an explicit request. The browser's "Play" is a
``setInterval`` calling ``/timewarp/advance`` — the server never runs a timer of its
own (which dodges the SSE fan-out / orphaned-background-task problem ops solves).

Wire shape (snake_case):

- ``GET /timewarp/state`` → ``{"now", "sla":{"deadline","cadence","max_nudges"},
  "timers":[…], "followup":{…}}``
- ``POST /timewarp/advance`` body ``{"ticks": int}`` → advance N ticks, fire due
  timers (exactly-once, A7), return the new state.
- ``POST /timewarp/step`` → advance one tick.
- ``POST /timewarp/reset`` → reset the clock/scenario (replay).

Demo furniture (A9).
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ._bff import cors_middleware, health_route, json_response
from ._world import CHASING_EXCHANGE, DemoWorld

__all__ = ["create_app", "app"]


def _state(world: DemoWorld) -> dict:
    followup = world.followups_for(CHASING_EXCHANGE)
    return {
        "now": world.now(),
        "sla": {
            "deadline": world.sla.deadline,
            "cadence": world.sla.cadence,
            "max_nudges": world.sla.max_nudges,
        },
        "timers": [
            {
                "id": timer.id,
                "context_id": timer.context_id,
                "fire_at": timer.fire_at,
                "kind": timer.kind.value,
                "sequence": timer.sequence,
                "fired": timer.fired,
            }
            for timer in sorted(
                world.scheduler._timers.values(), key=lambda t: (t.fire_at, t.sequence, t.id)
            )
        ],
        "followup": {
            "state": followup.state.value,
            "nudges_fired": followup.nudges_fired,
            "escalated": followup.escalated,
        },
    }


def create_app(world: DemoWorld | None = None) -> Starlette:
    """Create the time-warp BFF app (share ``world`` with ``ops_server``)."""
    world = world or DemoWorld()

    async def _get_state(_request: Request) -> JSONResponse:
        return json_response(_state(world))

    async def _advance(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            body = {}
        ticks = int(body.get("ticks", 1))
        if ticks < 0:
            return json_response({"error": "ticks must be non-negative"}, status_code=400)
        fired = await world.advance(ticks)
        return json_response({"fired": [t.id for t in fired], "state": _state(world)})

    async def _step(_request: Request) -> JSONResponse:
        fired = await world.step()
        return json_response({"fired": [t.id for t in fired], "state": _state(world)})

    async def _reset(_request: Request) -> JSONResponse:
        world.reset()
        return json_response({"reset": True, "state": _state(world)})

    routes = [
        health_route(),
        Route("/timewarp/state", _get_state, methods=["GET"]),
        Route("/timewarp/advance", _advance, methods=["POST"]),
        Route("/timewarp/step", _step, methods=["POST"]),
        Route("/timewarp/reset", _reset, methods=["POST"]),
    ]
    app = Starlette(routes=routes, middleware=cors_middleware())
    app.state.world = world
    return app


# Module-level app so ``uvicorn agents.address.timewarp_server:app`` works (C2).
app = create_app()
