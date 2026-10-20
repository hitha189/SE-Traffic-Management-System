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


def test_security_headers_present(tmp_path):
    client = make_client(tmp_path)
    r = client.post("/api/login", json={
        "username": "alice", "password": "Valid@123"})
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Cache-Control"] == "no-store"


def test_account_locks_after_repeated_failures(tmp_path):
    client = make_client(tmp_path)
    for _ in range(tms.MAX_FAILED_LOGINS):
        r = client.post("/api/login", json={
            "username": "alice", "password": "wrong123"})
        assert r.status_code == 401
    # Even the correct password is refused while locked
    r = client.post("/api/login", json={
        "username": "alice", "password": "Valid@123"})
    assert r.status_code == 429


def test_successful_login_resets_failures(tmp_path):
    client = make_client(tmp_path)
    for _ in range(tms.MAX_FAILED_LOGINS - 1):
        client.post("/api/login", json={
            "username": "alice", "password": "wrong123"})
    ok = client.post("/api/login", json={
        "username": "alice", "password": "Valid@123"})
    assert ok.status_code == 200
    assert "alice" not in tms.FAILED_LOGINS