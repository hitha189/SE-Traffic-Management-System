"""Availability monitoring (NFR-03).

Counts every request and every server-side failure (5xx) so availability can
be measured, and checks that the database answers so an uptime monitor or load
balancer can ask "is the system up?" at any time without logging in.

Availability target: at least 99% of requests during normal operation finish
without a server error, and the system recovers by itself when the database
becomes reachable again (a new connection is opened for every request).
Outages of the network or hosting are outside the system's control.
"""
import threading
import time

AVAILABILITY_TARGET_PERCENT = 99.0

_lock = threading.Lock()
_started = time.time()
_counts = {"requests": 0, "server_errors": 0}


def record(status_code):
    with _lock:
        _counts["requests"] += 1
        if status_code >= 500:
            _counts["server_errors"] += 1


def reset():
    """For tests: start counting from zero."""
    global _started
    with _lock:
        _started = time.time()
        _counts["requests"] = 0
        _counts["server_errors"] = 0


def snapshot():
    with _lock:
        requests = _counts["requests"]
        errors = _counts["server_errors"]
        started = _started
    availability = 100.0 if requests == 0 else round(
        100 * (requests - errors) / requests, 2)
    return {
        "uptime_seconds": int(time.time() - started),
        "requests": requests,
        "server_errors": errors,
        "availability_percent": availability,
        "target_percent": AVAILABILITY_TARGET_PERCENT,
        "meets_target": availability >= AVAILABILITY_TARGET_PERCENT,
    }


def database_ok(get_db):
    """True if the database can be opened and answers a query."""
    try:
        conn = get_db()
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()
        return True
    except Exception:
        return False
