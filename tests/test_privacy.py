"""NFR-10 Data privacy: collect only what is needed, protect it."""
import json

import app as tms
import storage
from helpers import make_client, login, report

EMAIL = "secret.person@example.com"


def register(client, username, email=EMAIL, role=None):
    client.post("/api/register", json={
        "username": username, "email": email, "password": "Valid@123"})
    if role:
        conn = tms.get_db()
        conn.execute("UPDATE users SET role = ? WHERE username = ?",
                     (role, username))
        conn.commit()
        conn.close()
    r = client.post("/api/login", json={"username": username,
                                        "password": "Valid@123"})
    return {"Authorization": "Bearer " + r.get_json()["token"]}


def columns(table):
    conn = tms.get_db()
    names = [r[1] for r in conn.execute("PRAGMA table_info(%s)" % table)]
    conn.close()
    return names


# ---- collect only what is necessary ------------------------------------------
def test_accounts_hold_only_the_details_the_srs_needs(tmp_path):
    make_client(tmp_path)
    assert columns("users") == ["id", "username", "email", "password_hash",
                                "role"]


def test_no_table_stores_phone_address_or_gps(tmp_path):
    make_client(tmp_path)
    conn = tms.get_db()
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")]
    conn.close()
    forbidden = ("phone", "mobile", "address", "gps", "birth", "ip_address",
                 "device", "latitude", "longitude")
    for table in tables:
        for col in columns(table):
            assert not any(word in col.lower() for word in forbidden), \
                (table, col)


def test_user_locations_are_named_areas_not_coordinates(tmp_path):
    make_client(tmp_path)
    for table in ("routes", "subscriptions", "notifications", "incidents",
                  "emergency_requests"):
        assert not {"lat", "lng"} & set(columns(table)), table


def test_registration_does_not_ask_for_anything_extra(tmp_path):
    client = make_client(tmp_path)
    r = client.post("/api/register", json={
        "username": "bob", "email": "b@x.com", "password": "Valid@123",
        "phone": "9999999999", "address": "1 Main St"})
    assert r.status_code == 201
    conn = tms.get_db()
    row = dict(conn.execute("SELECT * FROM users WHERE username = 'bob'"
                            ).fetchone())
    conn.close()
    assert set(row) == {"id", "username", "email", "password_hash", "role"}


# ---- protect it -----------------------------------------------------------------
def test_passwords_are_stored_as_hashes(tmp_path):
    client = make_client(tmp_path)
    register(client, "alice")
    conn = tms.get_db()
    stored = conn.execute("SELECT password_hash FROM users").fetchone()[0]
    conn.close()
    assert "Valid@123" not in stored and len(stored) > 30


def test_email_and_hash_never_appear_in_admin_or_shared_data(tmp_path):
    client = make_client(tmp_path)
    alice = register(client, "alice")
    admin = register(client, "boss", "boss@example.com", role="admin")
    client.put("/api/subscriptions", headers=alice, json={"areas": ["MG Road"]})
    client.get("/api/route?source=Majestic&destination=Whitefield",
               headers=alice)
    report(client, alice, "Accident", "MG Road", "Crash")
    client.post("/api/admin/reports", headers=admin, json={})
    client.get("/api/traffic", headers=alice)
    pages = []
    for headers, url in [
        (admin, "/api/admin/summary"), (admin, "/api/admin/audit?limit=500"),
        (admin, "/api/incidents"), (admin, "/api/admin/analytics"),
        (admin, "/api/admin/reports"), (admin, "/api/admin/reports/1"),
        (admin, "/api/admin/reports/1?format=text"),
        (admin, "/api/admin/status"), (admin, "/api/admin/consistency"),
        (admin, "/api/admin/integrations"), (admin, "/api/signals"),
        (alice, "/api/incidents"), (alice, "/api/alerts"),
        (alice, "/api/notifications"), (alice, "/api/parking"),
        (alice, "/api/subscriptions"), (alice, "/api/routes/history"),
        (None, "/api/health"),
    ]:
        r = client.get(url, headers=headers)
        assert r.status_code == 200, url
        pages.append(r.get_data(as_text=True))
    everything = "\n".join(pages)
    assert EMAIL not in everything and "boss@example.com" not in everything
    assert "password_hash" not in everything and "pbkdf2" not in everything \
        and "scrypt" not in everything


def test_only_admins_see_who_reported_an_incident(tmp_path):
    client = make_client(tmp_path)
    alice = register(client, "alice")
    bob = register(client, "bob")
    admin = register(client, "boss", "b@x.com", role="admin")
    report(client, alice)
    as_bob = client.get("/api/incidents", headers=bob).get_json()["incidents"]
    as_admin = client.get("/api/incidents",
                          headers=admin).get_json()["incidents"]
    assert "reported_by" not in as_bob[0]
    assert as_admin[0]["reported_by"] == "alice"
    assert as_bob[0]["location"] == "MG Road"       # the useful part remains


def test_route_history_is_private_to_its_owner(tmp_path):
    client = make_client(tmp_path)
    alice = register(client, "alice")
    bob = register(client, "bob")
    client.get("/api/route?source=Majestic&destination=Whitefield",
               headers=alice)
    assert len(client.get("/api/routes/history", headers=alice
                          ).get_json()["routes"]) == 1
    assert client.get("/api/routes/history", headers=bob
                      ).get_json()["routes"] == []


