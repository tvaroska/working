"""Frontend-v1 — Servicer Ops Dashboard BFF tests.

Asserts the read-model buckets (exchanges / HITL / escalation), that a HITL item
resolves via ``POST /ops/hitl/{doc_id}/{action}``, and that an exchange surfaces on
the escalation queue once the shared clock passes the SLA deadline (driven through a
shared :class:`DemoWorld`, the same instance ``timewarp_server`` advances).
"""

import json

from starlette.testclient import TestClient

from agents.address._world import CHASING_EXCHANGE, HITL_EXCHANGE, DemoWorld
from agents.address.ops_server import create_app


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    frames: list[tuple[str, dict]] = []
    for block in text.strip().split("\n\n"):
        event = data = None
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line[len("event: ") :]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: ") :])
        if event is not None:
            frames.append((event, data))
    return frames


def test_state_read_model_buckets():
    client = TestClient(create_app())
    snapshot = client.get("/ops/state").json()

    assert snapshot["now"] == 0
    ids = {e["id"] for e in snapshot["exchanges"]}
    assert {CHASING_EXCHANGE, HITL_EXCHANGE} <= ids

    # The expired gov-id sits PENDING in the HITL queue.
    hitl_ids = {h["doc_id"] for h in snapshot["hitl_queue"]}
    assert "gov-id-expired" in hitl_ids

    # Nothing escalated at tick 0.
    assert snapshot["escalation_queue"] == []


def test_hitl_approve_resolves_item():
    client = TestClient(create_app())

    resp = client.post("/ops/hitl/gov-id-expired/approve")
    assert resp.status_code == 200
    state = resp.json()["state"]
    assert all(h["doc_id"] != "gov-id-expired" for h in state["hitl_queue"])

    # Idempotency guard: resolving again 404s (no longer pending).
    assert client.post("/ops/hitl/gov-id-expired/approve").status_code == 404


def test_hitl_unknown_action_400():
    client = TestClient(create_app())
    assert client.post("/ops/hitl/gov-id-expired/frobnicate").status_code == 400


def test_escalation_surfaces_after_deadline():
    world = DemoWorld()  # shared world (as timewarp would pass in)
    client = TestClient(create_app(world=world))

    # Before the deadline: on-track, nothing escalated.
    assert client.get("/ops/state").json()["escalation_queue"] == []

    # Advance the shared clock past the escalation tick (deadline 3, cadence 2 -> tick 7).
    import asyncio

    asyncio.run(world.advance(7))

    snapshot = client.get("/ops/state").json()
    escalated = {e["exchange_id"]: e for e in snapshot["escalation_queue"]}
    assert CHASING_EXCHANGE in escalated
    assert escalated[CHASING_EXCHANGE]["escalated"] is True
    assert escalated[CHASING_EXCHANGE]["state"] == "escalated"


def test_stream_emits_snapshot_and_terminal_done():
    world = DemoWorld()
    import asyncio

    asyncio.run(world.advance(7))
    client = TestClient(create_app(world=world))

    resp = client.get("/ops/stream")
    assert resp.status_code == 200
    frames = _parse_sse(resp.text)
    events = [name for name, _ in frames]

    assert events[0] == "snapshot"
    assert events[-1] == "done"  # terminal close discipline (B2)
    # The escalated exchange rides on an event frame.
    escalation_events = [d for n, d in frames if n == "event"]
    assert any(d["exchange_id"] == CHASING_EXCHANGE for d in escalation_events)
