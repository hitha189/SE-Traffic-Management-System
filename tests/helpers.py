import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import app as tms  # noqa: E402


def make_client(tmp_path):
    tms.DB = str(tmp_path / "test.db")
    tms.init_db()
    return tms.app.test_client()


def login(client, username, role=None):
    """Register (if needed), set the role directly in the DB, log in and
    return the Authorization header."""
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


def report(client, headers, itype="Accident", location="MG Road",
           description="Two vehicles blocking lane"):
    return client.post("/api/incidents", headers=headers, json={
        "type": itype, "location": location, "description": description})


def audit_entries(client, admin_headers, **params):
    r = client.get("/api/admin/audit", headers=admin_headers,
                   query_string=params)
    return r.get_json()["entries"]
