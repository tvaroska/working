"""Frontend-v1 — Time-warp control BFF tests.

Asserts that ``POST /timewarp/advance`` fires the SLA ladder timers **exactly once**
(A7) and moves the chasing exchange ``overdue → escalated``, that ``reset`` restores
the seed, and that the server holds **no background task** (B4) — the clock only
moves on an explicit request.
"""

from starlette.testclient import TestClient

from agents.address._world import CHASING_EXCHANGE, DemoWorld
from agents.address.timewarp_server import create_app


def test_state_reports_sla_and_timers():
    client = TestClient(create_app())
    state = client.get("/timewarp/state").json()

    assert state["now"] == 0
    assert state["sla"] == {"deadline": 3, "cadence": 2, "max_nudges": 2}
    # The full SLA ladder is scheduled (2 nudges + escalation) and unfired at tick 0.
    assert len(state["timers"]) == 3
    assert all(not t["fired"] for t in state["timers"])
    assert state["followup"]["state"] == "on_track"


def test_advance_fires_ladder_exactly_once_and_escalates():
    world = DemoWorld()
    client = TestClient(create_app(world=world))

    # Advance past the escalation tick (deadline 3 / cadence 2 -> escalation @ tick 7).
    resp = client.post("/timewarp/advance", json={"ticks": 7})
    body = resp.json()
    assert resp.status_code == 200
    fired_ids = set(body["fired"])
    assert fired_ids == {
        f"{CHASING_EXCHANGE}-nudge-1",
        f"{CHASING_EXCHANGE}-nudge-2",
        f"{CHASING_EXCHANGE}-escalation",
    }
    assert body["state"]["followup"]["state"] == "escalated"
    assert body["state"]["followup"]["escalated"] is True

    # Exactly-once (A7): advancing again fires nothing (timers marked fired in place).
    again = client.post("/timewarp/advance", json={"ticks": 0}).json()
    assert again["fired"] == []
    assert all(t["fired"] for t in again["state"]["timers"])


def test_step_advances_one_tick():
    world = DemoWorld()
    client = TestClient(create_app(world=world))
    client.post("/timewarp/step")
    client.post("/timewarp/step")
    assert client.get("/timewarp/state").json()["now"] == 2


def test_reset_restores_seed():
    client = TestClient(create_app())
    client.post("/timewarp/advance", json={"ticks": 7})
    assert client.get("/timewarp/state").json()["now"] == 7

    resp = client.post("/timewarp/reset")
    state = resp.json()["state"]
    assert state["now"] == 0
    assert state["followup"]["state"] == "on_track"
    assert all(not t["fired"] for t in state["timers"])


def test_negative_ticks_rejected():
    client = TestClient(create_app())
    assert client.post("/timewarp/advance", json={"ticks": -1}).status_code == 400


def test_no_background_task_clock_is_manual():
    """B4: no SSE / no background timer — the clock only moves on explicit request."""
    world = DemoWorld()
    client = TestClient(create_app(world=world))
    # Building the app + repeated reads must never advance the clock on their own.
    assert world.now() == 0
    for _ in range(3):
        assert client.get("/timewarp/state").json()["now"] == 0
    # There is no SSE endpoint on this surface (B4).
    assert client.get("/timewarp/stream").status_code == 404
