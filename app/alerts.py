"""Traffic alerts (FR-10).

Alerts are generated for four kinds of event: Congestion, Accident, Closure
(a reported roadblock) and Hazard. Each alert is tied to its source (a road
or an incident) so it can be cleared when the event is over, and so the same
event never produces duplicate active alerts.
"""
import audit
import notifications

ALERT_KINDS = ["Congestion", "Accident", "Closure", "Hazard"]

# Incident type -> alert kind. "Other" does not raise an alert.
INCIDENT_ALERT_KIND = {
    "Accident": "Accident",
    "Roadblock": "Closure",
    "Hazard": "Hazard",
}


def init_alerts(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            location TEXT NOT NULL,
            message TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            cleared_at TEXT
        )"""
    )
    conn.commit()


def _active_for_source(conn, source_type, source_id):
    row = conn.execute(
        "SELECT id, kind, location FROM alerts WHERE source_type = ? "
        "AND source_id = ? AND active = 1", (source_type, str(source_id))
    ).fetchone()
    return dict(row) if row else None


def create_alert(conn, kind, location, message, source_type, source_id,
                 actor="system"):
    """Create an alert, log it (FR-20) and notify nearby subscribers (FR-11).
    Does not commit. Returns the new id, or None if an identical alert for
    this source is already active."""
    existing = _active_for_source(conn, source_type, source_id)
    if existing and existing["kind"] == kind \
            and existing["location"] == location:
        return None
    cur = conn.execute(
        "INSERT INTO alerts (kind, location, message, source_type, "
        "source_id) VALUES (?, ?, ?, ?, ?)",
        (kind, location, message, source_type, str(source_id)))
    alert_id = cur.lastrowid
    audit.log_action(conn, actor, "alert_created", "alert:%d" % alert_id,
                     "%s at %s: %s" % (kind, location, message))
    notifications.notify_for_alert(
        conn, alert_id, location, "%s alert at %s: %s" % (kind, location,
                                                           message))
    return alert_id


def clear_alerts_for_source(conn, source_type, source_id):
    """Mark the source's active alerts as cleared. Does not commit."""
    conn.execute(
        "UPDATE alerts SET active = 0, cleared_at = CURRENT_TIMESTAMP "
        "WHERE source_type = ? AND source_id = ? AND active = 1",
        (source_type, str(source_id)))


def sync_incident_alert(conn, incident, actor="system"):
    """Make the alerts match the incident's current state."""
    kind = INCIDENT_ALERT_KIND.get(incident["type"])
    if incident["status"] == "Closed" or kind is None:
        clear_alerts_for_source(conn, "incident", incident["id"])
        return None
    existing = _active_for_source(conn, "incident", incident["id"])
    if existing and (existing["kind"] != kind
                     or existing["location"] != incident["location"]):
        clear_alerts_for_source(conn, "incident", incident["id"])
    return create_alert(conn, kind, incident["location"],
                        incident["description"], "incident", incident["id"],
                        actor)


def sync_congestion_alerts(conn, roads):
    """Raise an alert for each road at High congestion and clear alerts for
    roads that have recovered. Does not commit."""
    created = []
    for road in roads:
        if road["congestion"] == "High":
            alert_id = create_alert(
                conn, "Congestion", road["name"],
                "Heavy traffic (%d%% density)" % road["density"],
                "road", road["name"])
            if alert_id:
                created.append(alert_id)
        else:
            clear_alerts_for_source(conn, "road", road["name"])
    return created


def list_alerts(conn, active_only=True):
    query = ("SELECT id, kind, location, message, active, created_at, "
             "cleared_at FROM alerts")
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY id DESC LIMIT 100"
    return [dict(r) for r in conn.execute(query).fetchall()]
