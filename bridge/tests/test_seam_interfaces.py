"""Seam interface conformance tests (M1.1).

These tests verify that:
1. The `adapter` fixture yields built instances conforming to their Protocol
2. build_local_adapter returns conforming instances for all seams
3. Skeleton methods raise NotImplementedError (documenting the M1.x deferral)

The fixture-based tests run twice (local, gcp); gcp skips until Sprint 2, proving
the parity wiring is intact. Direct factory tests run once (local only, no fixture).
"""

import pytest

from bridge.adapters.local import build_local_adapter
from bridge.adapters.local.exchange_store import LocalExchangeStore
from bridge.adapters.local.extraction import FixtureExtractionEngine
from bridge.adapters.local.scheduler import LocalScheduler
from bridge.adapters.local.skill_registry import LocalSkillRegistry
from bridge.seams import (
    ALL_SEAMS,
    ExchangeStoreSeam,
    ExtractionSeam,
    SchedulerSeam,
    Seam,
    SessionsSeam,
    SkillRegistrySeam,
    TaskStoreSeam,
)

# Fixture-based conformance tests (run against local + gcp when available)


@pytest.mark.seam("sessions")
def test_sessions_adapter_conforms(adapter):
    """Verify the sessions adapter conforms to SessionsSeam."""
    assert isinstance(adapter, SessionsSeam)


@pytest.mark.seam("task_store")
def test_task_store_adapter_conforms(adapter):
    """Verify the task_store adapter conforms to TaskStoreSeam."""
    assert isinstance(adapter, TaskStoreSeam)


@pytest.mark.seam("exchange_store")
def test_exchange_store_adapter_conforms(adapter):
    """Verify the exchange_store adapter conforms to ExchangeStoreSeam."""
    assert isinstance(adapter, ExchangeStoreSeam)


@pytest.mark.seam("skill_registry")
def test_skill_registry_adapter_conforms(adapter):
    """Verify the skill_registry adapter conforms to SkillRegistrySeam."""
    assert isinstance(adapter, SkillRegistrySeam)


@pytest.mark.seam("scheduler")
def test_scheduler_adapter_conforms(adapter):
    """Verify the scheduler adapter conforms to SchedulerSeam."""
    assert isinstance(adapter, SchedulerSeam)


@pytest.mark.seam("extraction")
def test_extraction_adapter_conforms(adapter):
    """Verify the extraction adapter conforms to ExtractionSeam."""
    assert isinstance(adapter, ExtractionSeam)


# Direct factory tests (no fixture, local only)


def test_build_local_adapter_all_seams_conform():
    """Verify build_local_adapter returns conforming instances for all seams."""
    seam_to_protocol = {
        Seam.SESSIONS: SessionsSeam,
        Seam.TASK_STORE: TaskStoreSeam,
        Seam.EXCHANGE_STORE: ExchangeStoreSeam,
        Seam.SKILL_REGISTRY: SkillRegistrySeam,
        Seam.SCHEDULER: SchedulerSeam,
        Seam.EXTRACTION: ExtractionSeam,
    }

    for seam in ALL_SEAMS:
        adapter = build_local_adapter(seam)
        protocol = seam_to_protocol[seam]
        assert isinstance(adapter, protocol), (
            f"build_local_adapter({seam}) returned {type(adapter).__name__}, "
            f"which does not conform to {protocol.__name__}"
        )


def test_build_local_adapter_unknown_seam_raises():
    """Verify build_local_adapter raises ValueError on an unknown seam."""
    # Use a string that's not a valid Seam (this will fail at Seam() construction,
    # so instead we mock a Seam-like value that the factory doesn't recognize)
    with pytest.raises(ValueError, match="Unknown seam"):
        # Create a mock value that looks like a Seam but isn't in the builders dict
        # We can't easily do this with the Enum, so we'll just test with a string
        # that would hypothetically be a seam value
        class FakeSeam:
            value = "unknown_seam"

        build_local_adapter(FakeSeam())  # type: ignore


# Skeleton deferral tests (document that NotImplementedError is raised)


@pytest.mark.anyio
async def test_exchange_store_skeleton_defers():
    """Verify LocalExchangeStore skeleton methods raise NotImplementedError."""
    store = LocalExchangeStore()

    with pytest.raises(NotImplementedError, match="M1.2"):
        await store.get("test-context")

    with pytest.raises(NotImplementedError, match="M1.2"):
        await store.save({})

    with pytest.raises(NotImplementedError, match="M1.2"):
        await store.materialize("test-context")


@pytest.mark.anyio
async def test_skill_registry_skeleton_defers():
    """Verify LocalSkillRegistry skeleton methods raise NotImplementedError."""
    registry = LocalSkillRegistry()

    with pytest.raises(NotImplementedError, match="M1.3"):
        await registry.list_skills()

    with pytest.raises(NotImplementedError, match="M1.3"):
        await registry.get_skill("test-skill")


@pytest.mark.anyio
async def test_scheduler_skeleton_defers():
    """Verify LocalScheduler skeleton methods raise NotImplementedError."""
    scheduler = LocalScheduler(clock=None)

    with pytest.raises(NotImplementedError, match="M1.12"):
        await scheduler.schedule({})

    with pytest.raises(NotImplementedError, match="M1.12"):
        await scheduler.due(None)

    with pytest.raises(NotImplementedError, match="M1.12"):
        await scheduler.cancel("test-timer")


@pytest.mark.anyio
async def test_extraction_skeleton_defers():
    """Verify FixtureExtractionEngine skeleton methods raise NotImplementedError."""
    engine = FixtureExtractionEngine()

    with pytest.raises(NotImplementedError, match="M1.7"):
        await engine.extract({}, {})
