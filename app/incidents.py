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
    conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_status "
                 "ON incidents (status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_location "
                 "ON incidents (location)")
    conn.commit()


def add_incident(conn, incident_type, location, description, reported_by,
                 commit=True):
    cur = conn.execute(
        "INSERT INTO incidents (type, location, description, reported_by) "
        "VALUES (?, ?, ?, ?)",
        (incident_type, location, description, reported_by),
    )
    if commit:
        conn.commit()
    return cur.lastrowid


LIST_LIMIT = 500  # newest incidents returned; keeps responses fast (NFR-06)


def list_incidents(conn, limit=LIST_LIMIT):
    rows = conn.execute(
        "SELECT id, type, location, description, reported_by, status, created_at "
        "FROM incidents ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]

# ---- Incident management (FR-09) -------------------------------------------
STATUSES = ["Reported", "Verified", "Closed"]


def get_incident(conn, incident_id):
    row = conn.execute(
        "SELECT id, type, location, description, reported_by, status, "
        "created_at FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    return dict(row) if row else None


def set_status(conn, incident_id, status):
    """Does not commit; the caller commits together with the audit entry."""
    conn.execute("UPDATE incidents SET status = ? WHERE id = ?",
                 (status, incident_id))


def update_fields(conn, incident_id, fields):
    """Update type / location / description. Does not commit."""
    for column in ("type", "location", "description"):
        if column in fields:
            conn.execute(
                "UPDATE incidents SET " + column + " = ? WHERE id = ?",
                (fields[column], incident_id))
