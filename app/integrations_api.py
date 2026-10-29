"""Data-source and sensor ingest routes (NFR-11)."""
import re

from flask import Blueprint, jsonify

import alerts
import audit
import datasources
import traffic
from validation import clean_str

SOURCE_ID = re.compile(r"^[A-Za-z0-9_-]{1,50}$")


def create_blueprint(deps):
    bp = Blueprint("integrations", __name__)
    admin = deps.require_role("admin")

    @bp.route("/api/admin/integrations", methods=["GET"])
    @admin
    def list_integrations():
        return jsonify({
            "sources": datasources.describe(),
            "ingest_types": datasources.ingest_kinds(),
            "planned": datasources.PLANNED,
        }), 200

    @bp.route("/api/admin/integrations/ingest", methods=["POST"])
    @admin
    def ingest():
        data = deps.json_body()
        source_id = clean_str(data.get("source_id"))
        kind = clean_str(data.get("type"))
        if not SOURCE_ID.match(source_id):
            return jsonify({"error": "source_id must be 1-50 letters, "
                            "digits, dashes or underscores"}), 400
        actor = deps.current_user()
        with deps.db_session() as conn:
            try:
                count = datasources.ingest(conn, kind, data.get("readings"))
            except ValueError as e:
                conn.rollback()  # all-or-nothing: no partial batch is kept
                return jsonify({"error": str(e)}), 400
            if kind == "traffic":
                traffic.prune_history(conn)
                alerts.sync_congestion_alerts(conn, traffic.list_roads(conn))
            audit.log_action(conn, actor, "data_ingested",
                             "source:%s" % source_id,
                             "%s: %d reading(s)" % (kind, count))
        return jsonify({"accepted": count, "type": kind}), 200

    return bp
