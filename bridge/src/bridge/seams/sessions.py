"""Sessions seam: task ≈ ADK session (state restore is platform-default).

Each A2A leg corresponds to one durable ADK session. The local adapter uses
InMemorySessionService; the GCP adapter uses VertexAiSessionService or
DatabaseSessionService. See wiki/bridge-seams.md for the full contract.

CAVEAT: @runtime_checkable Protocols check method presence only, not signatures.
This is the desired behavior for M1.1 conformance smoke tests — real behavior and
signature validation are pinned by the shared suite in M1.2+. Keep every Protocol
method-only (no data attributes) or isinstance will raise/misbehave.

Invariant (lessons-learned.md A13): Session/task state restore is mostly DEFAULT —
the platform provides it when using durable session/task stores. The webhook is a
doorbell, not a restore mechanism.
"""

from typing import Protocol, runtime_checkable

from google.adk.events import Event
from google.adk.sessions import Session

__all__ = ["SessionsSeam"]


@runtime_checkable
class SessionsSeam(Protocol):
    """Seam for session management (mirrors BaseSessionService subset).

    Local adapter: InMemorySessionService (google.adk.sessions)
    GCP adapter: VertexAiSessionService or DatabaseSessionService (Sprint 2)

    Methods mirror the BaseSessionService API that the Bridge uses.
    """

    async def create_session(self, **kwargs) -> Session:
        """Create a new session."""
        ...

    async def get_session(self, session_id: str, **kwargs) -> Session:
        """Retrieve a session by ID."""
        ...

    async def delete_session(self, session_id: str, **kwargs) -> None:
        """Delete a session."""
        ...

    async def list_sessions(self, **kwargs) -> list[Session]:
        """List all sessions."""
        ...

    async def append_event(self, session_id: str, event: Event, **kwargs) -> None:
        """Append an event to a session."""
        ...
