"""Local seam adapters factory.

Builds local adapter instances for each seam. This is the seam-selection home —
env-var selection (C3: BRIDGE_SEAM_*, BRIDGE_EXTRACTION_ENGINE) will layer on
here in M1.2+/deploy.

Local adapters:
- Sessions: InMemorySessionService (google.adk.sessions — native class, no skeleton)
- Task store: InMemoryTaskStore (a2a.server.tasks — native class, no skeleton)
- Exchange store: LocalExchangeStore (in-memory, M1.2)
- Skill registry: LocalSkillRegistry (directory-backed, loads Agent Skills folders +
    builds dynamic Agent Card; BRIDGE_SKILLS_DIR env override, M1.3)
- Scheduler: LocalScheduler (in-memory + virtual clock, M1.12)
- Extraction: FixtureExtractionEngine (deterministic fixtures, M1.7)

GCP adapters land in Sprint 2 via a parallel build_gcp_adapter factory.
"""

from a2a.server.tasks import InMemoryTaskStore
from google.adk.sessions import InMemorySessionService

from bridge.adapters.local.exchange_store import LocalExchangeStore
from bridge.adapters.local.extraction import FixtureExtractionEngine
from bridge.adapters.local.scheduler import LocalScheduler
from bridge.adapters.local.skill_registry import LocalSkillRegistry
from bridge.seams import Seam

__all__ = ["build_local_adapter"]


def build_local_adapter(seam: Seam, *, durable: bool = False, db_path: str | None = None) -> object:
    """Build and return a local adapter instance for the given seam.

    Args:
        seam: The seam to build an adapter for.
        durable: When True, SESSIONS/TASK_STORE return the SQLite-backed
            ``Database*`` variants (survive a process restart — lessons A13); the
            other seams ignore it. ``db_path`` is then required. Default False
            keeps the M1.1 in-memory behavior.
        db_path: Filesystem path for the SQLite database when ``durable=True``.

    Returns:
        A local adapter instance conforming to the seam's Protocol.

    Raises:
        ValueError: If the seam is not recognized, or ``durable=True`` is requested
            for SESSIONS/TASK_STORE without a ``db_path``.

    Note: Env-var seam selection (C3: BRIDGE_SEAM_*, BRIDGE_EXTRACTION_ENGINE)
    will layer on here in M1.2+/deploy. Today this is a direct seam→adapter dispatch.
    The durable variant keeps the "swap is a no-op for the agent" idiom: same seam,
    same Protocol, storage swapped (InMemory* ↔ Database* on sqlite+aiosqlite).
    """
    if durable and seam in (Seam.SESSIONS, Seam.TASK_STORE):
        if not db_path:
            raise ValueError(f"durable={seam.value} requires a db_path")
        # Lazy import so a plain `import bridge.adapters.local` does not pull
        # sqlalchemy unless a durable adapter is actually requested.
        from sqlalchemy.ext.asyncio import create_async_engine

        db_url = f"sqlite+aiosqlite:///{db_path}"
        if seam == Seam.SESSIONS:
            from google.adk.sessions import DatabaseSessionService

            return DatabaseSessionService(db_url=db_url)
        from a2a.server.tasks import DatabaseTaskStore

        return DatabaseTaskStore(engine=create_async_engine(db_url), create_table=True)

    builders = {
        Seam.SESSIONS: lambda: InMemorySessionService(),
        Seam.TASK_STORE: lambda: InMemoryTaskStore(),
        Seam.EXCHANGE_STORE: lambda: LocalExchangeStore(),
        Seam.SKILL_REGISTRY: lambda: LocalSkillRegistry(),
        Seam.SCHEDULER: lambda: LocalScheduler(clock=None),
        Seam.EXTRACTION: lambda: FixtureExtractionEngine(),
    }

    if seam not in builders:
        raise ValueError(f"Unknown seam: {seam}")

    return builders[seam]()
