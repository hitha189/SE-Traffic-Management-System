"""Parking routes (FR-16). A self-contained feature module (NFR-07):
it receives what it needs in `deps` and never imports app.py."""
from flask import Blueprint, jsonify, request

import audit
import datasources
import parking
from validation import clean_str


def create_blueprint(deps):
    bp = Blueprint("parking", __name__)
    everyone = deps.require_role("user", "admin", "emergency")
    admin = deps.require_role("admin")

    @bp.route("/api/parking", methods=["GET"])
    @everyone
    def list_parking():
        location = clean_str(request.args.get("location")) or None
        with deps.db_session() as conn:
            datasources.refresh(conn, "parking")
            areas = parking.list_areas(conn, location)
            summary = parking.summary(conn)
        return jsonify({"parking": areas, "summary": summary}), 200

    @bp.route("/api/admin/parking", methods=["POST"])
    @admin
    def add_parking():
        data = deps.json_body()
        actor = deps.current_user()
        with deps.db_session() as conn:
            try:
                new_id = parking.add_area(conn, data.get("name"),
                                          data.get("location"),
                                          data.get("capacity"))
            except parking.Conflict as e:
                return jsonify({"error": str(e)}), 409
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            audit.log_action(
                conn, actor, "parking_added", "parking:%d" % new_id,
                "%s at %s, capacity %d" % (data["name"].strip(),
                                           data["location"],
                                           data["capacity"]))
            area = next(a for a in parking.list_areas(conn)
                        if a["id"] == new_id)
        return jsonify({"parking_area": area}), 201

    return bp
