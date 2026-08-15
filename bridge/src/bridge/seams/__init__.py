"""Managed-service seams — Sprint-1 interfaces + Sprint-2 GCP adapters.

This package defines the six managed-service boundaries where the Bridge swaps adapters:
Sessions, Task store, Exchange store, Skill registry, Scheduler, and Extraction.

Each seam has two adapters: a local adapter (fast dev/test) and a GCP adapter (deployed).
The same test suite runs against both adapters, ensuring parity.

Sprint 1 will add seam interface definitions (Protocols/ABCs) here; Sprint 2 will add
the GCP adapter implementations. As of S0.3, only the enumeration exists.
"""

from enum import Enum

__all__ = ["Seam", "ALL_SEAMS"]


class Seam(str, Enum):
    """The six managed-service seams.

    Five are local↔gcp storage/infra seams (Sessions, Task store, Exchange store,
    Skill registry, Scheduler); Extraction is the capability axis (fixture|gemini|docai),
    deployed either way.
    """

    # Local↔GCP storage/infra seams
    SESSIONS = "sessions"
    TASK_STORE = "task_store"
    EXCHANGE_STORE = "exchange_store"
    SKILL_REGISTRY = "skill_registry"
    SCHEDULER = "scheduler"

    # Capability axis (fixture|gemini|docai), not local/gcp
    EXTRACTION = "extraction"


ALL_SEAMS: tuple[Seam, ...] = tuple(Seam)
