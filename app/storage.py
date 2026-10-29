import json

COUNTED_TABLES = ["users", "roads", "incidents", "routes", "signals",
                  "alerts", "notifications", "emergency_requests",
                  "audit_log", "parking_areas", "reports",
                  "traffic_history"]


def init_storage(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            path TEXT NOT NULL,
            distance_km REAL NOT NULL,
            eta_minutes INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_routes_user "
                 "ON routes (username, id)")
    conn.commit()


def purge_old_routes(conn, days):
    """Delete route history older than `days` days (NFR-10: location data is
    not kept longer than needed). Does not commit. Returns rows deleted."""
    cur = conn.execute(
        "DELETE FROM routes WHERE created_at < datetime('now', ?)",
        ("-%d days" % days,))
    return cur.rowcount


def save_route(conn, username, source, destination, route):
    conn.execute(
        "INSERT INTO routes (username, source, destination, path, "
        "distance_km, eta_minutes) VALUES (?, ?, ?, ?, ?, ?)",
        (username, source, destination, json.dumps(route["path"]),
         route["distance_km"], route["eta_minutes"]),
    )
    conn.commit()


def list_routes(conn, username):
    rows = conn.execute(
        "SELECT id, source, destination, path, distance_km, eta_minutes, "
        "created_at FROM routes WHERE username = ? ORDER BY id DESC LIMIT 50",
        (username,),
    ).fetchall()
    items = []
    for r in rows:
        item = dict(r)
        item["path"] = json.loads(item["path"])
        items.append(item)
    return items


def summary(conn):
    counts = {}
    for table in COUNTED_TABLES:
        counts[table] = conn.execute(
            "SELECT COUNT(*) FROM " + table).fetchone()[0]
    return counts