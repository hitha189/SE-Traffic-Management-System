import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import app as tms


def make_client(tmp_path):
    tms.DB = str(tmp_path / "test.db")
    tms.init_db()
    return tms.app.test_client()


def headers_for(client, username, role=None):
    client.post("/api/register", json={
        "username": username, "email": username + "@x.com",
        "password": "Valid@123"})
    if role:
        conn = tms.get_db()
        conn.execute("UPDATE users SET role = ? WHERE username = ?",
                     (role, username))
        conn.commit()
        conn.close()
    r = client.post("/api/login", json={
        "username": username, "password": "Valid@123"})
    return {"Authorization": "Bearer " + r.get_json()["token"]}


def test_route_is_saved_in_history(tmp_path):
    client = make_client(tmp_path)
    h = headers_for(client, "alice")
    client.get("/api/route?source=Majestic&destination=Whitefield", headers=h)
    r = client.get("/api/routes/history", headers=h)
    assert r.status_code == 200
    routes = r.get_json()["routes"]
    assert len(routes) == 1
    assert routes[0]["source"] == "Majestic"
    assert routes[0]["path"][-1] == "Whitefield"


def test_history_requires_login(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/routes/history").status_code == 401


def test_summary_blocked_for_normal_user(tmp_path):
    client = make_client(tmp_path)
    h = headers_for(client, "alice")
    assert client.get("/api/admin/summary", headers=h).status_code == 403


def test_summary_for_admin(tmp_path):
    client = make_client(tmp_path)
    h = headers_for(client, "boss", role="admin")
    r = client.get("/api/admin/summary", headers=h)
    assert r.status_code == 200
    records = r.get_json()["records"]
    assert records["users"] == 1
    assert records["roads"] >= 5