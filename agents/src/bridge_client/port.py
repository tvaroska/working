"""The transport-agnostic ``BridgeClient`` port.

The agent core talks to the Bridge only through this port:
``collect(request: CollectRequest) -> ExchangeTurn``. Whether an A2A mock or the
real Bridge answers is an adapter choice — the Sprint-1 mock->real swap is a
no-op for the agent because the agent never sees the transport.

This is the ``BridgeClient`` seam. In the repo's local/GCP framing this seam's
"adapters" are transport/target choices (A2A-to-mock now; A2A-to-real-Bridge in
Sprint 1), *not* an InMemory-vs-GCS backend pair, so M0 ships exactly one adapter
(``A2ABridgeClient``) and there is no GCP adapter here.
"""

import abc

from contract import CollectRequest, ExchangeTurn


class BridgeClientError(Exception):
    """Base error for any ``BridgeClient`` adapter failure.

    Adapters funnel transport, timeout, terminal-non-completed, and malformed
    payload failures into this single type so the agent (M0.5) has one stable
    exception to handle from the port.
    """


class BridgeTimeoutError(BridgeClientError):
    """Raised when a ``collect`` poll loop exceeds its deadline."""


class BridgeParkedError(BridgeClientError):
    """Raised when a collect parks at ``INPUT_REQUIRED`` / ``AUTH_REQUIRED``.

    A park is a **pause awaiting input, not a failure** (adr-0009). The M0
    tracer-bullet port has no resume path, so it surfaces the park as this
    distinct error rather than treating it as a generic terminal failure (which
    would misreport a resumable wait) or looping until the poll deadline (a
    silent hang). Parked collections require the native ``RemoteA2aAgent``
    consumer, which pauses/resumes via a ``LongRunningFunctionTool``.
    """


class BridgeClient(abc.ABC):
    """The abstract port the agent core talks through to reach the Bridge."""

    @abc.abstractmethod
    async def collect(self, request: CollectRequest) -> ExchangeTurn:
        """Ask the Bridge to collect documents; return the resulting turn.

        Async because every real adapter is I/O-bound and ADK tools accept
        coroutines. Adapters raise :class:`BridgeClientError` (or a subclass)
        on any failure.
        """
        raise NotImplementedError
