"""Scheduler acceptance tests (M1.12).

Tests the proactive follow-up scheduler: VirtualClock, plan_followups (SLA engine),
due() exactly-once emission (A7), deterministic ordering (A5), and the followup_status
read-model.

Key invariants tested:
- A7 (exactly-once): due(now) marks timers fired in place and NEVER re-returns them.
- A5 (deterministic ordering): due() output is sorted by (fire_at, sequence, id).
- SLA ladder: derived from the skill policy (deadline/cadence/max_nudges).
- Read-model: overdue → escalated transition surfaced via followup_status.
"""

import pytest

from bridge.adapters.local.scheduler import LocalScheduler
from bridge.adapters.local.skill_registry import LocalSkillRegistry
from bridge.scheduler import (
    FollowupState,
    SlaPolicy,
    Timer,
    TimerKind,
    VirtualClock,
    followup_status,
    plan_followups,
)

# --- VirtualClock tests ---


def test_virtual_clock_starts_at_zero():
    """VirtualClock starts at tick 0 by default."""
    clock = VirtualClock()
    assert clock.now() == 0


def test_virtual_clock_honors_start():
    """VirtualClock starts at a custom tick when specified."""
    clock = VirtualClock(start=10)
    assert clock.now() == 10


def test_virtual_clock_advance():
    """VirtualClock.advance() increments the tick and returns the new value."""
    clock = VirtualClock()
    assert clock.advance() == 1
    assert clock.now() == 1
    assert clock.advance(5) == 6
    assert clock.now() == 6


def test_virtual_clock_advance_negative_raises():
    """VirtualClock.advance() raises ValueError on negative ticks."""
    clock = VirtualClock()
    with pytest.raises(ValueError, match="negative ticks"):
        clock.advance(-1)


# --- plan_followups tests (SLA engine) ---


def test_plan_followups_address_policy():
    """plan_followups derives the correct SLA ladder from the address policy (C1).

    Address policy: deadline=3, cadence=2, max_nudges=2
    Expected: nudge#1@3, nudge#2@5, escalation@7
    """
    sla = SlaPolicy(deadline=3, cadence=2, max_nudges=2)
    timers = plan_followups(sla, start=0, context_id="ctx-1")

    assert len(timers) == 3
    # Nudge #1
    assert timers[0].id == "ctx-1-nudge-1"
    assert timers[0].context_id == "ctx-1"
    assert timers[0].fire_at == 3
    assert timers[0].kind == TimerKind.NUDGE
    assert timers[0].sequence == 1
    assert not timers[0].fired

    # Nudge #2
    assert timers[1].id == "ctx-1-nudge-2"
    assert timers[1].fire_at == 5
    assert timers[1].kind == TimerKind.NUDGE
    assert timers[1].sequence == 2

    # Escalation
    assert timers[2].id == "ctx-1-escalation"
    assert timers[2].fire_at == 7
    assert timers[2].kind == TimerKind.ESCALATION
    assert timers[2].sequence == 0


def test_plan_followups_custom_id_prefix():
    """plan_followups uses a custom id_prefix when specified."""
    sla = SlaPolicy(deadline=3, cadence=2, max_nudges=2)
    timers = plan_followups(sla, start=0, context_id="ctx-1", id_prefix="custom-prefix")

    assert timers[0].id == "custom-prefix-nudge-1"
    assert timers[1].id == "custom-prefix-nudge-2"
    assert timers[2].id == "custom-prefix-escalation"


def test_plan_followups_with_task_id():
    """plan_followups sets task_id on all timers when specified."""
    sla = SlaPolicy(deadline=3, cadence=2, max_nudges=2)
    timers = plan_followups(sla, start=0, context_id="ctx-1", task_id="task-1")

    for timer in timers:
        assert timer.task_id == "task-1"


# --- LocalScheduler seam tests ---


