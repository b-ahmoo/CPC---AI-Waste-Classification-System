"""Web routes for the Dashboard subsystem.

    GET  /dashboard/               the dashboard page
    GET  /dashboard/api/stats      current statistics as JSON (also saved as a snapshot); optional ?days=1..365
    GET  /dashboard/api/settings   current settings
    POST /dashboard/api/settings   change settings, e.g. {"use_mock_data": false}
    GET  /dashboard/data           MySQL data output: filterable scans table and saved snapshots
    POST /dashboard/data/sample    add sample rows to the scans table
    POST /dashboard/data/sample/clear  remove those sample rows again

Every error goes through DashboardErrorHandler (app/subsystems/dashboard/errors.py)
and comes back as JSON: {"error": "...", "type": "..."} with a matching status code.
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from app.extensions import db
from app.models.dashboard import DashboardSetting
from app.subsystems.dashboard.errors import DashboardErrorHandler, InvalidSettingError
from app.subsystems.dashboard.services import (
    add_sample_scans, build_snapshot, count_scans, filter_options, parse_days, query_scans,
    recent_snapshots, remove_sample_scans)

dashboard_bp = Blueprint("dashboard", __name__)
error_handler = DashboardErrorHandler()
error_handler.register(dashboard_bp)  # safety net for anything a route doesn't catch itself

ALLOWED_SETTINGS = {"use_mock_data", "time_range_days"}

# Identification shown on every dashboard page
STUDENT = {"name": "Srivaishnavi Jakku", "student_id": "7225998", "subsystem": "Statistical Dashboard"}


@dashboard_bp.context_processor
def identification():
    return {"student": STUDENT}


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


@dashboard_bp.route("/data")
def data_page():
    selected = {"material": request.args.get("material") or None,
                "bin_type": request.args.get("bin_type") or None,
                "days": None}
    try:
        selected["days"] = parse_days(request.args.get("days"))
        materials, bins = filter_options()
        return render_template(
            "dashboard/data.html",
            scans=query_scans(material=selected["material"], bin_type=selected["bin_type"], days=selected["days"]),
            total_scans=count_scans(),
            snapshots=recent_snapshots(),
            materials=materials,
            bins=bins,
            selected=selected,
        )
    except Exception as error:
        # Show the page with a friendly message instead of crashing.
        body, status = error_handler.handle(error)
        return render_template("dashboard/data.html", scans=[], total_scans=0, snapshots=[],
                               materials=[], bins=[], selected=selected, error=body["error"]), status


@dashboard_bp.route("/data/sample", methods=["POST"])
def add_sample():
    try:
        flash(f"Added {add_sample_scans()} sample scans to the database.")
    except Exception as error:
        flash(error_handler.handle(error)[0]["error"])
    return redirect(url_for("dashboard.data_page"))


@dashboard_bp.route("/data/sample/clear", methods=["POST"])
def clear_sample():
    try:
        flash(f"Removed {remove_sample_scans()} sample scans from the database.")
    except Exception as error:
        flash(error_handler.handle(error)[0]["error"])
    return redirect(url_for("dashboard.data_page"))
