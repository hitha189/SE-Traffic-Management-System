import os
import sqlite3
import time
from contextlib import contextmanager
from functools import wraps
from flask import Flask, g, request, jsonify, send_from_directory
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash, check_password_hash

import alerts
import audit
import emergency
import incidents
import notifications
import routing
import signals
import storage
import traffic
from validation import clean_str, is_vehicle_id, parse_int

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "TMS_SECRET_KEY", "change-this-secret-for-demo")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # reject oversized requests
DB = "tms.db"
# NFR-02: the SRS gives no number, so the project target is 1 second.
RESPONSE_TIME_TARGET_MS = 1000
TOKEN_MAX_AGE = 3600  # token valid for 1 hour

MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 300  # 5 minutes
FAILED_LOGINS = {}  # username -> (failed count, time of first failure)


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session():
    """One transaction per request: commit on success, roll back on any
    error, always close. Keeps an action and its audit entry together
    (NFR-05, NFR-09)."""
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def json_body():
    """The request JSON as a dict; anything else becomes an empty dict."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def current_user():
    return read_token()["username"]


def init_db():
    conn = get_db()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )"""
    )
    conn.commit()
    traffic.init_traffic(conn)
    incidents.init_incidents(conn)
    storage.init_storage(conn)
    signals.init_signals(conn)
    audit.init_audit(conn)
    alerts.init_alerts(conn)
    notifications.init_notifications(conn)
    emergency.init_emergency(conn)
    conn.close()


def make_token(username, role):
    s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    return s.dumps({"username": username, "role": role})


