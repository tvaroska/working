"""Local seam adapters factory.

Builds local adapter instances for each seam. This is the seam-selection home —
env-var selection (C3: BRIDGE_SEAM_*, BRIDGE_EXTRACTION_ENGINE) will layer on
here in M1.2+/deploy.

Local adapters:
- Sessions: InMemorySessionService (google.adk.sessions — native class, no skeleton)
- Task store: InMemoryTaskStore (a2a.server.tasks — native class, no skeleton)
- Exchange store: LocalExchangeStore (in-memory, M1.2 fills in behavior)
- Skill registry: LocalSkillRegistry (directory-backed, M1.3 fills in behavior)
- Scheduler: LocalScheduler (in-memory + virtual clock, M1.12 fills in behavior)
- Extraction: FixtureExtractionEngine (deterministic fixtures, M1.7 fills in behavior)

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


def build_local_adapter(seam: Seam) -> object:
    """Build and return a local adapter instance for the given seam.

    Args:
        seam: The seam to build an adapter for

    Returns:
        A local adapter instance conforming to the seam's Protocol

    Raises:
        ValueError: If the seam is not recognized

    Note: Env-var seam selection (C3: BRIDGE_SEAM_*, BRIDGE_EXTRACTION_ENGINE)
    will layer on here in M1.2+/deploy. Today this is a direct seam→adapter dispatch.
    """
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
