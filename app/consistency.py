"""Data consistency (NFR-09).

Two layers protect the records:

1. install_triggers(): the database itself refuses impossible values (a bad
   incident status, a signal colour that does not exist, a road whose
   congestion level disagrees with its density, a notification for an alert
   that does not exist, an edit to a closed incident ...). Triggers are used
   rather than table constraints so they also protect databases created by
   earlier sprints.

2. check(): scans every table for records that disagree with each other
   (an alert for a closed incident, a signal without a road, data left behind
   by a deleted user ...) and lists the problems. It reads only.
"""
import alerts
import incidents
import signals
import traffic

ROLES = ("user", "admin", "emergency")
EMERGENCY_STATUSES = ("Active", "Completed")


def _in(values):
    return ", ".join("'%s'" % v for v in values)


def _trigger(name, event, table, condition, message):
    return ("CREATE TRIGGER IF NOT EXISTS %s BEFORE %s ON %s WHEN %s "
            "BEGIN SELECT RAISE(ABORT, '%s'); END"
            % (name, event, table, condition, message))


def _statements():
    types = _in(incidents.INCIDENT_TYPES)
    statuses = _in(incidents.STATUSES)
    bad_incident = ("NEW.type NOT IN (%s) OR NEW.status NOT IN (%s)"
                    % (types, statuses))
    closed_frozen = (
        "OLD.status = 'Closed' AND (NEW.type IS NOT OLD.type OR "
        "NEW.location IS NOT OLD.location OR "
        "NEW.description IS NOT OLD.description OR "
        "NEW.status IS NOT OLD.status)")
    expected_level = (
        "CASE WHEN NEW.density < %d THEN 'Low' WHEN NEW.density < %d "
        "THEN 'Medium' ELSE 'High' END" % (traffic.LOW_MAX,
                                           traffic.MEDIUM_MAX))
    bad_road = ("NEW.density < 0 OR NEW.density > 100 OR "
                "NEW.congestion != " + expected_level)
    bad_signal = "NEW.state NOT IN (%s)" % _in(signals.SIGNAL_STATES)
    bad_role = "NEW.role NOT IN (%s)" % _in(ROLES)
    return [
        _trigger("incidents_valid_insert", "INSERT", "incidents",
                 bad_incident, "invalid incident record"),
        _trigger("incidents_valid_update", "UPDATE", "incidents",
                 "%s OR (OLD.status = 'Verified' AND NEW.status = 'Reported')"
                 " OR (%s)" % (bad_incident, closed_frozen),
                 "invalid incident change"),
        _trigger("signals_valid_insert", "INSERT", "signals", bad_signal,
                 "invalid signal state"),
        _trigger("signals_valid_update", "UPDATE", "signals", bad_signal,
                 "invalid signal state"),
        _trigger("roads_valid_insert", "INSERT", "roads", bad_road,
                 "road density and congestion do not agree"),
        _trigger("roads_valid_update", "UPDATE", "roads", bad_road,
                 "road density and congestion do not agree"),
        _trigger("users_valid_insert", "INSERT", "users", bad_role,
                 "invalid role"),
        _trigger("users_valid_update", "UPDATE", "users", bad_role,
                 "invalid role"),
        _trigger("alerts_valid_insert", "INSERT", "alerts",
                 "NEW.kind NOT IN (%s)" % _in(alerts.ALERT_KINDS),
                 "invalid alert kind"),
        _trigger("notifications_need_alert", "INSERT", "notifications",
                 "NOT EXISTS (SELECT 1 FROM alerts WHERE id = NEW.alert_id)",
                 "notification for an alert that does not exist"),
        _trigger("emergency_valid_insert", "INSERT", "emergency_requests",
                 "NEW.status NOT IN (%s)" % _in(EMERGENCY_STATUSES),
                 "invalid request status"),
        _trigger("emergency_valid_update", "UPDATE", "emergency_requests",
                 "NEW.status NOT IN (%s)" % _in(EMERGENCY_STATUSES),
                 "invalid request status"),
    ]


def install_triggers(conn):
    """Safe to run every start: each trigger is created once."""
    for statement in _statements():
        conn.execute(statement)
    conn.commit()


# ---- cross-table check ------------------------------------------------------
def _ids(conn, sql):
    return [r[0] for r in conn.execute(sql).fetchall()]


