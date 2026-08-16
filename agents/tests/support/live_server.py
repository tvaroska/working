"""A live mock Bridge server for tests that need real HTTP sockets.

Runs :func:`agents.mock_bridge.create_app` under uvicorn in a daemon thread on a
free port. Used by the native-consumer seam tests (adr-0009), which exercise the
park/resume contract over the wire. ``park`` is passed through so a test can drive
the first-turn INPUT_REQUIRED pause + resume->COMPLETED path.
"""

import asyncio
import socket
import threading
import time

import uvicorn

from agents.mock_bridge import create_app


def free_port() -> int:
    """Allocate a free port on 127.0.0.1."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class LiveMockServer:
    """Context manager running the mock Bridge in a daemon thread.

    Picks a free port, creates the app with ``hold_seconds`` / ``park`` / ``scenario``,
    runs a uvicorn server in a daemon thread, and waits until it is ready. On exit,
    signals shutdown and joins the thread.
    """

    def __init__(
        self,
        *,
        hold_seconds: float = 1.0,
        park: bool = False,
        scenario=None,
        task_store=None,
    ):
        self.hold_seconds = hold_seconds
        self.park = park
        self.scenario = scenario
        self.task_store = task_store
        self.port = free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.card_url = f"{self.base_url}/.well-known/agent-card.json"
        self.server: uvicorn.Server | None = None
        self.thread: threading.Thread | None = None
        self.executor = None

    def __enter__(self) -> "LiveMockServer":
        app = create_app(
            self.base_url,
            scenario=self.scenario,
            hold_seconds=self.hold_seconds,
            park=self.park,
            task_store=self.task_store,
        )
        self.executor = app.state.mock_executor
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
                raise RuntimeError("mock server did not start within 5s")
            time.sleep(0.01)
        return self

    def __exit__(self, *exc_info):
        if self.server is not None:
            self.server.should_exit = True
        if self.thread is not None:
            self.thread.join(timeout=5)
