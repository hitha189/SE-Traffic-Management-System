import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import app as tms


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


def test_traffic_requires_login(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/traffic").status_code == 401


def test_traffic_returns_roads_with_levels(tmp_path):
    client = make_client(tmp_path)
    r = client.get("/api/traffic", headers=login_headers(client))
    assert r.status_code == 200
    roads = r.get_json()["roads"]
    assert len(roads) >= 5
    for road in roads:
        assert road["congestion"] in ("Low", "Medium", "High")
        assert "lat" in road and "lng" in road


def test_traffic_includes_mg_road(tmp_path):
    client = make_client(tmp_path)
    r = client.get("/api/traffic", headers=login_headers(client))
    names = [road["name"] for road in r.get_json()["roads"]]
    assert "MG Road" in names