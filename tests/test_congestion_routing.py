import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import app as tms
import routing


def make_client(tmp_path):
    tms.DB = str(tmp_path / "test.db")
    tms.init_db()
    return tms.app.test_client()


def login_headers(client):
    client.post("/api/register", json={
        "username": "alice", "email": "a@x.com", "password": "Valid@123"})
    r = client.post("/api/login", json={
        "username": "alice", "password": "Valid@123"})
    return {"Authorization": "Bearer " + r.get_json()["token"]}


def test_quiet_roads_keep_shortest_route():
    quiet = {"MG Road": 5, "Indiranagar": 5}
    route = routing.find_route("Majestic", "Whitefield", quiet)
    assert "MG Road" in route["path"]


def test_heavy_congestion_changes_route():
    jam = {"MG Road": 100, "Indiranagar": 100}
    route = routing.find_route("Majestic", "Whitefield", jam)
    assert "MG Road" not in route["path"]
    assert route["congestion_aware"] is True


def test_route_api_uses_congestion_data(tmp_path):
    client = make_client(tmp_path)
    headers = login_headers(client)
    conn = tms.get_db()
    conn.execute("UPDATE roads SET density = 100, congestion = 'High' "
                 "WHERE name IN ('MG Road', 'Indiranagar')")
    conn.commit()
    conn.close()
    r = client.get("/api/route?source=Majestic&destination=Whitefield",
                   headers=headers)
    assert r.status_code == 200
    assert "MG Road" not in r.get_json()["path"]