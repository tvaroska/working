"""Live Bridge test servers running under uvicorn on a free port.

Runs a Bridge app (mock or real edge) under uvicorn in a daemon thread on a free
port. Used by the native-consumer seam tests (adr-0009) and the M1.13 mock→real
parity suite, which exercise the park/resume contract over the wire.

:class:`_ThreadedUvicornServer` holds the shared free-port / daemon-thread /
readiness-wait plumbing; :class:`LiveMockServer` builds the mock Bridge and
:class:`~tests.support.live_bridge_server.LiveBridgeServer` builds the real edge.
Both expose an identical ``base_url`` / ``card_url`` shape — the card URL is the
sole swap point for the consumer (M1.13).
"""

import asyncio
import socket
import threading
import time

import uvicorn
from starlette.applications import Starlette

from agents.mock_bridge import create_app


def free_port() -> int:
    """Allocate a free port on 127.0.0.1."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _ThreadedUvicornServer:
    """Context manager base: run a Starlette app under uvicorn in a daemon thread.

    Subclasses implement :meth:`_build_app` to assemble the app on a chosen free
    port; the base picks the port, exposes ``base_url`` / ``card_url``, runs the
    server, waits for readiness, and joins the thread on exit.
    """

    def __init__(self) -> None:
        self.port = free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.card_url = f"{self.base_url}/.well-known/agent-card.json"
        self.server: uvicorn.Server | None = None
        self.thread: threading.Thread | None = None

    def _build_app(self) -> Starlette:  # pragma: no cover - overridden
        raise NotImplementedError

    def __enter__(self):
        app = self._build_app()
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
        )
        self.server = uvicorn.Server(config)

        def _run_server():
            asyncio.run(self.server.serve())

        self.thread = threading.Thread(target=_run_server, daemon=True)
        self.thread.start()

        deadline = time.time() + 5
        while not self.server.started:
            if time.time() > deadline:
                raise RuntimeError(f"{type(self).__name__} did not start within 5s")
            time.sleep(0.01)
        return self

    def __exit__(self, *exc_info):
        if self.server is not None:
            self.server.should_exit = True
        if self.thread is not None:
            self.thread.join(timeout=5)


class LiveMockServer(_ThreadedUvicornServer):
    """Context manager running the mock Bridge in a daemon thread.

    Creates the app with ``hold_seconds`` / ``park`` / ``scenario`` / ``task_store``.
    ``park`` is passed through so a test can drive the first-turn INPUT_REQUIRED pause
    + resume->COMPLETED path.
    """

    def __init__(
        self,
        *,
        hold_seconds: float = 1.0,
        park: bool = False,
        scenario=None,
        task_store=None,
    ):
        super().__init__()
        self.hold_seconds = hold_seconds
        self.park = park
        self.scenario = scenario
        self.task_store = task_store
        self.executor = None

    def _build_app(self) -> Starlette:
        app = create_app(
            self.base_url,
            scenario=self.scenario,
            hold_seconds=self.hold_seconds,
            park=self.park,
            task_store=self.task_store,
        )
        self.executor = app.state.mock_executor
        return app
