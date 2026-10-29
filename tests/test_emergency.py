import routing
from helpers import make_client, login, report, audit_entries


def priority(client, headers, **overrides):
    body = {"vehicle_id": "AMB-101", "source": "Majestic",
            "destination": "Whitefield"}
    body.update(overrides)
    return client.post("/api/emergency/priority", headers=headers, json=body)


def signal_states(client, admin):
    items = client.get("/api/signals", headers=admin).get_json()["signals"]
    return {s["location"]: s["state"] for s in items}


# ---- FR-14 Emergency priority ------------------------------------------------
def test_emergency_vehicle_can_request_priority(tmp_path):
    client = make_client(tmp_path)
    amb = login(client, "amb1", "emergency")
    r = priority(client, amb)
    assert r.status_code == 201
    data = r.get_json()
    assert data["request_id"] >= 1
    assert data["route"]["path"][0] == "Majestic"
    assert data["route"]["path"][-1] == "Whitefield"


def test_unauthorized_users_cannot_request_priority(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    admin = login(client, "boss", "admin")
    assert client.post("/api/emergency/priority", json={}).status_code == 401
    assert priority(client, user).status_code == 403
    assert priority(client, admin).status_code == 403
    assert client.get("/api/emergency/requests",
                      headers=user).status_code == 403


def test_priority_rejects_bad_input(tmp_path):
    client = make_client(tmp_path)
    amb = login(client, "amb1", "emergency")
    assert priority(client, amb, vehicle_id="x").status_code == 400
    assert priority(client, amb, vehicle_id=12345).status_code == 400
    assert priority(client, amb, vehicle_id="AMB 1; DROP").status_code == 400
    assert priority(client, amb, source="Atlantis").status_code == 400
    assert priority(client, amb, destination="Majestic").status_code == 400


def test_priority_turns_route_signals_green_and_logs(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    amb = login(client, "amb1", "emergency")
    data = priority(client, amb).get_json()
    states = signal_states(client, admin)
    for place in data["route"]["path"]:
        assert states[place] == "Green"
    actions = [e["action"] for e in audit_entries(client, admin)]
    assert "emergency_priority_request" in actions
    assert actions.count("signal_change") == len(data["signals_cleared"])


def test_completing_request_restores_signals(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    amb = login(client, "amb1", "emergency")
    before = signal_states(client, admin)
    rid = priority(client, amb).get_json()["request_id"]
    r = client.post("/api/emergency/requests/%d/complete" % rid, headers=amb)
    assert r.status_code == 200
    assert signal_states(client, admin) == before
    again = client.post("/api/emergency/requests/%d/complete" % rid,
                        headers=amb)
    assert again.status_code == 409


def test_only_owner_or_admin_can_complete(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    amb1 = login(client, "amb1", "emergency")
    amb2 = login(client, "amb2", "emergency")
    rid = priority(client, amb1).get_json()["request_id"]
    url = "/api/emergency/requests/%d/complete" % rid
    assert client.post(url, headers=amb2).status_code == 403
    assert client.post(url, headers=admin).status_code == 200
    assert client.post("/api/emergency/requests/999/complete",
                       headers=admin).status_code == 404


def test_request_lists_are_scoped(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    amb1 = login(client, "amb1", "emergency")
    amb2 = login(client, "amb2", "emergency")
    priority(client, amb1)
    priority(client, amb2, vehicle_id="AMB-202")
    own = client.get("/api/emergency/requests", headers=amb1).get_json()
    everyone = client.get("/api/emergency/requests", headers=admin).get_json()
    assert len(own["requests"]) == 1
    assert len(everyone["requests"]) == 2
    assert "previous_states" not in everyone["requests"][0]


# ---- FR-15 Emergency route -----------------------------------------------------
def test_emergency_route_is_faster_than_normal_route():
    density = {"MG Road": 80, "Indiranagar": 80, "Majestic": 80,
               "Whitefield": 80, "Koramangala": 80, "Silk Board": 80}
    emergency = routing.find_emergency_route("Majestic", "Whitefield", density)
    normal = routing.find_route("Majestic", "Whitefield", density)
    assert emergency["emergency"] is True
    assert emergency["eta_minutes"] < normal["eta_minutes"]
    assert emergency["normal_eta_minutes"] == normal["eta_minutes"]


def test_emergency_route_uses_traffic_data():
    quiet = routing.find_emergency_route("Majestic", "Whitefield", {})
    heavy = routing.find_emergency_route(
        "Majestic", "Whitefield",
        {p: 100 for p in routing.known_places()})
    assert heavy["eta_minutes"] > quiet["eta_minutes"]


def test_emergency_route_avoids_roadblock_when_it_can(tmp_path):
    client = make_client(tmp_path)
    amb = login(client, "amb1", "emergency")
    user = login(client, "alice")
    report(client, user, "Roadblock", "Koramangala", "Road closed")
    r = client.get("/api/emergency/route", headers=amb, query_string={
        "source": "Majestic", "destination": "Silk Board"})
    route = r.get_json()
    assert r.status_code == 200
    assert "Koramangala" not in route["path"]
    assert route["avoided"] == ["Koramangala"]


def test_emergency_route_falls_back_when_roadblock_is_unavoidable():
    route = routing.find_emergency_route(
        "Majestic", "Silk Board", {},
        blocked={"Koramangala", "Whitefield"})
    assert route is not None
    assert route["path"][-1] == "Silk Board"


def test_emergency_route_access_and_validation(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    amb = login(client, "amb1", "emergency")
    admin = login(client, "boss", "admin")
    q = {"source": "Majestic", "destination": "Whitefield"}
    assert client.get("/api/emergency/route",
                      query_string=q).status_code == 401
    assert client.get("/api/emergency/route", headers=user,
                      query_string=q).status_code == 403
    assert client.get("/api/emergency/route", headers=amb,
                      query_string=q).status_code == 200
    assert client.get("/api/emergency/route", headers=admin,
                      query_string=q).status_code == 200
    assert client.get("/api/emergency/route", headers=amb, query_string={
        "source": "Nowhere", "destination": "Whitefield"}).status_code == 400
    assert client.get("/api/emergency/route",
                      headers=amb).status_code == 400
