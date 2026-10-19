import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import app as tms


def make_client(tmp_path):
    tms.DB = str(tmp_path / "test.db")
    tms.init_db()
    return tms.app.test_client()


def test_register_valid(tmp_path):
    client = make_client(tmp_path)
    r = client.post("/api/register", json={
        "username": "alice", "email": "a@x.com", "password": "Valid@123"})
    assert r.status_code == 201


def test_register_missing_details(tmp_path):
    client = make_client(tmp_path)
    r = client.post("/api/register", json={"username": "bob"})
    assert r.status_code == 400


def test_register_duplicate(tmp_path):
    client = make_client(tmp_path)
    body = {"username": "alice", "email": "a@x.com", "password": "Valid@123"}
    client.post("/api/register", json=body)
    r = client.post("/api/register", json=body)
    assert r.status_code == 409