import app as tms
import traffic
from helpers import make_client, login, report


def analytics(client, headers):
    r = client.get("/api/admin/analytics", headers=headers)
    assert r.status_code == 200
    return r.get_json()


def add_history(rows):
    """rows: (road, density, 'YYYY-MM-DD HH:MM:SS')"""
    conn = tms.get_db()
    for road, density, when in rows:
        conn.execute(
            "INSERT INTO traffic_history (road, density, congestion, "
            "recorded_at) VALUES (?, ?, ?, ?)",
            (road, density, traffic.level_for_density(density), when))
    conn.commit()
    conn.close()


def test_analytics_is_admin_only(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/admin/analytics").status_code == 401
    for name, role in (("alice", None), ("amb1", "emergency")):
        h = login(client, name, role)
        assert client.get("/api/admin/analytics",
                          headers=h).status_code == 403


def test_all_four_areas_are_always_present(tmp_path):
    client = make_client(tmp_path)
    data = analytics(client, login(client, "boss", "admin"))
    for area in ("traffic_flow", "congestion", "incidents", "patterns"):
        assert area in data


def test_empty_history_is_explained_not_an_error(tmp_path):
    client = make_client(tmp_path)
    data = analytics(client, login(client, "boss", "admin"))
    assert data["patterns"]["peak_hour"] is None
    assert "Not enough history" in data["patterns"]["note"]
    assert data["incidents"]["total"] == 0
    assert data["congestion"]["most_congested"] == []


def test_traffic_flow_reflects_current_conditions(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    admin = login(client, "boss", "admin")
    client.get("/api/traffic", headers=user)
    flow = analytics(client, admin)["traffic_flow"]
    assert len(flow["roads"]) == 6
    assert sum(flow["levels"].values()) == 6
    assert flow["busiest"]["density"] >= flow["quietest"]["density"]
    densities = [r["density"] for r in flow["roads"]]
    assert flow["average_density"] == round(sum(densities) / 6, 1)


def test_congestion_ranking_uses_history(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    add_history([("MG Road", 90, "2026-10-01 08:00:00")] * 4 +
                [("Majestic", 90, "2026-10-01 08:00:00")] * 1 +
                [("Majestic", 10, "2026-10-01 08:00:00")] * 3 +
                [("Whitefield", 10, "2026-10-01 08:00:00")] * 4)
    cong = analytics(client, admin)["congestion"]
    assert cong["readings_analysed"] == 12
    top = cong["most_congested"]
    assert top[0] == {"name": "MG Road", "readings": 4, "high_readings": 4,
                      "high_percent": 100}
    assert top[1]["name"] == "Majestic" and top[1]["high_percent"] == 25


def test_patterns_find_peak_hour_and_trends(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    rows = []
    for i, d in enumerate([10, 10, 10, 10, 60, 60, 60, 60]):   # Rising
        rows.append(("MG Road", d, "2026-10-01 09:00:00"))
    for d in [80, 80, 80, 80, 20, 20, 20, 20]:                  # Falling
        rows.append(("Majestic", d, "2026-10-01 18:00:00"))
    for d in [30] * 8:                                          # Stable
        rows.append(("Whitefield", d, "2026-10-01 13:00:00"))
    rows.append(("Silk Board", 40, "2026-10-01 13:00:00"))      # too few
    add_history(rows)
    patterns = analytics(client, admin)["patterns"]
    trends = {t["road"]: t["trend"] for t in patterns["road_trends"]}
    assert trends == {"MG Road": "Rising", "Majestic": "Falling",
                      "Whitefield": "Stable"}
    hours = {h["hour"]: h["average_density"]
             for h in patterns["hourly_average_density"]}
    assert set(hours) == {"09", "13", "18"}
    assert hours == {"09": 35.0, "13": 31.1, "18": 50.0}
    assert patterns["peak_hour"] == "18"
    assert patterns["quietest_hour"] == "13"


def test_incident_statistics(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    user = login(client, "alice")
    report(client, user, "Accident", "MG Road", "a")
    first = report(client, user, "Accident", "MG Road", "b").get_json()["id"]
    report(client, user, "Hazard", "Majestic", "c")
    client.patch("/api/incidents/%d" % first, headers=admin,
                 json={"action": "close"})
    inc = analytics(client, admin)["incidents"]
    assert inc["total"] == 3 and inc["open"] == 2
    assert inc["by_type"] == {"Accident": 2, "Hazard": 1}
    assert inc["by_status"] == {"Reported": 2, "Closed": 1}
    assert inc["hotspots"][0] == {"location": "MG Road", "incidents": 2}


def test_every_refresh_adds_history_and_it_stays_bounded(tmp_path,
                                                         monkeypatch):
    client = make_client(tmp_path)
    user = login(client, "alice")
    admin = login(client, "boss", "admin")
    client.get("/api/traffic", headers=user)
    assert analytics(client, admin)["congestion"]["readings_analysed"] == 6
    monkeypatch.setattr(traffic, "HISTORY_LIMIT", 20)
    for _ in range(10):
        client.get("/api/traffic", headers=user)
    assert analytics(client, admin)["congestion"]["readings_analysed"] <= 20
