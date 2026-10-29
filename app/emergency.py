"""Emergency vehicle priority (FR-14) and emergency routing (FR-15).

An emergency vehicle requests priority between two places. The system plans
its optimised route and turns the signals along that route green, remembering
their previous states so they can be restored when the request is completed.
"""
import json

import audit
import routing
import signals
import traffic


def init_emergency(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS emergency_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            vehicle_id TEXT NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            path TEXT NOT NULL,
            eta_minutes INTEGER NOT NULL,
            previous_states TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'Active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        )"""
    )
    conn.commit()


def blocked_places(conn):
    """Places with an open (not Closed) roadblock incident."""
    known = set(routing.known_places(conn))
    rows = conn.execute(
        "SELECT location FROM incidents WHERE type = 'Roadblock' "
        "AND status != 'Closed'").fetchall()
    return {r["location"] for r in rows if r["location"] in known}


def plan_route(conn, source, destination):
    roads = traffic.list_roads(conn)
    density = {r["name"]: r["density"] for r in roads}
    return routing.find_emergency_route(
        source, destination, density, blocked=blocked_places(conn),
        graph=routing.build_graph(conn))


def create_request(conn, username, vehicle_id, source, destination, route):
    """Grant priority: green the signals on the path. Does not commit."""
    previous = {}
    for place in route["path"]:
        sig = signals.get_signal_by_location(conn, place)
        if sig and sig["state"] != "Green":
            previous[str(sig["id"])] = sig["state"]
            signals.set_state(conn, sig["id"], "Green", username)
            audit.log_action(
                conn, username, "signal_change", "signal:%d" % sig["id"],
                "%s: %s -> Green (emergency priority)" % (
                    sig["location"], sig["state"]))
    cur = conn.execute(
        "INSERT INTO emergency_requests (username, vehicle_id, source, "
        "destination, path, eta_minutes, previous_states) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (username, vehicle_id, source, destination,
         json.dumps(route["path"]), route["eta_minutes"],
         json.dumps(previous)))
    request_id = cur.lastrowid
    audit.log_action(
        conn, username, "emergency_priority_request",
        "emergency_request:%d" % request_id,
        "%s: %s -> %s via %s" % (vehicle_id, source, destination,
                                 " > ".join(route["path"])))
    return request_id, sorted(
        signals.get_signal(conn, int(i))["location"] for i in previous)


def _row_to_dict(row):
    item = dict(row)
    item["path"] = json.loads(item["path"])
    item.pop("previous_states", None)
    return item


def get_request(conn, request_id):
    return conn.execute(
        "SELECT * FROM emergency_requests WHERE id = ?",
        (request_id,)).fetchone()


def list_requests(conn, username=None):
    query = ("SELECT id, username, vehicle_id, source, destination, path, "
             "eta_minutes, status, created_at, completed_at, "
             "previous_states FROM emergency_requests")
    params = []
    if username:
        query += " WHERE username = ?"
        params.append(username)
    query += " ORDER BY id DESC LIMIT 50"
    return [_row_to_dict(r) for r in conn.execute(query, params).fetchall()]


def complete_request(conn, row, actor):
    """Finish a request and restore signals still held at Green by it.
    Does not commit."""
    previous = json.loads(row["previous_states"])
    restored = []
    for signal_id, old_state in previous.items():
        sig = signals.get_signal(conn, int(signal_id))
        if sig and sig["state"] == "Green":
            signals.set_state(conn, sig["id"], old_state, actor)
            audit.log_action(
                conn, actor, "signal_change", "signal:%d" % sig["id"],
                "%s: Green -> %s (emergency priority ended)" % (
                    sig["location"], old_state))
            restored.append(sig["location"])
    conn.execute(
        "UPDATE emergency_requests SET status = 'Completed', "
        "completed_at = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
    audit.log_action(conn, actor, "emergency_request_completed",
                     "emergency_request:%d" % row["id"],
                     "restored: " + (", ".join(restored) or "none"))
    return restored
