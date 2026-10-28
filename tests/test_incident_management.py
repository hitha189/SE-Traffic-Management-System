from helpers import make_client, login, report, audit_entries


def setup(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    user = login(client, "alice")
    iid = report(client, user).get_json()["id"]
    return client, admin, user, iid


def test_admin_can_verify_incident(tmp_path):
    client, admin, _user, iid = setup(tmp_path)
    r = client.patch("/api/incidents/%d" % iid, headers=admin,
                     json={"action": "verify"})
    assert r.status_code == 200
    assert r.get_json()["incident"]["status"] == "Verified"


def test_admin_can_update_incident(tmp_path):
    client, admin, _user, iid = setup(tmp_path)
    r = client.patch("/api/incidents/%d" % iid, headers=admin, json={
        "action": "update", "type": "Roadblock",
        "description": "Lane fully blocked"})
    inc = r.get_json()["incident"]
    assert r.status_code == 200
    assert inc["type"] == "Roadblock"
    assert inc["description"] == "Lane fully blocked"
    assert inc["location"] == "MG Road"


def test_admin_can_close_incident(tmp_path):
    client, admin, _user, iid = setup(tmp_path)
    r = client.patch("/api/incidents/%d" % iid, headers=admin,
                     json={"action": "close", "note": "Cleared by police"})
    assert r.status_code == 200
    assert r.get_json()["incident"]["status"] == "Closed"


def test_closed_incident_cannot_change(tmp_path):
    client, admin, _user, iid = setup(tmp_path)
    client.patch("/api/incidents/%d" % iid, headers=admin,
                 json={"action": "close"})
    for body in ({"action": "verify"}, {"action": "close"},
                 {"action": "update", "description": "x"}):
        r = client.patch("/api/incidents/%d" % iid, headers=admin, json=body)
        assert r.status_code == 409


def test_cannot_verify_twice(tmp_path):
    client, admin, _user, iid = setup(tmp_path)
    client.patch("/api/incidents/%d" % iid, headers=admin,
                 json={"action": "verify"})
    r = client.patch("/api/incidents/%d" % iid, headers=admin,
                     json={"action": "verify"})
    assert r.status_code == 409


def test_normal_user_cannot_manage_incidents(tmp_path):
    client, _admin, user, iid = setup(tmp_path)
    r = client.patch("/api/incidents/%d" % iid, headers=user,
                     json={"action": "close"})
    assert r.status_code == 403
    listed = client.get("/api/incidents", headers=user).get_json()
    assert listed["incidents"][0]["status"] == "Reported"


def test_invalid_requests(tmp_path):
    client, admin, _user, iid = setup(tmp_path)
    url = "/api/incidents/%d" % iid
    assert client.patch(url, headers=admin,
                        json={"action": "delete"}).status_code == 400
    assert client.patch(url, headers=admin,
                        json={"action": "update"}).status_code == 400
    assert client.patch(url, headers=admin, json={
        "action": "update", "type": "Alien"}).status_code == 400
    assert client.patch(url, headers=admin, json={
        "action": "update", "location": ""}).status_code == 400
    assert client.patch("/api/incidents/999", headers=admin,
                        json={"action": "verify"}).status_code == 404
    listed = client.get("/api/incidents", headers=admin).get_json()
    assert listed["incidents"][0]["type"] == "Accident"


def test_updates_are_logged(tmp_path):
    client, admin, _user, iid = setup(tmp_path)
    client.patch("/api/incidents/%d" % iid, headers=admin,
                 json={"action": "verify"})
    client.patch("/api/incidents/%d" % iid, headers=admin, json={
        "action": "update", "description": "Now only one lane"})
    client.patch("/api/incidents/%d" % iid, headers=admin,
                 json={"action": "close"})
    actions = [e["action"] for e in audit_entries(client, admin)]
    for expected in ("incident_reported", "incident_verified",
                     "incident_updated", "incident_closed"):
        assert expected in actions
