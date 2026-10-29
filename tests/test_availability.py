"""NFR-03 Availability."""
import audit
import health
from helpers import make_client, login, tms


def test_health_check_needs_no_login(tmp_path):
    client = make_client(tmp_path)
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok" and body["database"] == "ok"
    assert body["uptime_seconds"] >= 0


def test_health_reports_an_outage_and_recovers_without_restart(tmp_path):
    client = make_client(tmp_path)
    good = tms.DB
    try:
        tms.DB = str(tmp_path / "missing-folder" / "tms.db")  # unreachable
        r = client.get("/api/health")
        assert r.status_code == 503
        assert r.get_json() == {"status": "degraded",
                                "database": "unavailable",
                                "uptime_seconds": r.get_json()[
                                    "uptime_seconds"]}
    finally:
        tms.DB = good
    r = client.get("/api/health")  # database is back: no restart needed
    assert r.status_code == 200 and r.get_json()["status"] == "ok"


def test_other_requests_fail_cleanly_during_an_outage(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    good = tms.DB
    try:
        tms.DB = str(tmp_path / "missing-folder" / "tms.db")
        r = client.get("/api/traffic", headers=user)
        assert r.status_code == 500 and r.is_json
    finally:
        tms.DB = good
    assert client.get("/api/traffic", headers=user).status_code == 200


def test_status_shows_availability_to_admins_only(tmp_path):
    client = make_client(tmp_path)
    health.reset()
    user = login(client, "alice")
    admin = login(client, "boss", "admin")
    assert client.get("/api/admin/status").status_code == 401
    assert client.get("/api/admin/status", headers=user).status_code == 403
    body = client.get("/api/admin/status", headers=admin).get_json()
    assert body["database"] == "ok"
    assert body["requests"] >= 4
    assert body["server_errors"] == 0
    assert body["availability_percent"] == 100.0
    assert body["target_percent"] == 99.0 and body["meets_target"] is True


def test_normal_operation_has_no_server_errors(tmp_path):
    client = make_client(tmp_path)
    health.reset()
    user = login(client, "alice")
    admin = login(client, "boss", "admin")
    urls = [("/api/traffic", user), ("/api/alerts", user),
            ("/api/parking", user), ("/api/places", user),
            ("/api/incidents", user), ("/api/health", None),
            ("/api/signals", admin), ("/api/admin/analytics", admin),
            ("/api/admin/audit", admin), ("/api/admin/consistency", admin)]
    for _ in range(15):
        for url, headers in urls:
            assert client.get(url, headers=headers).status_code == 200
    client.get("/api/signals", headers=user)       # 403 is not a failure
    client.get("/api/does-not-exist")              # 404 is not a failure
    stats = health.snapshot()
    assert stats["requests"] >= 150
    assert stats["server_errors"] == 0
    assert stats["availability_percent"] == 100.0


def test_server_errors_are_counted_and_service_continues(tmp_path,
                                                         monkeypatch):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    sig = client.get("/api/signals", headers=admin).get_json()["signals"][0]
    new = "Red" if sig["state"] != "Red" else "Green"
    health.reset()

    def broken(*args, **kwargs):
        raise RuntimeError("simulated fault")
    monkeypatch.setattr(audit, "log_action", broken)
    r = client.put("/api/signals/%d" % sig["id"], headers=admin,
                   json={"state": new})
    assert r.status_code == 500
    monkeypatch.undo()
    for _ in range(4):                        # the system keeps serving
        assert client.get("/api/signals", headers=admin).status_code == 200
    stats = health.snapshot()
    assert stats["server_errors"] == 1
    assert stats["availability_percent"] == 80.0
    assert stats["meets_target"] is False
