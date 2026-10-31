"""Web routes for the Dashboard subsystem.

    GET  /dashboard/               the dashboard page
    GET  /dashboard/api/stats      current statistics as JSON (also saved as a snapshot)
    GET  /dashboard/api/settings   current settings
    POST /dashboard/api/settings   change settings, e.g. {"use_mock_data": false}
"""

from flask import Blueprint, jsonify, render_template, request

from app.extensions import db
from app.models.dashboard import DashboardSetting
from app.subsystems.dashboard.services import build_snapshot

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def dashboard_page():
    return render_template("dashboard/dashboard.html")


@dashboard_bp.route("/api/stats")
def api_stats():
    return jsonify(build_snapshot().to_dict())


@dashboard_bp.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    setting = DashboardSetting.get_or_create()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        try:
            if "use_mock_data" in data:
                setting.set_use_mock_data(data["use_mock_data"])
            if "time_range_days" in data:
                setting.set_time_range_days(data["time_range_days"])
        except ValueError as error:
            db.session.rollback()
            return jsonify({"error": str(error)}), 400
        db.session.commit()
    return jsonify(setting.to_dict())
