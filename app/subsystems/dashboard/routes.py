"""Web routes for the Dashboard subsystem.

    GET  /dashboard/               the dashboard page
    GET  /dashboard/api/stats      current statistics as JSON (also saved as a snapshot); optional ?days=1..365
    GET  /dashboard/api/settings   current settings
    POST /dashboard/api/settings   change settings, e.g. {"use_mock_data": false}

Every error goes through DashboardErrorHandler (app/subsystems/dashboard/errors.py)
and comes back as JSON: {"error": "...", "type": "..."} with a matching status code.
"""

from flask import Blueprint, jsonify, render_template, request

from app.extensions import db
from app.models.dashboard import DashboardSetting
from app.subsystems.dashboard.errors import DashboardErrorHandler, InvalidSettingError
from app.subsystems.dashboard.services import build_snapshot, parse_days

dashboard_bp = Blueprint("dashboard", __name__)
error_handler = DashboardErrorHandler()
error_handler.register(dashboard_bp)  # safety net for anything a route doesn't catch itself

ALLOWED_SETTINGS = {"use_mock_data", "time_range_days"}


@dashboard_bp.route("/")
def dashboard_page():
    return render_template("dashboard/dashboard.html")


@dashboard_bp.route("/api/stats")
def api_stats():
    try:
        days = parse_days(request.args.get("days"))
        snapshot = build_snapshot(days=days)
    except Exception as error:
        return error_handler.response(error)
    return jsonify(snapshot.to_dict())


@dashboard_bp.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    try:
        setting = DashboardSetting.get_or_create()
        if request.method == "POST":
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                raise InvalidSettingError("Send the settings as a JSON object.")
            unknown = set(data) - ALLOWED_SETTINGS
            if unknown:
                raise InvalidSettingError(f"Unknown setting: {', '.join(sorted(unknown))}.",
                                          field=sorted(unknown)[0])
            if "use_mock_data" in data:
                setting.set_use_mock_data(data["use_mock_data"])
            if "time_range_days" in data:
                setting.set_time_range_days(data["time_range_days"])
            db.session.commit()
    except Exception as error:
        db.session.rollback()  # never keep half-applied settings
        return error_handler.response(error)
    return jsonify(setting.to_dict())
