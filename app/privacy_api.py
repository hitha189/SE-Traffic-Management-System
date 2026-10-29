"""Personal-data routes (NFR-10): download my data, delete my account."""
from flask import Blueprint, jsonify

import audit
import privacy


def create_blueprint(deps):
    bp = Blueprint("privacy", __name__)
    everyone = deps.require_role("user", "admin", "emergency")

    @bp.route("/api/me/export", methods=["GET"])
    @everyone
    def export_my_data():
        conn = deps.get_db()
        try:
            data = privacy.export_user_data(conn, deps.current_user())
        finally:
            conn.close()
        return jsonify(data), 200

    @bp.route("/api/me", methods=["DELETE"])
    @everyone
    def delete_my_account():
        username = deps.current_user()
        password = deps.json_body().get("password")
        with deps.db_session() as conn:
            row = conn.execute(
                "SELECT password_hash, role FROM users WHERE username = ?",
                (username,)).fetchone()
            if row["role"] == "admin":
                return jsonify({"error": "Admin accounts cannot be deleted "
                                "here; ask another admin"}), 403
            if (not isinstance(password, str)
                    or not deps.check_password_hash(row["password_hash"],
                                                    password)):
                return jsonify({"error": "Password is incorrect"}), 403
            audit.log_action(conn, username, "account_deleted",
                             "user:%s" % username,
                             "account and personal data removed by owner")
            privacy.erase_user(conn, username)
        return jsonify({"message": "Account and personal data deleted"}), 200

    return bp
