"""Audit logging (FR-20) and audit traceability (NFR-12).

The audit_log table is append-only: database triggers reject any UPDATE or
DELETE, so a recorded administrative action cannot be altered afterwards.
Each entry stores who did what, to which object, when (UTC), and details.
"""


def init_audit(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    conn.execute(
        """CREATE TRIGGER IF NOT EXISTS audit_no_update
        BEFORE UPDATE ON audit_log
        BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END"""
    )
    conn.execute(
        """CREATE TRIGGER IF NOT EXISTS audit_no_delete
        BEFORE DELETE ON audit_log
        BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END"""
    )
    conn.commit()


def log_action(conn, actor, action, target, details=""):
    """Add one entry. Does NOT commit: it joins the caller's transaction, so
    an action and its log entry are saved together or not at all (NFR-09)."""
    conn.execute(
        "INSERT INTO audit_log (actor, action, target, details) "
        "VALUES (?, ?, ?, ?)",
        (actor, action, target, details),
    )


def list_logs(conn, action=None, actor=None, limit=100):
    query = ("SELECT id, actor, action, target, details, created_at "
             "FROM audit_log")
    clauses, params = [], []
    if action:
        clauses.append("action = ?")
        params.append(action)
    if actor:
        clauses.append("actor = ?")
        params.append(actor)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(query, params).fetchall()]
