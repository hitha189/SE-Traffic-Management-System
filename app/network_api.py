"""Add roads without changing code (NFR-06). Admin only."""
from flask import Blueprint, jsonify

import audit
import network


def create_blueprint(deps):
    bp = Blueprint("network", __name__)

    @bp.route("/api/admin/roads", methods=["POST"])
    @deps.require_role("admin")
    def add_road():
        data = deps.json_body()
        actor = deps.current_user()
        with deps.db_session() as conn:
            try:
                road = network.add_road(
                    conn, data.get("name"), data.get("lat"), data.get("lng"),
                    data.get("connects_to"))
            except network.Conflict as e:
                return jsonify({"error": str(e)}), 409
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            audit.log_action(
                conn, actor, "road_added", "road:%s" % road["name"],
                "linked to " + ", ".join(
                    "%s (%s km)" % (link["to"], link["km"])
                    for link in road["links"]))
        return jsonify({"road": road}), 201

    return bp
