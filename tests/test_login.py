import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import app as tms


def make_client(tmp_path):
    tms.DB = str(tmp_path / "test.db")
    tms.init_db()
    client = tms.app.test_client()
    client.post("/api/register", json={
        "username": "alice", "email": "a@x.com", "password": "Valid@123"})
    return client


def test_login_valid(tmp_path):
    client = make_client(tmp_path)
    r = client.post("/api/login", json={
        "username": "alice", "password": "Valid@123"})
    assert r.status_code == 200
    assert r.get_json()["role"] == "user"


def test_login_wrong_password(tmp_path):
    client = make_client(tmp_path)
    r = client.post("/api/login", json={
        "username": "alice", "password": "wrong123"})
    assert r.status_code == 401


def test_login_unknown_user(tmp_path):
    client = make_client(tmp_path)
    r = client.post("/api/login", json={
        "username": "nobody", "password": "Valid@123"})
    assert r.status_code == 401