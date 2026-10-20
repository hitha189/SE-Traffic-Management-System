import os
import sqlite3
import time
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash

import incidents
import routing
import storage
import traffic

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "TMS_SECRET_KEY", "change-this-secret-for-demo")
DB = "tms.db"
TOKEN_MAX_AGE = 3600  # token valid for 1 hour

MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 300  # 5 minutes
FAILED_LOGINS = {}  # username -> (failed count, time of first failure)


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


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


@app.after_request
def add_security_headers(response):
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
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

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
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

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
    conn = get_db()
    traffic.refresh_simulated(conn)
    roads = traffic.list_roads(conn)
    conn.close()
    return jsonify({"roads": roads}), 200


@app.route("/api/incidents", methods=["POST"])
@require_role("user", "admin", "emergency")
def report_incident():
    data = request.get_json(silent=True) or {}
    incident_type = (data.get("type") or "").strip()
    location = (data.get("location") or "").strip()
    description = (data.get("description") or "").strip()

    if (incident_type not in incidents.INCIDENT_TYPES
            or not location or not description
            or len(location) > 100 or len(description) > 500):
        return jsonify({"error": "Invalid or missing incident details"}), 400

    conn = get_db()
    new_id = incidents.add_incident(
        conn, incident_type, location, description, read_token()["username"])
    conn.close()
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


if __name__ == "__main__":
    init_db()
    app.run(debug=True)