@pytest.mark.seam("scheduler")
@pytest.mark.anyio
async def test_scheduler_due_returns_only_due_timers():
    """due(now) returns only timers with fire_at <= now, sorted deterministically."""
    scheduler = LocalScheduler()
    sla = SlaPolicy(deadline=3, cadence=2, max_nudges=2)
    timers = plan_followups(sla, start=0, context_id="ctx-1")
    for timer in timers:
        await scheduler.schedule(timer)

    # At tick 5, nudge#1 and nudge#2 are due (fire_at 3 and 5), but not escalation (7)
    due = await scheduler.due(now=5)
    assert len(due) == 2
    assert due[0].id == "ctx-1-nudge-1"
    assert due[1].id == "ctx-1-nudge-2"

    # Escalation not in the returned list
    assert not any(t.id == "ctx-1-escalation" for t in due)


@pytest.mark.seam("scheduler")
@pytest.mark.anyio
async def test_scheduler_due_deterministic_sort():
    """due() sorts by (fire_at, sequence, id) when multiple timers share a fire_at."""
    scheduler = LocalScheduler()

    # Create two timers with the same fire_at but different sequences
    timer_a = Timer(id="z-timer", context_id="ctx", fire_at=10, kind=TimerKind.NUDGE, sequence=2)
    timer_b = Timer(id="a-timer", context_id="ctx", fire_at=10, kind=TimerKind.NUDGE, sequence=1)
    await scheduler.schedule(timer_a)
    await scheduler.schedule(timer_b)

    due = await scheduler.due(now=10)
    # Sorted by (fire_at, sequence, id): both at fire_at=10, sequence 1 < 2
    assert len(due) == 2
    assert due[0].id == "a-timer"  # sequence=1
    assert due[1].id == "z-timer"  # sequence=2


@pytest.mark.seam("scheduler")
@pytest.mark.anyio
async def test_scheduler_exactly_once_a7():
    """A7 load-bearing: due(now) marks timers fired, NEVER re-returns them.

    This is THE test the no-duplicate guarantee rides on.
    """
    scheduler = LocalScheduler()
    sla = SlaPolicy(deadline=3, cadence=2, max_nudges=2)
    timers = plan_followups(sla, start=0, context_id="ctx-1")
    for timer in timers:
        await scheduler.schedule(timer)

    # First call at tick 7: all 3 timers fire
    due1 = await scheduler.due(now=7)
    assert len(due1) == 3
    assert all(t.fired for t in due1)  # Each returned timer is marked fired

    # Second call at the same tick: MUST return empty
    due2 = await scheduler.due(now=7)
    assert len(due2) == 0, "Fired timers re-appeared (A7 violated)"

    # Advance the clock further: still empty
    scheduler.clock.advance(10)
    due3 = await scheduler.due()
    assert len(due3) == 0


@pytest.mark.seam("scheduler")
@pytest.mark.anyio
async def test_scheduler_cancel():
    """A cancelled timer never appears in due(), even past its fire_at."""
    scheduler = LocalScheduler()
    timer = Timer(id="cancel-me", context_id="ctx", fire_at=5, kind=TimerKind.NUDGE, sequence=1)
    await scheduler.schedule(timer)
    await scheduler.cancel("cancel-me")

    # Even at tick 10, the cancelled timer does not appear
    due = await scheduler.due(now=10)
    assert len(due) == 0


@pytest.mark.seam("scheduler")
@pytest.mark.anyio
async def test_scheduler_schedule_idempotency():
    """Scheduling the same timer.id twice keeps one entry (upsert)."""
    scheduler = LocalScheduler()
    timer1 = Timer(id="same-id", context_id="ctx", fire_at=5, kind=TimerKind.NUDGE, sequence=1)
    timer2 = Timer(id="same-id", context_id="ctx", fire_at=10, kind=TimerKind.NUDGE, sequence=2)
    await scheduler.schedule(timer1)
    await scheduler.schedule(timer2)

    # Only the second timer (fire_at=10) should be scheduled
    due = await scheduler.due(now=10)
    assert len(due) == 1
    assert due[0].fire_at == 10
    assert due[0].sequence == 2


