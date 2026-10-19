import sqlite3
from functools import wraps
from flask import Flask, request, jsonify
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-for-demo"
DB = "tms.db"
TOKEN_MAX_AGE = 3600  # token valid for 1 hour


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

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

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


@app.route("/api/emergency/ping", methods=["GET"])
@require_role("emergency", "admin")
def emergency_ping():
    return jsonify({"message": "Emergency access granted"}), 200


if __name__ == "__main__":
    init_db()
    app.run(debug=True)