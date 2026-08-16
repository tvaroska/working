"""Frontend-v1 — Processing-Agent Console BFF tests.

Drives the console ``create_app`` SSE endpoint with an ASGI test client and asserts
the **sense-B** beat: the distinct-issuer scenario streams a turn where
``satisfaction.done is False`` with two bills from the *same* canonical issuer
rejected (one more outstanding), then ``done`` after a distinct second issuer. Also
asserts a terminal ``done`` event closes the stream (lessons B2).
"""

import json

from starlette.testclient import TestClient

from agents.address.console_server import build_console_turns, create_app


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    """Parse a finite ``text/event-stream`` body into ``(event, data)`` frames."""
    frames: list[tuple[str, dict]] = []
    for block in text.strip().split("\n\n"):
        event = None
        data = None
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line[len("event: ") :]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: ") :])
        if event is not None:
            frames.append((event, data))
    return frames


def test_scenarios_lists_sense_b():
    client = TestClient(create_app())
    resp = client.get("/console/scenarios")
    assert resp.status_code == 200
    ids = {s["id"] for s in resp.json()["scenarios"]}
    assert "sense-b" in ids
    assert "distinct-issuers" in ids


def test_health():
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok"}


def test_stream_shows_sense_b_reject_then_done():
    client = TestClient(create_app())
    resp = client.get("/console/stream?scenario=sense-b")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    frames = _parse_sse(resp.text)
    events = [name for name, _ in frames]

    # snapshot first, terminal done last (B2 close discipline).
    assert events[0] == "snapshot"
    assert events[-1] == "done"

    turns = [data for name, data in frames if name == "turn"]
    assert len(turns) == 3

    # Round 2: two bills from the SAME issuer (power-co) -> not done, still outstanding.
    round2 = turns[1]
    assert round2["satisfaction"]["done"] is False
    assert round2["satisfaction"]["accepted_issuers"] == ["power-co"]
    assert "utility-bill" in round2["satisfaction"]["outstanding"]
    assert len(round2["ledger_handed"]) == 2  # two same-issuer bills handed
    assert "power-co" in round2["reasoning"]  # sense-B reasoning is legible

    # Round 3: a distinct second issuer -> done.
    round3 = turns[2]
    assert round3["satisfaction"]["done"] is True
    assert set(round3["satisfaction"]["accepted_issuers"]) == {"power-co", "aqua-util"}
    assert round3["terminal"] is True
    assert round3["requirements"][0]["status"] == "satisfied"

    # The terminal done frame reports the outcome.
    assert frames[-1][1]["outcome"] == "done"


def test_gov_id_scenario_is_instant():
    turns = build_console_turns("gov-id-instant")
    assert len(turns) == 1
    assert turns[0]["satisfaction"]["done"] is True
    assert turns[0]["terminal"] is True


def test_unknown_scenario_404():
    client = TestClient(create_app())
    assert client.get("/console/stream?scenario=nope").status_code == 404
