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


def test_find_route_majestic_to_whitefield():
    route = routing.find_route("Majestic", "Whitefield")
    assert route is not None
    assert route["path"][0] == "Majestic"
    assert route["path"][-1] == "Whitefield"
    assert route["distance_km"] > 0


def test_unknown_place_returns_none():
    assert routing.find_route("Majestic", "Atlantis") is None


def test_route_api_valid(tmp_path):
    client = make_client(tmp_path)
    r = client.get("/api/route?source=Majestic&destination=Whitefield",
                   headers=login_headers(client))
    assert r.status_code == 200
    assert "eta_minutes" in r.get_json()


def test_route_api_invalid(tmp_path):
    client = make_client(tmp_path)
    headers = login_headers(client)
    assert client.get("/api/route?source=Majestic&destination=Majestic",
                      headers=headers).status_code == 400
    assert client.get("/api/route?source=Majestic&destination=Atlantis",
                      headers=headers).status_code == 404


def test_route_requires_login(tmp_path):
    client = make_client(tmp_path)
    r = client.get("/api/route?source=Majestic&destination=Whitefield")
    assert r.status_code == 401