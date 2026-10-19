import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import app as tms


def make_client(tmp_path):
    tms.DB = str(tmp_path / "test.db")
    tms.init_db()
    return tms.app.test_client()


def register_and_login(client, username, role=None):
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


def test_no_token_is_rejected(tmp_path):
    client = make_client(tmp_path)
    r = client.get("/api/admin/ping")
    assert r.status_code == 401


def test_normal_user_cannot_access_admin(tmp_path):
    client = make_client(tmp_path)
    headers = register_and_login(client, "alice")
    r = client.get("/api/admin/ping", headers=headers)
    assert r.status_code == 403


def test_admin_can_access_admin(tmp_path):
    client = make_client(tmp_path)
    headers = register_and_login(client, "boss", role="admin")
    r = client.get("/api/admin/ping", headers=headers)
    assert r.status_code == 200


def test_emergency_role_access(tmp_path):
    client = make_client(tmp_path)
    ok = register_and_login(client, "amb1", role="emergency")
    no = register_and_login(client, "alice")
    assert client.get("/api/emergency/ping", headers=ok).status_code == 200
    assert client.get("/api/emergency/ping", headers=no).status_code == 403