def read_token():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    try:
        return s.loads(header[7:], max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def require_role(*roles):
    """Allow only logged-in users whose role is in `roles`."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = read_token()
            if user is None:
                return jsonify({"error": "Authentication required"}), 401
            if user["role"] not in roles:
                return jsonify({"error": "Access denied"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def is_locked(username):
    entry = FAILED_LOGINS.get(username)
    if not entry:
        return False
    count, first = entry
    if time.time() - first > LOCKOUT_SECONDS:
        FAILED_LOGINS.pop(username, None)
        return False
    return count >= MAX_FAILED_LOGINS


def record_failure(username):
    now = time.time()
    count, first = FAILED_LOGINS.get(username, (0, now))
    if now - first > LOCKOUT_SECONDS:
        count, first = 0, now
    FAILED_LOGINS[username] = (count + 1, first)


@app.before_request
def start_timer():
    g.start = time.perf_counter()


@app.errorhandler(HTTPException)
def handle_http_error(e):
    """Return JSON, not an HTML page, for 404, 405, 413 and similar."""
    return jsonify({"error": e.description}), e.code


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    """Never leak internals; the open transaction has already rolled back."""
    app.logger.exception("Unhandled error")
    return jsonify({"error": "Something went wrong. Please try again."}), 500


@app.after_request
def add_security_headers(response):
    start = g.get("start")
    if start is not None:
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time-ms"] = "%.1f" % elapsed_ms
        if elapsed_ms > RESPONSE_TIME_TARGET_MS:
            app.logger.warning("Slow request %s took %.0f ms",
                               request.path, elapsed_ms)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/")
def home():
    return send_from_directory("static", "index.html")


@app.route("/api/register", methods=["POST"])
def register():
    data = json_body()
    username = clean_str(data.get("username"), 50)
    email = clean_str(data.get("email"), 100)
    password = data.get("password")
    password = password if isinstance(password, str) else ""

    if not username or not email or len(password) < 6 or "@" not in email:
        return jsonify({"error": "Invalid or missing details"}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, generate_password_hash(password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 409
    finally:
        conn.close()

    return jsonify({"message": "Account created"}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = json_body()
    username = clean_str(data.get("username"), 50)
    password = data.get("password")
    password = password if isinstance(password, str) else ""

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if is_locked(username):
        return jsonify({
            "error": "Too many failed attempts. Try again in a few minutes."
        }), 429

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        record_failure(username)
        return jsonify({"error": "Invalid credentials"}), 401

    FAILED_LOGINS.pop(username, None)
    token = make_token(user["username"], user["role"])
    return jsonify({
        "message": "Login successful",
        "role": user["role"],
        "token": token,
    }), 200


@app.route("/api/admin/ping", methods=["GET"])
@require_role("admin")
def admin_ping():
    return jsonify({"message": "Admin access granted"}), 200


@app.route("/api/admin/summary", methods=["GET"])
@require_role("admin")
def admin_summary():
    conn = get_db()
    counts = storage.summary(conn)
    conn.close()
    return jsonify({"records": counts}), 200


@app.route("/api/emergency/ping", methods=["GET"])
@require_role("emergency", "admin")
def emergency_ping():
    return jsonify({"message": "Emergency access granted"}), 200


@app.route("/api/traffic", methods=["GET"])
@require_role("user", "admin", "emergency")
def get_traffic():
    with db_session() as conn:
        traffic.refresh_simulated(conn)
        roads = traffic.list_roads(conn)
        alerts.sync_congestion_alerts(conn, roads)
    return jsonify({"roads": roads}), 200


@app.route("/api/incidents", methods=["POST"])
@require_role("user", "admin", "emergency")
def report_incident():
    data = json_body()
    incident_type = clean_str(data.get("type"))
    location = clean_str(data.get("location"), 100)
    description = clean_str(data.get("description"), 500)

    if (incident_type not in incidents.INCIDENT_TYPES
            or not location or not description):
        return jsonify({"error": "Invalid or missing incident details"}), 400

    username = current_user()
    with db_session() as conn:
        new_id = incidents.add_incident(
            conn, incident_type, location, description, username,
            commit=False)
        audit.log_action(conn, username, "incident_reported",
                         "incident:%d" % new_id,
                         "%s at %s" % (incident_type, location))
        alerts.sync_incident_alert(
            conn, incidents.get_incident(conn, new_id), actor=username)
    return jsonify({"message": "Incident reported", "id": new_id}), 201


@app.route("/api/incidents", methods=["GET"])
@require_role("user", "admin", "emergency")
def get_incidents():
    conn = get_db()
    items = incidents.list_incidents(conn)
    conn.close()
    return jsonify({"incidents": items}), 200


@app.route("/api/places", methods=["GET"])
@require_role("user", "admin", "emergency")
def get_places():
    return jsonify({"places": routing.known_places()}), 200


@app.route("/api/route", methods=["GET"])
@require_role("user", "admin", "emergency")
def get_route():
    source = (request.args.get("source") or "").strip()
    destination = (request.args.get("destination") or "").strip()

    if not source or not destination or source == destination:
        return jsonify({"error": "Enter a valid source and destination"}), 400

    conn = get_db()
    roads = traffic.list_roads(conn)
    density = {r["name"]: r["density"] for r in roads}

    route = routing.find_route(source, destination, density)
    if route is None:
        conn.close()
        return jsonify({"error": "No route found for these locations"}), 404

    storage.save_route(conn, read_token()["username"], source, destination, route)
    conn.close()
    return jsonify(route), 200


@app.route("/api/routes/history", methods=["GET"])
@require_role("user", "admin", "emergency")
def route_history():
    conn = get_db()
    items = storage.list_routes(conn, read_token()["username"])
    conn.close()
    return jsonify({"routes": items}), 200


# =============================================================================
# Sprint 2
# =============================================================================

# ---- Signals (FR-06, FR-07) ---------------------------------------------------
@app.route("/api/signals", methods=["GET"])
@require_role("admin")
def get_signals():
    conn = get_db()
    items = signals.list_signals(conn)
    conn.close()
    return jsonify({"signals": items, "states": signals.SIGNAL_STATES}), 200


@app.route("/api/signals/<int:signal_id>", methods=["PUT"])
@require_role("admin")
def change_signal(signal_id):
    new_state = clean_str(json_body().get("state"))
    if new_state not in signals.SIGNAL_STATES:
        return jsonify({"error": "State must be one of: " +
                        ", ".join(signals.SIGNAL_STATES)}), 400

    actor = current_user()
    with db_session() as conn:
        signal = signals.get_signal(conn, signal_id)
        if signal is None:
            return jsonify({"error": "Signal not found"}), 404
        if signal["state"] == new_state:
            return jsonify({"error": "Signal is already " + new_state}), 400
        old = signals.set_state(conn, signal_id, new_state, actor)
        audit.log_action(conn, actor, "signal_change",
                         "signal:%d" % signal_id,
                         "%s: %s -> %s" % (signal["location"], old,
                                           new_state))
        updated = signals.get_signal(conn, signal_id)
    return jsonify({"signal": updated}), 200


# ---- Incident management (FR-09) ----------------------------------------------
@app.route("/api/incidents/<int:incident_id>", methods=["PATCH"])
@require_role("admin")
def manage_incident(incident_id):
    data = json_body()
    action = clean_str(data.get("action"))
    if action not in ("verify", "update", "close"):
        return jsonify({"error": "Action must be verify, update or close"}), 400

    fields = {}
    if action == "update":
        if "type" in data:
            value = clean_str(data.get("type"))
            if value not in incidents.INCIDENT_TYPES:
                return jsonify({"error": "Invalid incident type"}), 400
            fields["type"] = value
        if "location" in data:
            value = clean_str(data.get("location"), 100)
            if not value:
                return jsonify({"error": "Invalid location"}), 400
            fields["location"] = value
        if "description" in data:
            value = clean_str(data.get("description"), 500)
            if not value:
                return jsonify({"error": "Invalid description"}), 400
            fields["description"] = value
        if not fields:
            return jsonify({"error": "Nothing to update"}), 400

    actor = current_user()
    target = "incident:%d" % incident_id
    with db_session() as conn:
        incident = incidents.get_incident(conn, incident_id)
        if incident is None:
            return jsonify({"error": "Incident not found"}), 404
        if incident["status"] == "Closed":
            return jsonify({"error": "A closed incident cannot be changed"}), 409

        if action == "verify":
            if incident["status"] != "Reported":
                return jsonify({"error": "Incident is already verified"}), 409
            incidents.set_status(conn, incident_id, "Verified")
            audit.log_action(conn, actor, "incident_verified", target)
        elif action == "close":
            incidents.set_status(conn, incident_id, "Closed")
            note = clean_str(data.get("note"), 200)
            audit.log_action(conn, actor, "incident_closed", target, note)
        else:
            changes = ", ".join(
                "%s: %r -> %r" % (k, incident[k], v) for k, v in fields.items()
                if incident[k] != v)
            incidents.update_fields(conn, incident_id, fields)
            audit.log_action(conn, actor, "incident_updated", target,
                             changes or "no change")

        updated = incidents.get_incident(conn, incident_id)
        alerts.sync_incident_alert(conn, updated, actor=actor)
    return jsonify({"incident": updated}), 200


# ---- Alerts and notifications (FR-10, FR-11) ------------------------------------
@app.route("/api/alerts", methods=["GET"])
@require_role("user", "admin", "emergency")
def get_alerts():
    conn = get_db()
    items = alerts.list_alerts(conn)
    conn.close()
    return jsonify({"alerts": items}), 200


@app.route("/api/subscriptions", methods=["GET"])
@require_role("user", "admin", "emergency")
def get_subscriptions():
    conn = get_db()
    areas = notifications.get_subscriptions(conn, current_user())
    conn.close()
    return jsonify({"areas": areas, "available": routing.known_places()}), 200


@app.route("/api/subscriptions", methods=["PUT"])
@require_role("user", "admin", "emergency")
def set_subscriptions():
    areas = json_body().get("areas")
    known = set(routing.known_places())
    if (not isinstance(areas, list) or len(areas) > len(known)
            or any(not isinstance(a, str) or a not in known for a in areas)):
        return jsonify({"error": "Choose areas from the list"}), 400
    with db_session() as conn:
        notifications.set_subscriptions(conn, current_user(), areas)
    return jsonify({"areas": sorted(set(areas))}), 200


@app.route("/api/notifications", methods=["GET"])
@require_role("user", "admin", "emergency")
def get_notifications():
    conn = get_db()
    items = notifications.list_notifications(conn, current_user())
    conn.close()
    return jsonify({"notifications": items}), 200


@app.route("/api/notifications/<int:notification_id>/read", methods=["POST"])
@require_role("user", "admin", "emergency")
def read_notification(notification_id):
    with db_session() as conn:
        changed = notifications.mark_read(
            conn, current_user(), notification_id)
    if not changed:
        return jsonify({"error": "Notification not found"}), 404
    return jsonify({"message": "Marked as read"}), 200


# ---- Emergency priority and routing (FR-14, FR-15) ------------------------------
def _valid_places(source, destination):
    known = set(routing.known_places())
    return (source in known and destination in known
            and source != destination)


@app.route("/api/emergency/route", methods=["GET"])
@require_role("emergency", "admin")
def emergency_route():
    source = clean_str(request.args.get("source"))
    destination = clean_str(request.args.get("destination"))
    if not _valid_places(source, destination):
        return jsonify({"error": "Enter a valid source and destination"}), 400
    conn = get_db()
    route = emergency.plan_route(conn, source, destination)
    conn.close()
    if route is None:
        return jsonify({"error": "No route found for these locations"}), 404
    return jsonify(route), 200


@app.route("/api/emergency/priority", methods=["POST"])
@require_role("emergency")
def emergency_priority():
    data = json_body()
    vehicle_id = data.get("vehicle_id")
    source = clean_str(data.get("source"))
    destination = clean_str(data.get("destination"))
    if not is_vehicle_id(vehicle_id):
        return jsonify({"error": "Vehicle ID must be 3-20 letters, "
                        "digits or dashes"}), 400
    if not _valid_places(source, destination):
        return jsonify({"error": "Enter a valid source and destination"}), 400

    username = current_user()
    with db_session() as conn:
        route = emergency.plan_route(conn, source, destination)
        if route is None:
            return jsonify({"error": "No route found for these locations"}), 404
        request_id, cleared = emergency.create_request(
            conn, username, vehicle_id, source, destination, route)
    return jsonify({
        "message": "Priority granted",
        "request_id": request_id,
        "route": route,
        "signals_cleared": cleared,
    }), 201


@app.route("/api/emergency/requests", methods=["GET"])
@require_role("emergency", "admin")
def emergency_requests():
    user = read_token()
    conn = get_db()
    items = emergency.list_requests(
        conn, None if user["role"] == "admin" else user["username"])
    conn.close()
    for item in items:
        item.pop("previous_states", None)
    return jsonify({"requests": items}), 200


@app.route("/api/emergency/requests/<int:request_id>/complete",
           methods=["POST"])
@require_role("emergency", "admin")
def complete_emergency_request(request_id):
    user = read_token()
    with db_session() as conn:
        row = emergency.get_request(conn, request_id)
        if row is None:
            return jsonify({"error": "Request not found"}), 404
        if user["role"] != "admin" and row["username"] != user["username"]:
            return jsonify({"error": "Access denied"}), 403
        if row["status"] != "Active":
            return jsonify({"error": "Request is already completed"}), 409
        restored = emergency.complete_request(conn, row, user["username"])
    return jsonify({"message": "Priority ended",
                    "signals_restored": restored}), 200


# ---- Audit log (FR-20, NFR-12) ---------------------------------------------------
@app.route("/api/admin/audit", methods=["GET"])
@require_role("admin")
def get_audit_log():
    raw_limit = request.args.get("limit")
    limit = 100 if raw_limit is None else parse_int(raw_limit, 1, 500)
    if limit is None:
        return jsonify({"error": "limit must be a number from 1 to 500"}), 400
    conn = get_db()
    items = audit.list_logs(
        conn,
        action=clean_str(request.args.get("action")) or None,
        actor=clean_str(request.args.get("actor")) or None,
        limit=limit)
    conn.close()
    return jsonify({"entries": items}), 200


if __name__ == "__main__":
    init_db()
    app.run(debug=True)