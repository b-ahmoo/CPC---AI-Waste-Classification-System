"""Web routes for the Dashboard subsystem (statistical dashboard).

    /dashboard/            -> the dashboard page
    /dashboard/api/stats   -> statistics as JSON (used by the page's charts)
"""

from flask import Blueprint, jsonify, render_template

from .dashboard_service import DashboardService

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

# Mock data for now. When the classifier is ready:
#   DashboardService(use_mock_data=False, record_provider=<function returning records>)
_service = DashboardService(use_mock_data=True)
_service.initialize()


@dashboard_bp.route("/")
def dashboard_page():
    return render_template("dashboard/dashboard.html")


@dashboard_bp.route("/api/stats")
def api_stats():
    _service.refresh()
    return jsonify(_service.get_dashboard_data())
