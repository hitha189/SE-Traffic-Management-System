"""Personal data and location privacy (NFR-10).

What is collected, and why (nothing else is stored):
  users          username, email, password hash, role  (FR-01 account details)
  routes         place names of searched trips          (route history)
  subscriptions  area names the user follows            (FR-11)
  incidents      who reported what and where            (FR-08)

No phone number, home address or GPS position is ever collected. Locations in
the prototype are named areas, never coordinates of a person.
Users can download their data and delete their account.
"""
import storage

ERASED_NAME = "deleted-user"
ROUTE_RETENTION_DAYS = 30


def export_user_data(conn, username):
    """Everything stored about one user, never including the password hash."""
    user = conn.execute(
        "SELECT username, email, role FROM users WHERE username = ?",
        (username,)).fetchone()
    if user is None:
        return None
    incidents = conn.execute(
        "SELECT id, type, location, description, status, created_at "
        "FROM incidents WHERE reported_by = ? ORDER BY id", (username,)
    ).fetchall()
    subs = conn.execute(
        "SELECT area FROM subscriptions WHERE username = ? ORDER BY area",
        (username,)).fetchall()
    notes = conn.execute(
        "SELECT message, is_read, created_at FROM notifications "
        "WHERE username = ? ORDER BY id", (username,)).fetchall()
    return {
        "profile": dict(user),
        "subscribed_areas": [s["area"] for s in subs],
        "notifications": [dict(n) for n in notes],
        "route_history": storage.list_routes(conn, username),
        "incidents_reported": [dict(i) for i in incidents],
        "retention": {
            "route_history_days": ROUTE_RETENTION_DAYS,
            "note": "Older routes are deleted automatically.",
        },
    }


def erase_user(conn, username):
    """Delete the account and personal data. Incidents already reported stay
    (they matter to other drivers) but lose the reporter's name. Does not
    commit. The audit log keeps the username only, as the SRS requires
    traceability (NFR-12); it holds no email or route data."""
    conn.execute("DELETE FROM routes WHERE username = ?", (username,))
    conn.execute("DELETE FROM subscriptions WHERE username = ?", (username,))
    conn.execute("DELETE FROM notifications WHERE username = ?", (username,))
    conn.execute("DELETE FROM emergency_requests WHERE username = ?",
                 (username,))
    conn.execute("UPDATE incidents SET reported_by = ? WHERE reported_by = ?",
                 (ERASED_NAME, username))
    conn.execute("DELETE FROM users WHERE username = ?", (username,))
