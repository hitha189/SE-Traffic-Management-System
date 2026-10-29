"""Analytics and report routes (FR-17, FR-18). Admin only."""
from flask import Blueprint, Response, jsonify, request

import analytics
import audit
import reports
from validation import clean_str


def create_blueprint(deps):
    bp = Blueprint("reporting", __name__)
    admin = deps.require_role("admin")

    @bp.route("/api/admin/analytics", methods=["GET"])
    @admin
    def get_analytics():
        conn = deps.get_db()
        try:
            result = analytics.analyze(conn)
        finally:
            conn.close()
        return jsonify(result), 200

    @bp.route("/api/admin/reports", methods=["POST"])
    @admin
    def create_report():
        data = deps.json_body()
        title = data.get("title")
        if title is not None and not isinstance(title, str):
            return jsonify({"error": "Title must be text"}), 400
        actor = deps.current_user()
        with deps.db_session() as conn:
            try:
                report = reports.generate(conn, actor, title)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            audit.log_action(conn, actor, "report_generated",
                             "report:%d" % report["id"], report["title"])
        return jsonify({"report": report}), 201

    @bp.route("/api/admin/reports", methods=["GET"])
    @admin
    def list_reports():
        conn = deps.get_db()
        try:
            items = reports.list_reports(conn)
        finally:
            conn.close()
        return jsonify({"reports": items}), 200

    @bp.route("/api/admin/reports/<int:report_id>", methods=["GET"])
    @admin
    def get_report(report_id):
        fmt = clean_str(request.args.get("format")) or "json"
        if fmt not in ("json", "text"):
            return jsonify({"error": "format must be json or text"}), 400
        conn = deps.get_db()
        try:
            report = reports.get_report(conn, report_id)
        finally:
            conn.close()
        if report is None:
            return jsonify({"error": "Report not found"}), 404
        if fmt == "text":
            return Response(
                reports.render_text(report), mimetype="text/plain",
                headers={"Content-Disposition":
                         'attachment; filename="report-%d.txt"' % report_id})
        return jsonify({"report": report}), 200

    return bp