def test_location_data_is_not_kept_forever(tmp_path):
    client = make_client(tmp_path)
    alice = register(client, "alice")
    conn = tms.get_db()
    for days in (1, 29, 31, 90):
        conn.execute(
            "INSERT INTO routes (username, source, destination, path, "
            "distance_km, eta_minutes, created_at) VALUES ('alice', 'a', "
            "'b', '[]', 1, 1, datetime('now', ?))", ("-%d days" % days,))
    conn.commit()
    assert storage.purge_old_routes(conn, 30) == 2
    left = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
    conn.close()
    assert left == 2


def test_old_routes_are_removed_automatically_at_startup(tmp_path):
    client = make_client(tmp_path)
    register(client, "alice")
    conn = tms.get_db()
    conn.execute(
        "INSERT INTO routes (username, source, destination, path, "
        "distance_km, eta_minutes, created_at) VALUES ('alice', 'a', 'b', "
        "'[]', 1, 1, datetime('now', '-45 days'))")
    conn.commit()
    conn.close()
    tms.init_db()                                  # what happens on start
    conn = tms.get_db()
    assert conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0] == 0
    conn.close()


# ---- the user's own rights --------------------------------------------------------
def test_user_can_download_all_their_data(tmp_path):
    client = make_client(tmp_path)
    alice = register(client, "alice")
    bob = register(client, "bob", "bob@example.com")
    client.put("/api/subscriptions", headers=alice,
               json={"areas": ["MG Road"]})
    client.get("/api/route?source=Majestic&destination=Whitefield",
               headers=alice)
    report(client, alice, "Accident", "MG Road", "Crash")
    report(client, bob, "Hazard", "Majestic", "Oil")
    r = client.get("/api/me/export", headers=alice)
    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "no-store"
    data = r.get_json()
    assert data["profile"] == {"username": "alice", "email": EMAIL,
                               "role": "user"}
    assert data["subscribed_areas"] == ["MG Road"]
    assert len(data["route_history"]) == 1
    assert len(data["notifications"]) == 2   # her own, and Bob's nearby one
    assert [i["location"] for i in data["incidents_reported"]] == ["MG Road"]
    assert data["retention"]["route_history_days"] == 30
    text = json.dumps(data)
    assert "password" not in text and "bob" not in text


def test_export_needs_login(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/me/export").status_code == 401
    assert client.delete("/api/me").status_code == 401


def test_deleting_an_account_removes_personal_data(tmp_path):
    client = make_client(tmp_path)
    alice = register(client, "alice")
    admin = register(client, "boss", "b@x.com", role="admin")
    client.put("/api/subscriptions", headers=alice,
               json={"areas": ["MG Road"]})
    client.get("/api/route?source=Majestic&destination=Whitefield",
               headers=alice)
    open_id = report(client, alice, "Accident", "MG Road", "Crash"
                     ).get_json()["id"]
    closed_id = report(client, alice, "Hazard", "Majestic", "Oil"
                       ).get_json()["id"]
    client.patch("/api/incidents/%d" % closed_id, headers=admin,
                 json={"action": "close"})

    r = client.delete("/api/me", headers=alice, json={"password": "Valid@123"})
    assert r.status_code == 200

    conn = tms.get_db()
    for table in ("users", "routes", "subscriptions", "notifications"):
        col = "username"
        assert conn.execute("SELECT COUNT(*) FROM %s WHERE %s = 'alice'" %
                            (table, col)).fetchone()[0] == 0, table
    reporters = {row[0] for row in conn.execute(
        "SELECT reported_by FROM incidents")}
    conn.close()
    assert reporters == {"deleted-user"}   # incidents stay, name does not
    incidents = client.get("/api/incidents", headers=admin
                           ).get_json()["incidents"]
    assert {i["id"] for i in incidents} == {open_id, closed_id}
    assert client.post("/api/login", json={
        "username": "alice", "password": "Valid@123"}).status_code == 401
    # the old login token stops working immediately
    assert client.get("/api/traffic", headers=alice).status_code == 401
    assert client.get("/api/me/export", headers=alice).status_code == 401
    assert client.get("/api/admin/consistency", headers=admin
                      ).get_json()["consistent"] is True
    log = client.get("/api/admin/audit?action=account_deleted",
                     headers=admin).get_json()["entries"]
    assert len(log) == 1 and "removed by owner" in log[0]["details"]
    assert EMAIL not in json.dumps(log)


def test_deleting_needs_the_right_password(tmp_path):
    client = make_client(tmp_path)
    alice = register(client, "alice")
    for body in ({}, {"password": "wrong"}, {"password": 123456},
                 {"password": None}):
        assert client.delete("/api/me", headers=alice,
                             json=body).status_code == 403
    assert client.get("/api/traffic", headers=alice).status_code == 200


def test_admins_cannot_delete_themselves_by_accident(tmp_path):
    client = make_client(tmp_path)
    admin = register(client, "boss", "b@x.com", role="admin")
    r = client.delete("/api/me", headers=admin, json={"password": "Valid@123"})
    assert r.status_code == 403
    assert client.get("/api/signals", headers=admin).status_code == 200


def test_emergency_users_data_is_erased_too(tmp_path):
    client = make_client(tmp_path)
    amb = register(client, "amb1", "amb@x.com", role="emergency")
    admin = register(client, "boss", "b@x.com", role="admin")
    client.post("/api/emergency/priority", headers=amb, json={
        "vehicle_id": "AMB-1", "source": "Majestic",
        "destination": "Whitefield"})
    assert client.delete("/api/me", headers=amb,
                         json={"password": "Valid@123"}).status_code == 200
    assert client.get("/api/emergency/requests", headers=admin
                      ).get_json()["requests"] == []
