INCIDENT_TYPES = ["Accident", "Roadblock", "Hazard", "Other"]


def init_incidents(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            reported_by TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Reported',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    conn.commit()


def add_incident(conn, incident_type, location, description, reported_by):
    cur = conn.execute(
        "INSERT INTO incidents (type, location, description, reported_by) "
        "VALUES (?, ?, ?, ?)",
        (incident_type, location, description, reported_by),
    )
    conn.commit()
    return cur.lastrowid


def list_incidents(conn):
    rows = conn.execute(
        "SELECT id, type, location, description, reported_by, status, created_at "
        "FROM incidents ORDER BY id DESC"
    ).fetchall()
    return [dict(r) for r in rows]