import traffic
from helpers import make_client, login, report


def alerts_of(client, headers):
    return client.get("/api/alerts", headers=headers).get_json()["alerts"]


def force_density(monkeypatch, value):
    monkeypatch.setattr(traffic.random, "randint", lambda a, b: value)


def test_alerts_require_login(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/alerts").status_code == 401


def test_accident_creates_alert(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    report(client, user, "Accident", "MG Road", "Crash")
    items = alerts_of(client, user)
    assert len(items) == 1
    assert items[0]["kind"] == "Accident" and items[0]["location"] == "MG Road"


def test_roadblock_is_a_closure_and_hazard_is_a_hazard(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    report(client, user, "Roadblock", "Majestic", "Road closed")
    report(client, user, "Hazard", "Whitefield", "Oil on road")
    kinds = {a["kind"] for a in alerts_of(client, user)}
    assert kinds == {"Closure", "Hazard"}


def test_other_incidents_raise_no_alert(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    report(client, user, "Other", "MG Road", "Stray dog")
    assert alerts_of(client, user) == []


def test_heavy_congestion_raises_alert_without_duplicates(tmp_path,
                                                          monkeypatch):
    client = make_client(tmp_path)
    user = login(client, "alice")
    force_density(monkeypatch, 95)
    client.get("/api/traffic", headers=user)
    client.get("/api/traffic", headers=user)  # refresh again
    items = [a for a in alerts_of(client, user) if a["kind"] == "Congestion"]
    assert len(items) == 6  # one per road, not two


def test_congestion_alert_clears_when_traffic_recovers(tmp_path, monkeypatch):
    client = make_client(tmp_path)
    user = login(client, "alice")
    force_density(monkeypatch, 95)
    client.get("/api/traffic", headers=user)
    force_density(monkeypatch, 10)
    client.get("/api/traffic", headers=user)
    assert alerts_of(client, user) == []


def test_light_traffic_raises_no_alert(tmp_path, monkeypatch):
    client = make_client(tmp_path)
    user = login(client, "alice")
    force_density(monkeypatch, 20)
    client.get("/api/traffic", headers=user)
    assert alerts_of(client, user) == []


def test_closing_incident_clears_its_alert(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    iid = report(client, admin).get_json()["id"]
    assert len(alerts_of(client, admin)) == 1
    client.patch("/api/incidents/%d" % iid, headers=admin,
                 json={"action": "close"})
    assert alerts_of(client, admin) == []


def test_editing_incident_updates_its_alert(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    iid = report(client, admin).get_json()["id"]
    client.patch("/api/incidents/%d" % iid, headers=admin, json={
        "action": "update", "type": "Roadblock", "location": "Majestic"})
    items = alerts_of(client, admin)
    assert len(items) == 1
    assert items[0]["kind"] == "Closure" and items[0]["location"] == "Majestic"
