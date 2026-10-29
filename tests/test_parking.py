import sqlite3

import pytest

import app as tms
import parking
from helpers import make_client, login, audit_entries


def get_parking(client, headers, **params):
    return client.get("/api/parking", headers=headers, query_string=params)


def test_parking_requires_login(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/parking").status_code == 401


def test_every_role_can_view_parking(tmp_path):
    client = make_client(tmp_path)
    for name, role in (("alice", None), ("boss", "admin"),
                       ("amb1", "emergency")):
        r = get_parking(client, login(client, name, role))
        assert r.status_code == 200
        assert len(r.get_json()["parking"]) == 6


def test_each_area_shows_what_drivers_need(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    for area in get_parking(client, user).get_json()["parking"]:
        for field in ("name", "location", "capacity", "available",
                      "occupancy_percent", "status", "updated_at"):
            assert field in area
        assert area["status"] in ("Available", "Limited", "Full")


def test_spaces_always_stay_within_capacity(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    for _ in range(40):  # each request moves the simulated numbers
        for area in get_parking(client, user).get_json()["parking"]:
            assert 0 <= area["available"] <= area["capacity"]
            assert 0 <= area["occupancy_percent"] <= 100


def test_filter_by_location(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    areas = get_parking(client, user, location="MG Road").get_json()["parking"]
    assert len(areas) == 1 and areas[0]["location"] == "MG Road"
    none = get_parking(client, user, location="Atlantis").get_json()
    assert none["parking"] == []


def test_summary_matches_the_areas(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    data = get_parking(client, user).get_json()
    assert data["summary"]["areas"] == 6
    assert data["summary"]["total_available"] == sum(
        a["available"] for a in data["parking"])
    assert data["summary"]["total_capacity"] == sum(
        a["capacity"] for a in data["parking"])


def test_status_labels():
    assert parking._status(0, 100) == "Full"
    assert parking._status(20, 100) == "Limited"
    assert parking._status(21, 100) == "Available"


def test_admin_can_add_a_parking_area(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    r = client.post("/api/admin/parking", headers=admin, json={
        "name": "MG Road Metro Parking", "location": "MG Road",
        "capacity": 60})
    assert r.status_code == 201
    area = r.get_json()["parking_area"]
    assert area["available"] == 60 and area["status"] == "Available"
    names = [a["name"] for a in get_parking(client, admin).get_json()["parking"]]
    assert "MG Road Metro Parking" in names
    log = audit_entries(client, admin, action="parking_added")
    assert len(log) == 1 and "MG Road Metro Parking" in log[0]["details"]


@pytest.mark.parametrize("body", [
    {"location": "MG Road", "capacity": 10},                       # no name
    {"name": "X", "location": "Atlantis", "capacity": 10},         # bad place
    {"name": "X", "location": "MG Road", "capacity": 0},
    {"name": "X", "location": "MG Road", "capacity": -4},
    {"name": "X", "location": "MG Road", "capacity": "ten"},
    {"name": "X", "location": "MG Road", "capacity": True},
    {"name": "X", "location": "MG Road", "capacity": 10001},
    {"name": 5, "location": "MG Road", "capacity": 10},
    {"name": "N" * 81, "location": "MG Road", "capacity": 10},
])
def test_bad_parking_area_is_rejected(tmp_path, body):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    assert client.post("/api/admin/parking", headers=admin,
                       json=body).status_code == 400
    assert len(get_parking(client, admin).get_json()["parking"]) == 6


def test_duplicate_area_is_409(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    r = client.post("/api/admin/parking", headers=admin, json={
        "name": "MG Road Parking", "location": "MG Road", "capacity": 10})
    assert r.status_code == 409


def test_only_admin_can_add_areas(tmp_path):
    client = make_client(tmp_path)
    body = {"name": "New", "location": "MG Road", "capacity": 10}
    assert client.post("/api/admin/parking", json=body).status_code == 401
    for name, role in (("alice", None), ("amb1", "emergency")):
        h = login(client, name, role)
        assert client.post("/api/admin/parking", headers=h,
                           json=body).status_code == 403


def test_database_refuses_impossible_parking_numbers(tmp_path):
    make_client(tmp_path)
    conn = tms.get_db()
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE parking_areas SET available = capacity + 1")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE parking_areas SET available = -1")
    conn.close()
