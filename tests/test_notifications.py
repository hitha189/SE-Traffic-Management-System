from helpers import make_client, login, report


def subscribe(client, headers, areas):
    return client.put("/api/subscriptions", headers=headers,
                      json={"areas": areas})


def inbox(client, headers):
    return client.get("/api/notifications",
                      headers=headers).get_json()["notifications"]


def test_user_can_choose_areas(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    r = subscribe(client, user, ["MG Road", "Majestic"])
    assert r.status_code == 200
    got = client.get("/api/subscriptions", headers=user).get_json()
    assert got["areas"] == ["MG Road", "Majestic"]
    assert "Whitefield" in got["available"]


def test_invalid_areas_rejected(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    assert subscribe(client, user, ["Atlantis"]).status_code == 400
    assert subscribe(client, user, "MG Road").status_code == 400
    assert subscribe(client, user, [5]).status_code == 400


def test_subscriber_is_notified_for_selected_area(tmp_path):
    client = make_client(tmp_path)
    alice = login(client, "alice")
    reporter = login(client, "bob")
    subscribe(client, alice, ["MG Road"])
    report(client, reporter, "Accident", "MG Road", "Crash")
    items = inbox(client, alice)
    assert len(items) == 1
    assert "MG Road" in items[0]["message"] and items[0]["is_read"] == 0


def test_subscriber_is_notified_for_nearby_area(tmp_path):
    client = make_client(tmp_path)
    alice = login(client, "alice")
    reporter = login(client, "bob")
    subscribe(client, alice, ["Majestic"])  # MG Road is next to Majestic
    report(client, reporter, "Accident", "MG Road", "Crash")
    assert len(inbox(client, alice)) == 1


def test_unrelated_user_is_not_notified(tmp_path):
    client = make_client(tmp_path)
    far = login(client, "farAway")
    nobody = login(client, "nobody")
    reporter = login(client, "bob")
    subscribe(client, far, ["Whitefield"])  # not next to Majestic
    report(client, reporter, "Accident", "Majestic", "Crash")
    assert inbox(client, far) == []
    assert inbox(client, nobody) == []


def test_other_incident_does_not_notify(tmp_path):
    client = make_client(tmp_path)
    alice = login(client, "alice")
    subscribe(client, alice, ["MG Road"])
    report(client, alice, "Other", "MG Road", "Stray dog")
    assert inbox(client, alice) == []


def test_mark_read_and_ownership(tmp_path):
    client = make_client(tmp_path)
    alice = login(client, "alice")
    mallory = login(client, "mallory")
    subscribe(client, alice, ["MG Road"])
    report(client, alice, "Accident", "MG Road", "Crash")
    nid = inbox(client, alice)[0]["id"]
    assert client.post("/api/notifications/%d/read" % nid,
                       headers=mallory).status_code == 404
    assert inbox(client, alice)[0]["is_read"] == 0
    assert client.post("/api/notifications/%d/read" % nid,
                       headers=alice).status_code == 200
    assert inbox(client, alice)[0]["is_read"] == 1


def test_notifications_require_login(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/notifications").status_code == 401
    assert client.get("/api/subscriptions").status_code == 401
