"""NFR-06 Scalability: more roads, users, sensors, parking areas, data."""
import time

import app as tms
import routing
from helpers import make_client, login, report

TARGET_MS = tms.RESPONSE_TIME_TARGET_MS


def took_ms(response):
    return float(response.headers["X-Response-Time-ms"])


def add_road(client, admin, name, links, lat=12.95, lng=77.6):
    return client.post("/api/admin/roads", headers=admin, json={
        "name": name, "lat": lat, "lng": lng, "connects_to": links})


# ---- a new road needs no code change ---------------------------------------
def test_a_new_road_appears_everywhere(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    user = login(client, "alice")
    r = add_road(client, admin, "Hebbal", [{"to": "Majestic", "km": 7.5}],
                 lat=13.0358, lng=77.597)
    assert r.status_code == 201
    names = [x["name"] for x in client.get(
        "/api/traffic", headers=user).get_json()["roads"]]
    assert "Hebbal" in names                                   # map / traffic
    assert "Hebbal" in client.get("/api/places", headers=user
                                  ).get_json()["places"]       # route lists
    sigs = client.get("/api/signals", headers=admin).get_json()["signals"]
    assert "Hebbal" in [s["location"] for s in sigs]           # signals
    route = client.get("/api/route?source=Hebbal&destination=Whitefield",
                       headers=user).get_json()
    assert route["path"][0] == "Hebbal"                        # routing
    assert route["path"][-1] == "Whitefield"
    flow = client.get("/api/admin/analytics", headers=admin).get_json()
    assert "Hebbal" in [x["name"] for x in flow["traffic_flow"]["roads"]]


def test_alerts_and_notifications_work_on_a_new_road(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    alice = login(client, "alice")
    add_road(client, admin, "Hebbal", [{"to": "Majestic", "km": 7.5}])
    client.put("/api/subscriptions", headers=alice,
               json={"areas": ["Majestic"]})        # next to the new road
    report(client, admin, "Accident", "Hebbal", "Crash")
    notes = client.get("/api/notifications", headers=alice).get_json()
    assert len(notes["notifications"]) == 1
    assert "Hebbal" in notes["notifications"][0]["message"]


def test_emergency_routing_uses_a_new_road(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    amb = login(client, "amb1", "emergency")
    add_road(client, admin, "Hebbal", [{"to": "Majestic", "km": 7.5}])
    r = client.post("/api/emergency/priority", headers=amb, json={
        "vehicle_id": "AMB-9", "source": "Hebbal",
        "destination": "Koramangala"})
    assert r.status_code == 201
    assert r.get_json()["route"]["path"][0] == "Hebbal"


def test_new_road_is_saved_and_logged(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    add_road(client, admin, "Hebbal", [{"to": "Majestic", "km": 7.5}])
    tms.init_db()  # a restart must keep it, and not duplicate the seed data
    conn = tms.get_db()
    assert conn.execute("SELECT COUNT(*) FROM roads WHERE name = 'Hebbal'"
                        ).fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM road_links").fetchone()[0] == 9
    conn.close()
    log = client.get("/api/admin/audit?action=road_added",
                     headers=admin).get_json()["entries"]
    assert len(log) == 1 and "Majestic" in log[0]["details"]


def test_bad_roads_are_rejected(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    ok = [{"to": "MG Road", "km": 2}]
    assert add_road(client, admin, "MG Road", ok).status_code == 409
    for name, links, lat in [
        ("", ok, 12.9), (None, ok, 12.9), ("N" * 51, ok, 12.9),
        ("A", ok, 91), ("A", ok, "north"), ("A", ok, True),
        ("A", [], 12.9), ("A", "MG Road", 12.9),
        ("A", [{"to": "Atlantis", "km": 2}], 12.9),
        ("A", [{"to": "MG Road", "km": 0}], 12.9),
        ("A", [{"to": "MG Road", "km": -3}], 12.9),
        ("A", [{"to": "MG Road", "km": 101}], 12.9),
        ("A", [{"to": "MG Road", "km": "far"}], 12.9),
        ("A", [{"to": "MG Road", "km": 1}] * 11, 12.9),
    ]:
        assert add_road(client, admin, name, links, lat=lat
                        ).status_code == 400, (name, links, lat)
    assert len(client.get("/api/traffic", headers=admin
                          ).get_json()["roads"]) == 6


def test_only_admins_can_add_roads(tmp_path):
    client = make_client(tmp_path)
    body = {"name": "Hebbal", "lat": 13, "lng": 77,
            "connects_to": [{"to": "Majestic", "km": 5}]}
    assert client.post("/api/admin/roads", json=body).status_code == 401
    for name, role in (("alice", None), ("amb1", "emergency")):
        h = login(client, name, role)
        assert client.post("/api/admin/roads", headers=h,
                           json=body).status_code == 403


def test_database_network_matches_the_built_in_one(tmp_path):
    make_client(tmp_path)
    conn = tms.get_db()
    assert routing.build_graph(conn) == routing.build_graph()
    assert routing.known_places(conn) == routing.known_places()
    conn.close()


# ---- growth: many roads, parking areas, data -------------------------------
def test_sixty_more_roads_still_respond_within_the_target(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    previous = "Majestic"
    for i in range(60):
        name = "Ring Road %02d" % i
        assert add_road(client, admin, name,
                        [{"to": previous, "km": 1.5}]).status_code == 201
        previous = name
    for i in range(30):
        assert client.post("/api/admin/parking", headers=admin, json={
            "name": "Lot %d" % i, "location": "Ring Road %02d" % i,
            "capacity": 50}).status_code == 201

    traffic = client.get("/api/traffic", headers=admin)
    assert len(traffic.get_json()["roads"]) == 66
    assert took_ms(traffic) < TARGET_MS
    route = client.get("/api/route?source=Majestic&destination=" + previous,
                       headers=admin)
    assert route.status_code == 200 and len(route.get_json()["path"]) == 61
    assert took_ms(route) < TARGET_MS
    for url in ("/api/places", "/api/parking", "/api/signals",
                "/api/admin/analytics", "/api/alerts"):
        r = client.get(url, headers=admin)
        assert r.status_code == 200 and took_ms(r) < TARGET_MS, url
    assert len(client.get("/api/parking", headers=admin
                          ).get_json()["parking"]) == 36


def test_large_amounts_of_data_stay_fast(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    conn = tms.get_db()
    conn.executemany(
        "INSERT INTO incidents (type, location, description, reported_by, "
        "status) VALUES (?, ?, ?, ?, ?)",
        [("Accident", "MG Road", "d%d" % i, "u%d" % (i % 50), "Reported")
         for i in range(5000)])
    conn.executemany(
        "INSERT INTO audit_log (actor, action, target, details) "
        "VALUES (?, ?, ?, ?)",
        [("boss", "signal_change", "signal:1", "x%d" % i)
         for i in range(20000)])
    conn.executemany(
        "INSERT INTO traffic_history (road, density, congestion) "
        "VALUES (?, ?, ?)",
        [("MG Road", i % 100, "Low") for i in range(10000)])
    conn.commit()
    conn.close()

    r = client.get("/api/incidents", headers=admin)
    assert len(r.get_json()["incidents"]) == 500     # newest 500 only
    assert took_ms(r) < TARGET_MS
    for url in ("/api/admin/analytics", "/api/admin/audit?limit=100",
                "/api/admin/audit?action=signal_change&limit=50",
                "/api/admin/summary"):
        r = client.get(url, headers=admin)
        assert r.status_code == 200 and took_ms(r) < TARGET_MS, url
    rep = client.post("/api/admin/reports", headers=admin, json={})
    assert rep.status_code == 201 and took_ms(rep) < TARGET_MS


def test_thousands_of_users_do_not_slow_login(tmp_path):
    client = make_client(tmp_path)
    alice = login(client, "alice")
    conn = tms.get_db()
    conn.executemany(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        [("user%d" % i, "u%d@x.com" % i, "x") for i in range(5000)])
    conn.commit()
    conn.close()
    r = client.post("/api/login", json={"username": "alice",
                                        "password": "Valid@123"})
    assert r.status_code == 200 and took_ms(r) < TARGET_MS
    assert client.get("/api/traffic", headers=alice).status_code == 200


def test_indexes_exist_for_the_busy_tables(tmp_path):
    make_client(tmp_path)
    conn = tms.get_db()
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index'")}
    conn.close()
    for index in ("idx_incidents_status", "idx_incidents_location",
                  "idx_alerts_active", "idx_alerts_source",
                  "idx_notifications_user", "idx_audit_action",
                  "idx_audit_actor", "idx_history_road", "idx_routes_user",
                  "idx_parking_location", "idx_subscriptions_area"):
        assert index in names