# --- followup_status read-model tests ---


def test_followup_status_on_track():
    """followup_status returns ON_TRACK when no timers have fired."""
    timers = [
        Timer(
            id="t1",
            context_id="ctx",
            fire_at=10,
            kind=TimerKind.NUDGE,
            sequence=1,
            fired=False,
        ),
        Timer(
            id="t2",
            context_id="ctx",
            fire_at=20,
            kind=TimerKind.ESCALATION,
            sequence=0,
            fired=False,
        ),
    ]
    status = followup_status(timers, context_id="ctx")
    assert status.state == FollowupState.ON_TRACK
    assert status.nudges_fired == 0
    assert not status.escalated


def test_followup_status_overdue():
    """followup_status returns OVERDUE when ≥1 nudge fired, not yet escalated."""
    timers = [
        Timer(
            id="t1",
            context_id="ctx",
            fire_at=10,
            kind=TimerKind.NUDGE,
            sequence=1,
            fired=True,
        ),
        Timer(
            id="t2",
            context_id="ctx",
            fire_at=20,
            kind=TimerKind.ESCALATION,
            sequence=0,
            fired=False,
        ),
    ]
    status = followup_status(timers, context_id="ctx")
    assert status.state == FollowupState.OVERDUE
    assert status.nudges_fired == 1
    assert not status.escalated


def test_followup_status_escalated():
    """followup_status returns ESCALATED when the escalation timer fired."""
    timers = [
        Timer(
            id="t1",
            context_id="ctx",
            fire_at=10,
            kind=TimerKind.NUDGE,
            sequence=1,
            fired=True,
        ),
        Timer(
            id="t2",
            context_id="ctx",
            fire_at=20,
            kind=TimerKind.ESCALATION,
            sequence=0,
            fired=True,
        ),
    ]
    status = followup_status(timers, context_id="ctx")
    assert status.state == FollowupState.ESCALATED
    assert status.nudges_fired == 1
    assert status.escalated


# --- End-to-end demo beat (ties M1.3) ---


@pytest.mark.seam("scheduler")
@pytest.mark.anyio
async def test_end_to_end_sla_progression():
    """End-to-end: load address policy, step virtual clock, observe overdue → escalated.

    Ties M1.3 (skill policy) to M1.12 (scheduler). Asserts the SLA engine reads from
    the skill policy and the read-model surfaces overdue → escalated (no outbound send).
    """
    # Load the real address-proof skill
    registry = LocalSkillRegistry()
    skill = await registry.get_skill("address-proof")
    assert skill is not None
    assert skill.policy is not None
    assert skill.policy.sla is not None
    sla = skill.policy.sla

    # Schedule followups
    scheduler = LocalScheduler()
    await scheduler.schedule_followups(sla, context_id="ctx-demo", start=0)

    # Tick 2: ON_TRACK (nothing fired yet)
    scheduler.clock.advance(2)
    await scheduler.due()
    status = scheduler.followups_for("ctx-demo")
    assert status.state == FollowupState.ON_TRACK

    # Tick 3: nudge#1 fires → OVERDUE
    scheduler.clock.advance(1)
    due = await scheduler.due()
    assert len(due) == 1
    assert due[0].kind == TimerKind.NUDGE
    status = scheduler.followups_for("ctx-demo")
    assert status.state == FollowupState.OVERDUE
    assert status.nudges_fired == 1

    # Tick 5: nudge#2 fires → still OVERDUE
    scheduler.clock.advance(2)
    due = await scheduler.due()
    assert len(due) == 1
    status = scheduler.followups_for("ctx-demo")
    assert status.state == FollowupState.OVERDUE
    assert status.nudges_fired == 2

    # Tick 7: escalation fires → ESCALATED
    scheduler.clock.advance(2)
    due = await scheduler.due()
    assert len(due) == 1
    assert due[0].kind == TimerKind.ESCALATION
    status = scheduler.followups_for("ctx-demo")
    assert status.state == FollowupState.ESCALATED
    assert status.escalated
