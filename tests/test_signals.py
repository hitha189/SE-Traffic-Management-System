from helpers import make_client, login, audit_entries


def signal_id(client, admin, location):
    items = client.get("/api/signals", headers=admin).get_json()["signals"]
    return next(s for s in items if s["location"] == location)


def test_signals_require_login(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/signals").status_code == 401


def test_normal_user_cannot_view_signals(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    assert client.get("/api/signals", headers=user).status_code == 403


def test_admin_can_view_all_signals(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    data = client.get("/api/signals", headers=admin).get_json()
    assert len(data["signals"]) == 6
    assert {s["state"] for s in data["signals"]} <= {"Red", "Yellow", "Green"}
    assert data["states"] == ["Red", "Yellow", "Green"]


def test_admin_can_change_signal_and_it_is_logged(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    sig = signal_id(client, admin, "MG Road")
    new = "Red" if sig["state"] != "Red" else "Green"
    r = client.put("/api/signals/%d" % sig["id"], headers=admin,
                   json={"state": new})
    assert r.status_code == 200
    assert r.get_json()["signal"]["state"] == new
    assert r.get_json()["signal"]["updated_by"] == "boss"
    log = audit_entries(client, admin, action="signal_change")
    assert len(log) == 1
    assert "MG Road" in log[0]["details"] and new in log[0]["details"]


def test_invalid_state_is_rejected_and_not_applied(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    sig = signal_id(client, admin, "MG Road")
    r = client.put("/api/signals/%d" % sig["id"], headers=admin,
                   json={"state": "Purple"})
    assert r.status_code == 400
    assert signal_id(client, admin, "MG Road")["state"] == sig["state"]
    assert audit_entries(client, admin, action="signal_change") == []


def test_unchanged_state_is_rejected(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    sig = signal_id(client, admin, "MG Road")
    r = client.put("/api/signals/%d" % sig["id"], headers=admin,
                   json={"state": sig["state"]})
    assert r.status_code == 400


def test_unknown_signal_is_404(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    r = client.put("/api/signals/999", headers=admin, json={"state": "Red"})
    assert r.status_code == 404


def test_non_admin_cannot_change_signal(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    user = login(client, "alice")
    amb = login(client, "amb1", "emergency")
    sig = signal_id(client, admin, "MG Road")
    for headers in (user, amb):
        r = client.put("/api/signals/%d" % sig["id"], headers=headers,
                       json={"state": "Red"})
        assert r.status_code == 403
    assert signal_id(client, admin, "MG Road")["state"] == sig["state"]


def test_missing_body_is_400(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    sig = signal_id(client, admin, "MG Road")
    r = client.put("/api/signals/%d" % sig["id"], headers=admin)
    assert r.status_code == 400