def _check_incident_alerts(conn, problems):
    for alert_id in _ids(conn, """
            SELECT a.id FROM alerts a
            LEFT JOIN incidents i ON CAST(a.source_id AS INTEGER) = i.id
            WHERE a.source_type = 'incident' AND a.active = 1
              AND (i.id IS NULL OR i.status = 'Closed')"""):
        problems.append("Alert %d is active but its incident is closed or "
                        "missing" % alert_id)
    for inc in conn.execute(
            "SELECT id, type, location FROM incidents "
            "WHERE status != 'Closed'").fetchall():
        kind = alerts.INCIDENT_ALERT_KIND.get(inc["type"])
        if kind is None:
            continue
        alert = conn.execute(
            "SELECT kind, location FROM alerts WHERE source_type = "
            "'incident' AND source_id = ? AND active = 1",
            (str(inc["id"]),)).fetchone()
        if alert is None:
            problems.append("Open incident %d has no active alert" % inc["id"])
        elif alert["kind"] != kind or alert["location"] != inc["location"]:
            problems.append("Alert for incident %d does not match the "
                            "incident" % inc["id"])


def _check_congestion_alerts(conn, problems):
    for road in conn.execute(
            "SELECT name, congestion FROM roads").fetchall():
        active = conn.execute(
            "SELECT 1 FROM alerts WHERE source_type = 'road' AND "
            "source_id = ? AND active = 1", (road["name"],)).fetchone()
        if road["congestion"] == "High" and not active:
            problems.append("%s is heavily congested but has no alert"
                            % road["name"])
        if road["congestion"] != "High" and active:
            problems.append("%s has a congestion alert but traffic is not "
                            "heavy" % road["name"])


def _check_roads_and_signals(conn, problems):
    for road in conn.execute(
            "SELECT name, density, congestion FROM roads").fetchall():
        expected = traffic.level_for_density(road["density"])
        if not 0 <= road["density"] <= 100 or road["congestion"] != expected:
            problems.append("Road %s: density %s does not match level %s"
                            % (road["name"], road["density"],
                               road["congestion"]))
    for loc in _ids(conn, "SELECT location FROM signals WHERE location NOT "
                          "IN (SELECT name FROM roads)"):
        problems.append("Signal at %s has no road" % loc)
    for name in _ids(conn, "SELECT name FROM roads WHERE name NOT IN "
                           "(SELECT location FROM signals)"):
        problems.append("Road %s has no signal" % name)


def _check_parking(conn, problems):
    for row in conn.execute(
            "SELECT name, capacity, available, location FROM "
            "parking_areas").fetchall():
        if not 0 <= row["available"] <= row["capacity"]:
            problems.append("Parking %s: %d free of %d spaces" % (
                row["name"], row["available"], row["capacity"]))
        if conn.execute("SELECT 1 FROM roads WHERE name = ?",
                        (row["location"],)).fetchone() is None:
            problems.append("Parking %s is on an unknown road"
                            % row["name"])


def _check_users_and_orphans(conn, problems):
    for name in _ids(conn, "SELECT username FROM users WHERE role NOT IN "
                           "(%s)" % _in(ROLES)):
        problems.append("User %s has an invalid role" % name)
    for table in ("routes", "subscriptions", "notifications",
                  "emergency_requests"):
        n = conn.execute(
            "SELECT COUNT(*) FROM %s WHERE username NOT IN "
            "(SELECT username FROM users)" % table).fetchone()[0]
        if n:
            problems.append("%d record(s) in %s belong to a user who no "
                            "longer exists" % (n, table))
    n = conn.execute("SELECT COUNT(*) FROM notifications WHERE alert_id NOT "
                     "IN (SELECT id FROM alerts)").fetchone()[0]
    if n:
        problems.append("%d notification(s) point to a missing alert" % n)


def _check_audit(conn, problems):
    for alert_id in _ids(conn, """
            SELECT id FROM alerts WHERE 'alert:' || id NOT IN
            (SELECT target FROM audit_log WHERE action = 'alert_created')"""):
        problems.append("Alert %d was created but not logged" % alert_id)


CHECKS = [
    _check_incident_alerts, _check_congestion_alerts,
    _check_roads_and_signals, _check_parking, _check_users_and_orphans,
    _check_audit,
]


def check(conn):
    problems = []
    for check_fn in CHECKS:
        check_fn(conn, problems)
    return {"consistent": not problems, "checks_run": len(CHECKS),
            "problems": problems}
