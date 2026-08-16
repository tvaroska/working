"""Shared plumbing for the Frontend-v1 demo BFF servers (Frontend-v1).

The four demo servers (``console_server`` / ``ops_server`` — SSE; ``portal_server``
/ ``timewarp_server`` — REST) are **demo furniture** (lessons A9): thin Python
Starlette apps that project the already-built local components (the address graph,
the A2UI edge, the M1.12 scheduler) onto the three actor surfaces + the time-warp
control. They are the only agent-side code allowed to ``import bridge``; the
production agent (``agent.py``/``graph.py``) never imports them.

Conventions shared by all four (kept here so each server file stays small):

- **Snake_case JSON on the wire** — every surface hand-maps to camelCase in its own
  TS ``domain/`` layer (lessons B3). Servers never emit camelCase.
- **CORS** for the Vite dev origins (dev only).
- **A ``GET /health``** returning ``{"status": "ok"}``.
- **SSE** via raw Starlette ``StreamingResponse`` (media type ``text/event-stream``).
  The generator yields named frames — ``event: snapshot`` / ``event: turn`` /
  ``event: event`` — then a terminal ``event: done`` and returns (a clean close).
  Because the generator is finite (it ends after ``done``) the whole scripted
  stream is one body: the browser ``EventSource`` closes on ``done`` and never
  reconnects (lessons B1/B2), and a test can read the full body and parse frames.

Decision (Frontend-v1 §4): SSE uses raw Starlette ``StreamingResponse`` rather than
``sse-starlette`` — it matches the repo's existing Starlette usage, avoids a new
dependency, and gives byte-exact control over the frame framing that the one-shot
Playwright stub (``e2e/sse.ts``) mirrors.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable
from typing import Any

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

__all__ = [
    "DEV_ORIGINS",
    "cors_middleware",
    "health_route",
    "sse_frame",
    "sse_response",
    "json_response",
]

# The Vite dev origins the surfaces are served from (host shell on 5173, the
# Playwright preview on 4173). Dev-only — production zoning is the network layer
# (Sprint 2, not here).
DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]


def cors_middleware() -> list[Middleware]:
    """CORS middleware allowing the Vite dev origins (dev only)."""
    return [
        Middleware(
            CORSMiddleware,
            allow_origins=DEV_ORIGINS,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]


async def _health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def health_route() -> Route:
    """A ``GET /health`` route returning ``{"status": "ok"}``."""
    return Route("/health", _health, methods=["GET"])


def sse_frame(event: str, data: Any) -> str:
    """Format one named SSE frame (``event:`` + ``data:`` + blank line)."""
    payload = json.dumps(data, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


def sse_response(frames: Iterable[tuple[str, Any]]) -> StreamingResponse:
    """Stream a finite sequence of ``(event, data)`` frames as ``text/event-stream``.

    The caller supplies every frame including the terminal ``("done", ...)`` frame;
    the generator ends after the last frame so the connection closes cleanly (B2).
    """

    async def _emit() -> AsyncIterator[str]:
        for event, data in frames:
            yield sse_frame(event, data)

    return StreamingResponse(
        _emit(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def json_response(data: Any, status_code: int = 200) -> JSONResponse:
    """A snake_case JSON response (the wire is snake_case — B3)."""
    return JSONResponse(data, status_code=status_code)
