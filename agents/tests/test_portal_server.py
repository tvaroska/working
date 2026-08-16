"""Frontend-v1 — Provider Portal BFF tests (A2UI Path-B wrapper).

Asserts the three canonical dispositions travel through ``POST /portal/intake``
(auto-approve / resubmit / rejected), that the refreshed screen reflects the
classified ledger, and that ``GET /portal/screen`` round-trips a declarative
``A2uiScreen`` (content-not-pixels, M1.10).
"""

from starlette.testclient import TestClient

from agents.address.portal_server import create_app


def _intake(client: TestClient, context: str, fixture_id: str) -> dict:
    resp = client.post(
        "/portal/intake",
        json={"context": context, "mode": "upload", "fixture_id": fixture_id},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_gov_id_clean_auto_approves():
    client = TestClient(create_app())
    body = _intake(client, "ctx-gov", "gov-id-clean")
    fulfillment = body["fulfillment"]
    assert fulfillment["phase"] == "auto_approve"
    assert fulfillment["disposition"] == "accepted"
    assert fulfillment["terminal"] is True
    # The refreshed screen shows the requirement satisfied -> no intake affordance.
    assert body["screen"]["status"]["done"] is True
    assert body["screen"]["intake"] is None


def test_blurry_bill_requests_resubmit():
    client = TestClient(create_app())
    body = _intake(client, "ctx-blur", "bill-aquautil-blurry")
    fulfillment = body["fulfillment"]
    assert fulfillment["phase"] == "resubmit"
    assert fulfillment["disposition"] == "rejected"
    assert fulfillment["awaiting_resubmission"] is True
    # Still outstanding: the screen keeps an intake affordance for a fresh upload.
    assert body["screen"]["status"]["done"] is False
    assert body["screen"]["intake"] is not None


def test_unsupported_doctype_rejected():
    client = TestClient(create_app())
    body = _intake(client, "ctx-pass", "passport-unsupported")
    fulfillment = body["fulfillment"]
    assert fulfillment["phase"] == "unsupported"
    assert fulfillment["disposition"] == "rejected"
    assert fulfillment["terminal"] is True


def test_screen_round_trips_a2ui_shape():
    client = TestClient(create_app())
    resp = client.get("/portal/screen?context=ctx-fresh")
    assert resp.status_code == 200
    screen = resp.json()

    # A2uiScreen: status view + (optional) intake spec — content, not pixels.
    assert set(screen.keys()) == {"status", "intake"}
    status = screen["status"]
    assert set(status.keys()) == {"sent", "accepted", "outstanding", "next", "done"}
    assert status["sent"] == []  # a fresh context has an empty ledger
    assert status["done"] is False

    # The intake spec declares affordances (a file input), not layout.
    intake = screen["intake"]
    assert intake is not None
    inputs = {field["input"] for field in intake["accepts"]}
    assert "file" in inputs


def test_intake_reflected_in_subsequent_screen():
    client = TestClient(create_app())
    _intake(client, "ctx-thread", "gov-id-clean")
    screen = client.get("/portal/screen?context=ctx-thread").json()
    sent_ids = {doc["id"] for doc in screen["status"]["sent"]}
    assert "gov-id-clean" in sent_ids
    assert screen["status"]["done"] is True


def test_missing_fixture_id_400():
    client = TestClient(create_app())
    resp = client.post("/portal/intake", json={"context": "ctx-x", "mode": "upload"})
    assert resp.status_code == 400
