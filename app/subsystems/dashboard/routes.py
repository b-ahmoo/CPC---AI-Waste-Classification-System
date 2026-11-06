"""Web routes for the Dashboard subsystem.

    GET  /dashboard/               the dashboard page
    GET  /dashboard/api/stats      current statistics as JSON (also saved as a snapshot)
    GET  /dashboard/api/settings   current settings
    POST /dashboard/api/settings   change settings, e.g. {"use_mock_data": false}
    GET  /dashboard/data           MySQL data output: filterable scans table and saved snapshots
    POST /dashboard/data/sample    add sample rows to the scans table
    POST /dashboard/data/sample/clear  remove those sample rows again
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from app.extensions import db
from app.models.dashboard import DashboardSetting
from app.subsystems.dashboard.services import (
    add_sample_scans, build_snapshot, count_scans, filter_options, query_scans, recent_snapshots,
    remove_sample_scans)

dashboard_bp = Blueprint("dashboard", __name__)

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


@dashboard_bp.route("/data")
def data_page():
    material = request.args.get("material") or None
    bin_type = request.args.get("bin_type") or None
    days = request.args.get("days", type=int)
    materials, bins = filter_options()
    return render_template(
        "dashboard/data.html",
        scans=query_scans(material=material, bin_type=bin_type, days=days),
        total_scans=count_scans(),
        snapshots=recent_snapshots(),
        materials=materials,
        bins=bins,
        selected={"material": material, "bin_type": bin_type, "days": days},
    )


@dashboard_bp.route("/data/sample", methods=["POST"])
def add_sample():
    flash(f"Added {add_sample_scans()} sample scans to the database.")
    return redirect(url_for("dashboard.data_page"))


@dashboard_bp.route("/data/sample/clear", methods=["POST"])
def clear_sample():
    flash(f"Removed {remove_sample_scans()} sample scans from the database.")
    return redirect(url_for("dashboard.data_page"))
