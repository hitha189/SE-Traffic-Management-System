import audit
from helpers import make_client, login


def test_wrong_types_in_register_and_login_give_400_not_500(tmp_path):
    client = make_client(tmp_path)
    for body in ({"username": 5, "email": "a@x.com", "password": "Valid@123"},
                 {"username": "bob", "email": ["a@x.com"],
                  "password": "Valid@123"},
                 {"username": "bob", "email": "a@x.com", "password": 123456}):
        assert client.post("/api/register", json=body).status_code == 400
    assert client.post("/api/login", json={
        "username": 1, "password": 2}).status_code == 400


def test_non_object_json_is_rejected_cleanly(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    for payload in ([1, 2, 3], "text", 42, None):
        r = client.post("/api/incidents", headers=user, json=payload)
        assert r.status_code == 400
    r = client.post("/api/incidents", headers=user, data="{not json",
                    content_type="application/json")
    assert r.status_code == 400


def test_incident_field_types_and_lengths(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    for body in ({"type": "Accident", "location": 7, "description": "x"},
                 {"type": ["Accident"], "location": "MG Road",
                  "description": "x"},
                 {"type": "Accident", "location": "L" * 101,
                  "description": "x"},
                 {"type": "Accident", "location": "MG Road",
                  "description": "d" * 501}):
        assert client.post("/api/incidents", headers=user,
                           json=body).status_code == 400
    assert client.get("/api/incidents",
                      headers=user).get_json()["incidents"] == []


def test_errors_are_json_not_html(tmp_path):
    client = make_client(tmp_path)
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404 and r.is_json and "error" in r.get_json()
    r = client.delete("/api/login")
    assert r.status_code == 405 and r.is_json


def test_oversized_request_is_rejected(tmp_path):
    client = make_client(tmp_path)
    r = client.post("/api/login", data="x" * 200_000,
                    content_type="application/json")
    assert r.status_code == 413 and r.is_json


def test_failed_action_leaves_data_unchanged(tmp_path, monkeypatch):
    """If the audit entry cannot be written, the signal change is rolled
    back too, so data is never half-updated (NFR-05, NFR-09)."""
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    sigs = client.get("/api/signals", headers=admin).get_json()["signals"]
    target = sigs[0]
    new = "Red" if target["state"] != "Red" else "Green"

    def broken(*args, **kwargs):
        raise RuntimeError("disk full")
    monkeypatch.setattr(audit, "log_action", broken)

    r = client.put("/api/signals/%d" % target["id"], headers=admin,
                   json={"state": new})
    assert r.status_code == 500
    assert r.is_json and "disk full" not in r.get_data(as_text=True)
    monkeypatch.undo()
    after = client.get("/api/signals", headers=admin).get_json()["signals"]
    assert after[0]["state"] == target["state"]


def test_failed_incident_report_creates_no_orphan_record(tmp_path,
                                                         monkeypatch):
    client = make_client(tmp_path)
    user = login(client, "alice")
    admin = login(client, "boss", "admin")

    def broken(*args, **kwargs):
        raise RuntimeError("boom")
    monkeypatch.setattr(audit, "log_action", broken)
    r = client.post("/api/incidents", headers=user, json={
        "type": "Accident", "location": "MG Road", "description": "Crash"})
    assert r.status_code == 500
    monkeypatch.undo()
    # Incident, alert and audit entry are saved together or not at all.
    incidents = client.get("/api/incidents", headers=admin).get_json()
    alerts = client.get("/api/alerts", headers=admin).get_json()["alerts"]
    entries = client.get("/api/admin/audit", headers=admin).get_json()
    assert incidents["incidents"] == []
    assert alerts == []
    assert entries["entries"] == []
