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


def test_report_incident_valid(tmp_path):
    client = make_client(tmp_path)
    headers = login_headers(client)
    r = client.post("/api/incidents", headers=headers, json={
        "type": "Accident", "location": "MG Road",
        "description": "Two vehicles blocking lane"})
    assert r.status_code == 201
    listed = client.get("/api/incidents", headers=headers).get_json()
    assert listed["incidents"][0]["location"] == "MG Road"


def test_report_incident_invalid(tmp_path):
    client = make_client(tmp_path)
    headers = login_headers(client)
    r = client.post("/api/incidents", headers=headers, json={
        "type": "Alien landing", "location": "", "description": ""})
    assert r.status_code == 400


def test_report_incident_requires_login(tmp_path):
    client = make_client(tmp_path)
    r = client.post("/api/incidents", json={
        "type": "Accident", "location": "MG Road", "description": "Crash"})
    assert r.status_code == 401