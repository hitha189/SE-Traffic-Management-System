"""The nine cases from Traffic_Management_System_Test_Plan.pdf, automated.

Each test is named after its Test Plan ID (UT-01 ... ST-03) so the Test Plan
and the reports can point to it. Where the plan's sample data does not exist
in the prototype, the nearest real data is used and the difference is listed
in the updated Test Plan PDF:

- "Junction-01" -> the signal at Majestic (signals are named after junctions)
- "City Hospital" -> Whitefield (destinations must be places on the network)
- "Road closure" -> incident type "Roadblock", which raises a "Closure" alert
"""
import app as tms
from helpers import make_client, login, report, audit_entries


def set_density(road, density, level):
    conn = tms.get_db()
    conn.execute("UPDATE roads SET density = ?, congestion = ? WHERE name = ?",
                 (density, level, road))
    conn.commit()
    conn.close()


def freeze_simulator(monkeypatch):
    """Stop the traffic simulator from overwriting the test's readings."""
    monkeypatch.setattr(tms.datasources, "refresh", lambda conn, kind: None)


# ---- Unit tests --------------------------------------------------------------
def test_ut01_login_with_valid_credentials(tmp_path):
    client = make_client(tmp_path)
    client.post("/api/register", json={
        "username": "valid_user", "email": "valid_user@x.com",
        "password": "Valid@123"})
    r = client.post("/api/login", json={
        "username": "valid_user", "password": "Valid@123"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["message"] == "Login successful"
    assert data["role"] == "user"
    # The token opens the dashboard data.
    headers = {"Authorization": "Bearer " + data["token"]}
    assert client.get("/api/traffic", headers=headers).status_code == 200


def test_ut02_login_rejected_with_invalid_credentials(tmp_path):
    client = make_client(tmp_path)
    client.post("/api/register", json={
        "username": "valid_user", "email": "valid_user@x.com",
        "password": "Valid@123"})
    for username in ("invalid_user", "valid_user"):
        r = client.post("/api/login", json={
            "username": username, "password": "wrong123"})
        assert r.status_code == 401
        assert r.get_json()["error"] == "Invalid credentials"
        assert "token" not in r.get_json()


def test_ut03_valid_incident_report_is_stored(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "valid_user")
    r = report(client, user, "Accident", "MG Road",
               "Two vehicles blocking lane")
    assert r.status_code == 201
    assert r.get_json()["message"] == "Incident reported"
    items = client.get("/api/incidents", headers=user).get_json()["incidents"]
    stored = next(i for i in items if i["id"] == r.get_json()["id"])
    assert stored["type"] == "Accident"
    assert stored["location"] == "MG Road"
    assert stored["description"] == "Two vehicles blocking lane"


# ---- Integration tests -------------------------------------------------------
def test_it01_traffic_data_and_incidents_reach_the_map(tmp_path, monkeypatch):
    client = make_client(tmp_path)
    freeze_simulator(monkeypatch)
    user = login(client, "driver")
    set_density("MG Road", 90, "High")
    report(client, user, "Accident", "MG Road", "Two vehicles blocking lane")

    roads = client.get("/api/traffic", headers=user).get_json()["roads"]
    mg = next(r for r in roads if r["name"] == "MG Road")
    assert mg["congestion"] == "High"
    assert "lat" in mg and "lng" in mg  # needed to draw the map marker

    alerts = client.get("/api/alerts", headers=user).get_json()["alerts"]
    kinds = {(a["kind"], a["location"]) for a in alerts}
    assert ("Accident", "MG Road") in kinds
    assert ("Congestion", "MG Road") in kinds


def test_it02_route_planning_avoids_high_traffic(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "driver")
    url = "/api/route?source=Majestic&destination=Whitefield"
    quiet = client.get(url, headers=user).get_json()
    assert quiet["path"][0] == "Majestic" and quiet["path"][-1] == "Whitefield"

    for road in quiet["path"][1:-1]:  # make the usual route ("Route A") jam
        set_density(road, 100, "High")
    busy = client.get(url, headers=user).get_json()
    assert busy["congestion_aware"] is True
    assert busy["path"] != quiet["path"]
    assert not set(busy["path"][1:-1]) & set(quiet["path"][1:-1])


def test_it03_road_closure_notifies_relevant_users(tmp_path):
    client = make_client(tmp_path)
    near = login(client, "near_user")
    far = login(client, "far_user")
    client.put("/api/subscriptions", headers=near, json={"areas": ["MG Road"]})
    client.put("/api/subscriptions", headers=far,
               json={"areas": ["Silk Board"]})

    reporter = login(client, "reporter")
    assert report(client, reporter, "Roadblock", "MG Road",
                  "Road closed for repairs").status_code == 201

    alerts = client.get("/api/alerts", headers=near).get_json()["alerts"]
    assert any(a["kind"] == "Closure" and a["location"] == "MG Road"
               for a in alerts)
    got = client.get("/api/notifications", headers=near).get_json()
    assert any("MG Road" in n["message"] for n in got["notifications"])
    none = client.get("/api/notifications", headers=far).get_json()
    assert none["notifications"] == []


# ---- System tests ------------------------------------------------------------
def test_st01_end_to_end_monitoring_and_route_planning(tmp_path, monkeypatch):
    client = make_client(tmp_path)
    freeze_simulator(monkeypatch)
    # 1. Login
    user = login(client, "driver")
    # 2. Live map data
    roads = client.get("/api/traffic", headers=user).get_json()["roads"]
    assert {r["name"] for r in roads} >= {"Majestic", "Whitefield"}
    # An accident is reported on the way
    report(client, user, "Accident", "MG Road", "Two vehicles blocking lane")
    # 3-4. Source/destination and route
    r = client.get("/api/route?source=Majestic&destination=Whitefield",
                   headers=user)
    assert r.status_code == 200
    route = r.get_json()
    assert route["path"][0] == "Majestic" and route["path"][-1] == "Whitefield"
    assert route["eta_minutes"] > 0
    # 5. Alerts
    alerts = client.get("/api/alerts", headers=user).get_json()["alerts"]
    assert any(a["kind"] == "Accident" for a in alerts)
    # The trip is saved in the user's history
    history = client.get("/api/routes/history", headers=user).get_json()
    assert len(history["routes"]) == 1


def test_st02_admin_signal_change_is_authorised_stored_and_audited(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "admin1", "admin")
    driver = login(client, "driver")
    signals = client.get("/api/signals", headers=admin).get_json()["signals"]
    junction = next(s for s in signals if s["location"] == "Majestic")
    url = "/api/signals/%d" % junction["id"]

    # Start from RED, as in the plan's "Old" value. Setting a signal to the
    # state it already has is refused, so only change it if needed.
    if junction["state"] != "Red":
        assert client.put(url, headers=admin,
                          json={"state": "Red"}).status_code == 200
    assert client.put(url, headers=admin,
                      json={"state": "Red"}).status_code == 400
    # A non-admin is refused; an invalid state is rejected.
    assert client.put(url, headers=driver,
                      json={"state": "Green"}).status_code == 403
    assert client.put(url, headers=admin,
                      json={"state": "Blue"}).status_code == 400
    # RED -> GREEN by the admin.
    r = client.put(url, headers=admin, json={"state": "Green"})
    assert r.status_code == 200
    assert r.get_json()["signal"]["state"] == "Green"
    after = client.get("/api/signals", headers=admin).get_json()["signals"]
    assert next(s for s in after if s["id"] == junction["id"])["state"] \
        == "Green"
    log = audit_entries(client, admin, action="signal_change")
    assert log[0]["actor"] == "admin1"
    assert "Green" in log[0]["details"]


def test_st03_emergency_priority_and_optimised_route(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "admin1", "admin")
    amb = login(client, "ambulance1", "emergency")
    set_density("MG Road", 100, "High")
    set_density("Indiranagar", 100, "High")

    r = client.post("/api/emergency/priority", headers=amb, json={
        "vehicle_id": "Ambulance-01", "source": "Majestic",
        "destination": "Whitefield"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["route"]["path"][-1] == "Whitefield"
    # Optimised: an emergency route that uses the live traffic data and is
    # at least as fast as the normal route.
    assert data["route"]["emergency"] is True
    assert data["route"]["congestion_aware"] is True
    assert data["route"]["eta_minutes"] <= data["route"]["normal_eta_minutes"]
    # Signals on the route are cleared for the vehicle.
    assert data["signals_cleared"]

    mine = client.get("/api/emergency/requests",
                      headers=amb).get_json()["requests"]
    assert mine[0]["vehicle_id"] == "Ambulance-01"
    actions = [e["action"] for e in audit_entries(client, admin)]
    assert "emergency_priority_request" in actions
