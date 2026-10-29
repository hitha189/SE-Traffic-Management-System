"""Availability and data-consistency routes (NFR-03, NFR-09)."""
from flask import Blueprint, jsonify

import consistency
import health


def create_blueprint(deps):
    bp = Blueprint("health", __name__)
    admin = deps.require_role("admin")

    @bp.route("/api/health", methods=["GET"])
    def health_check():
        """Public, no login: for uptime monitors and load balancers."""
        ok = health.database_ok(deps.get_db)
        body = {
            "status": "ok" if ok else "degraded",
            "database": "ok" if ok else "unavailable",
            "uptime_seconds": health.snapshot()["uptime_seconds"],
        }
        return jsonify(body), 200 if ok else 503

    @bp.route("/api/admin/status", methods=["GET"])
    @admin
    def status():
        body = health.snapshot()
        body["database"] = ("ok" if health.database_ok(deps.get_db)
                            else "unavailable")
        return jsonify(body), 200

    @bp.route("/api/admin/consistency", methods=["GET"])
    @admin
    def consistency_check():
        conn = deps.get_db()
        try:
            result = consistency.check(conn)
        finally:
            conn.close()
        return jsonify(result), 200

    return bp
