import time

import app as tms
from helpers import make_client, login

TARGET_MS = tms.RESPONSE_TIME_TARGET_MS


def test_target_is_defined():
    assert TARGET_MS == 1000


def test_responses_carry_timing_header(tmp_path):
    client = make_client(tmp_path)
    r = client.get("/")
    assert float(r.headers["X-Response-Time-ms"]) >= 0


def test_normal_requests_meet_the_target(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    admin = login(client, "boss", "admin")
    calls = [
        ("GET", "/api/traffic", user),
        ("GET", "/api/alerts", user),
        ("GET", "/api/incidents", user),
        ("GET", "/api/places", user),
        ("GET", "/api/route?source=Majestic&destination=Whitefield", user),
        ("GET", "/api/signals", admin),
        ("GET", "/api/admin/audit", admin),
    ]
    for method, url, headers in calls:
        start = time.perf_counter()
        r = client.open(url, method=method, headers=headers)
        elapsed = (time.perf_counter() - start) * 1000
        assert r.status_code == 200, url
        assert elapsed < TARGET_MS, "%s took %.0f ms" % (url, elapsed)
        assert float(r.headers["X-Response-Time-ms"]) < TARGET_MS


def test_expected_load_stays_within_target(tmp_path):
    """50 users reading traffic and alerts in a row (expected prototype
    load): every single response must still meet the target."""
    client = make_client(tmp_path)
    user = login(client, "alice")
    slowest = 0.0
    for _ in range(50):
        for url in ("/api/traffic", "/api/alerts"):
            r = client.get(url, headers=user)
            slowest = max(slowest, float(r.headers["X-Response-Time-ms"]))
    assert slowest < TARGET_MS
