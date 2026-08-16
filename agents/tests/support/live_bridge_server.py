"""A live *real* Bridge edge server for the M1.13 mock→real parity suite.

Mirrors :class:`~tests.support.live_server.LiveMockServer` but assembles the real
inbound A2A edge (:func:`bridge.edges.a2a.app.create_app`) instead of the mock. It
serves the identical wire contract behind an identical ``base_url`` / ``card_url``
shape, so the durable graph consumer swaps between the two by card URL only.

Test-only cross-package dependency: ``agents/`` tests import ``bridge/`` (one
directional — ``bridge/`` never imports ``agents/``; lessons A9). The production
agent never imports ``bridge``.
"""

from bridge.edges.a2a.app import create_app
from starlette.applications import Starlette

from tests.support.live_server import _ThreadedUvicornServer


class LiveBridgeServer(_ThreadedUvicornServer):
    """Context manager running the real Bridge edge in a daemon thread.

    Creates the app with ``collect_plan`` / ``hold_seconds`` / ``strict`` /
    ``task_store``. Exposes ``executor`` (``app.state.executor``) for parity with the
    mock's ``app.state.mock_executor`` in case a test wants to introspect captured
    requests.
    """

    def __init__(
        self,
        *,
        collect_plan=None,
        hold_seconds: float = 0.02,
        strict: bool = False,
        task_store=None,
    ):
        super().__init__()
        self.collect_plan = collect_plan
        self.hold_seconds = hold_seconds
        self.strict = strict
        self.task_store = task_store
        self.executor = None

    def _build_app(self) -> Starlette:
        app = create_app(
            self.base_url,
            collect_plan=self.collect_plan,
            hold_seconds=self.hold_seconds,
            strict=self.strict,
            task_store=self.task_store,
        )
        self.executor = app.state.executor
        return app
