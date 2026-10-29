"""NFR-09 Data consistency."""
import sqlite3

import pytest

import app as tms
import consistency
from helpers import make_client, login, report


def raw(sql, params=()):
    conn = tms.get_db()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def check(client, admin):
    r = client.get("/api/admin/consistency", headers=admin)
    assert r.status_code == 200
    return r.get_json()


# ---- layer 1: the database refuses impossible records -----------------------
@pytest.mark.parametrize("sql", [
    "INSERT INTO incidents (type, location, description, reported_by) "
    "VALUES ('Meteor', 'MG Road', 'd', 'u')",
    "INSERT INTO incidents (type, location, description, reported_by, status)"
    " VALUES ('Accident', 'MG Road', 'd', 'u', 'Pending')",
    "UPDATE signals SET state = 'Purple'",
    "UPDATE roads SET density = 150, congestion = 'High'",
    "UPDATE roads SET density = -1, congestion = 'Low'",
    "UPDATE roads SET density = 80, congestion = 'Low'",
    "UPDATE roads SET congestion = 'Medium' WHERE congestion = 'Low'",
    "UPDATE roads SET congestion = 'Extreme'",
    "UPDATE users SET role = 'superuser'",
    "INSERT INTO alerts (kind, location, message, source_type, source_id) "
    "VALUES ('Meteor', 'MG Road', 'm', 'road', 'MG Road')",
    "INSERT INTO notifications (username, alert_id, message) "
    "VALUES ('ghost', 999, 'for an alert that does not exist')",
    "INSERT INTO emergency_requests (username, vehicle_id, source, "
    "destination, path, eta_minutes, status) VALUES "
    "('a', 'V1', 'x', 'y', '[]', 1, 'Lost')",
])
def test_database_refuses_bad_records(tmp_path, sql):
    make_client(tmp_path)
    raw("INSERT INTO users (username, email, password_hash) "
        "VALUES ('u', 'u@x.com', 'x')")           # so user updates have a row
    with pytest.raises(sqlite3.DatabaseError):
        raw(sql)


def test_closed_incidents_are_frozen_but_the_reporter_can_be_erased(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    admin = login(client, "boss", "admin")
    iid = report(client, user).get_json()["id"]
    client.patch("/api/incidents/%d" % iid, headers=admin,
                 json={"action": "close"})
    for sql in ("UPDATE incidents SET description = 'rewritten'",
                "UPDATE incidents SET location = 'Elsewhere'",
                "UPDATE incidents SET type = 'Hazard'",
                "UPDATE incidents SET status = 'Reported'"):
        with pytest.raises(sqlite3.DatabaseError):
            raw(sql)
    raw("UPDATE incidents SET reported_by = 'deleted-user'")  # allowed


def test_a_verified_incident_cannot_go_back_to_reported(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    admin = login(client, "boss", "admin")
    iid = report(client, user).get_json()["id"]
    client.patch("/api/incidents/%d" % iid, headers=admin,
                 json={"action": "verify"})
    with pytest.raises(sqlite3.DatabaseError):
        raw("UPDATE incidents SET status = 'Reported'")


def test_triggers_are_installed_once_and_on_every_restart(tmp_path):
    make_client(tmp_path)
    tms.init_db()
    tms.init_db()
    conn = tms.get_db()
    n = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type = "
                     "'trigger'").fetchone()[0]
    conn.close()
    assert n == len(consistency._statements()) + 2  # + the 2 audit triggers


# ---- layer 2: the whole system agrees with itself ---------------------------
def test_a_fresh_system_is_consistent(tmp_path):
    client = make_client(tmp_path)
    result = check(client, login(client, "boss", "admin"))
    assert result == {"consistent": True, "checks_run": 6, "problems": []}


def test_everyday_operations_keep_the_records_consistent(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    alice = login(client, "alice")
    amb = login(client, "amb1", "emergency")
    client.put("/api/subscriptions", headers=alice,
               json={"areas": ["MG Road", "Majestic"]})
    ids = [report(client, alice, t, loc, "x").get_json()["id"]
           for t, loc in (("Accident", "MG Road"), ("Roadblock", "Majestic"),
                          ("Hazard", "Whitefield"), ("Other", "Silk Board"))]
    for _ in range(3):
        client.get("/api/traffic", headers=alice)
    client.patch("/api/incidents/%d" % ids[0], headers=admin,
                 json={"action": "verify"})
    client.patch("/api/incidents/%d" % ids[1], headers=admin, json={
        "action": "update", "location": "Koramangala", "type": "Accident"})
    client.patch("/api/incidents/%d" % ids[2], headers=admin,
                 json={"action": "close"})
    sig = client.get("/api/signals", headers=admin).get_json()["signals"][0]
    client.put("/api/signals/%d" % sig["id"], headers=admin, json={
        "state": "Red" if sig["state"] != "Red" else "Green"})
    rid = client.post("/api/emergency/priority", headers=amb, json={
        "vehicle_id": "AMB-1", "source": "Majestic",
        "destination": "Whitefield"}).get_json()["request_id"]
    client.post("/api/emergency/requests/%d/complete" % rid, headers=amb)
    client.post("/api/admin/roads", headers=admin, json={
        "name": "Hebbal", "lat": 13.0, "lng": 77.6,
        "connects_to": [{"to": "Majestic", "km": 7}]})
    client.post("/api/admin/integrations/ingest", headers=admin, json={
        "source_id": "s1", "type": "traffic",
        "readings": [{"road": "Hebbal", "density": 95},
                     {"road": "MG Road", "density": 10}]})
    client.get("/api/parking", headers=alice)
    client.post("/api/admin/reports", headers=admin, json={})
    result = check(client, admin)
    assert result["problems"] == [] and result["consistent"] is True


@pytest.mark.parametrize("sql, expected", [
    ("DELETE FROM signals WHERE location = 'MG Road'",
     "Road MG Road has no signal"),
    ("DELETE FROM roads WHERE name = 'Whitefield'",
     "Signal at Whitefield has no road"),
    ("UPDATE parking_areas SET location = 'Atlantis' WHERE id = 1",
     "unknown road"),
    ("INSERT INTO subscriptions (username, area) VALUES ('ghost', 'MG Road')",
     "no longer exists"),
    ("INSERT INTO routes (username, source, destination, path, distance_km, "
     "eta_minutes) VALUES ('ghost', 'a', 'b', '[]', 1, 1)",
     "no longer exists"),
    ("DELETE FROM incidents", "no active alert|closed or missing"),
])
def test_the_check_finds_records_that_disagree(tmp_path, sql, expected):
    import re
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    user = login(client, "alice")
    report(client, user, "Accident", "MG Road", "Crash")
    raw(sql)
    result = check(client, admin)
    assert result["consistent"] is False
    assert any(re.search(expected, p) for p in result["problems"]), \
        result["problems"]


def test_congestion_alert_mismatch_is_found(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    raw("UPDATE roads SET density = 90, congestion = 'High' "
        "WHERE name = 'MG Road'")          # High, but nobody raised an alert
    result = check(client, admin)
    assert "MG Road is heavily congested but has no alert" in result[
        "problems"]


def test_the_check_is_admin_only(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/admin/consistency").status_code == 401
    for name, role in (("alice", None), ("amb1", "emergency")):
        h = login(client, name, role)
        assert client.get("/api/admin/consistency",
                          headers=h).status_code == 403
