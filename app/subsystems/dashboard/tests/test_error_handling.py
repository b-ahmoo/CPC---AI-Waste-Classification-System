"""Tests for error handling in the Statistical Dashboard subsystem (Home Assignment 4).

Follows the Flask testing guide: the app is made by the app factory with a test
config, requests go through Flask's test client, and the database is an
in-memory SQLite database, so no MySQL server or API key is needed.

Run inside Docker:  docker compose exec web python -m pytest app/subsystems/dashboard/tests
"""

import logging

import pytest
from sqlalchemy.exc import OperationalError

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.dashboard import DashboardSetting, DashboardSnapshot
from app.models.scan import Scan
from app.subsystems.dashboard import services
from app.subsystems.dashboard.errors import (
    DashboardError, DashboardErrorHandler, DataSourceError, InvalidFilterError, InvalidSettingError)

DB_DOWN = OperationalError("SELECT ...", {}, Exception("database is down"))


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"  # in-memory database


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "your-openai-api-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "your-open-ai-api-endpoint")
    app = create_app(TestConfig)
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


# --- The exception classes ------------------------------------------------------

def test_exception_hierarchy_and_status_codes():
    for error_class, status in [(InvalidSettingError, 400), (InvalidFilterError, 400),
                                (DataSourceError, 503), (DashboardError, 500)]:
        assert issubclass(error_class, DashboardError)
        assert issubclass(error_class, Exception)
        assert error_class.status_code == status


def test_error_message_defaults_and_field():
    assert str(DataSourceError()) == DataSourceError.default_message
    error = InvalidFilterError("days must be a whole number.", field="days")
    assert error.to_dict() == {"error": "days must be a whole number.",
                               "type": "InvalidFilterError", "field": "days"}


# --- The error-handling class -----------------------------------------------------

def test_handler_turns_value_error_into_400():
    body, status = DashboardErrorHandler().handle(ValueError("time_range_days must be between 1 and 365"))
    assert status == 400
    assert body["type"] == "InvalidSettingError"
    assert "between 1 and 365" in body["error"]


def test_handler_turns_database_error_into_503_and_rolls_back(app, monkeypatch):
    rollbacks = []
    monkeypatch.setattr(db.session, "rollback", lambda: rollbacks.append(True))
    body, status = DashboardErrorHandler().handle(DB_DOWN)
    assert status == 503
    assert body["error"] == DataSourceError.default_message
    assert rollbacks == [True]


def test_handler_hides_unexpected_errors_but_logs_the_traceback(caplog):
    with caplog.at_level(logging.ERROR):
        body, status = DashboardErrorHandler().handle(KeyError("secret internal detail"))
    assert status == 500
    assert "secret internal detail" not in body["error"]  # never shown to the user
    assert caplog.records[-1].exc_info is not None       # but kept for developers


def test_handler_logs_user_mistakes_only_as_warnings(caplog):
    handler = DashboardErrorHandler()
    with caplog.at_level(logging.WARNING):
        handler.handle(InvalidFilterError("bad days"))
    assert caplog.records[-1].levelno == logging.WARNING
    assert handler.handled_count == 1


def test_failed_rollback_is_logged_not_raised(app, monkeypatch, caplog):
    def broken_rollback():
        raise RuntimeError("connection lost")

    monkeypatch.setattr(db.session, "rollback", broken_rollback)
    with caplog.at_level(logging.WARNING):
        body, status = DashboardErrorHandler().handle(DB_DOWN)
    assert status == 503
    assert "rollback failed" in caplog.text


# --- Validation and error handling in the services ----------------------------------

def test_parse_days_accepts_valid_values():
    assert services.parse_days(None) is None
    assert services.parse_days("") is None
    assert services.parse_days("7") == 7


def test_parse_days_rejects_invalid_values():
    for bad in ("abc", "0", "366", "-3", "2.5"):
        with pytest.raises(InvalidFilterError):
            services.parse_days(bad)


def test_missing_rules_file_raises_data_source_error_with_cause(tmp_path):
    with pytest.raises(DataSourceError) as caught:
        services.load_bin_rules(tmp_path / "missing.json")
    assert isinstance(caught.value.__cause__, FileNotFoundError)  # exception chaining


def test_scans_with_broken_timestamps_are_skipped(app, caplog):
    db.session.add_all([
        Scan(timestamp="not-a-date", image_hash="t1", item_name="?", material="Glas", bin_type="Altglas", is_pfand=False),
        Scan(timestamp=services.datetime.now(services.timezone.utc).isoformat(), image_hash="t2", item_name="Jar",
             material="Glas", bin_type="Altglas", is_pfand=False),
    ])
    db.session.commit()
    with caplog.at_level(logging.WARNING):
        scans = services.load_live_scans(days=7)
    assert [s["item_name"] for s in scans] == ["Jar"]
    assert "Skipped 1 scan" in caplog.text


# --- Error responses from the routes --------------------------------------------------

def test_stats_with_invalid_days_returns_400_json(client):
    response = client.get("/dashboard/api/stats?days=abc")
    assert response.status_code == 400
    assert response.get_json() == {"error": "days must be a whole number.",
                                   "type": "InvalidFilterError", "field": "days"}
    assert DashboardSnapshot.query.count() == 0  # nothing was saved


def test_stats_when_database_is_down_returns_503(client, monkeypatch):
    def database_down(*args, **kwargs):
        raise DB_DOWN

    monkeypatch.setattr(services.DashboardSetting, "get_or_create", database_down)
    response = client.get("/dashboard/api/stats")
    assert response.status_code == 503
    assert response.get_json()["type"] == "DataSourceError"


def test_failed_snapshot_save_returns_503_and_saves_nothing(client, monkeypatch):
    DashboardSetting.get_or_create()  # create the settings row before breaking commit
    real_commit = db.session.commit

    def failing_commit():
        raise DB_DOWN

    monkeypatch.setattr(db.session, "commit", failing_commit)
    response = client.get("/dashboard/api/stats")
    monkeypatch.setattr(db.session, "commit", real_commit)
    assert response.status_code == 503
    assert response.get_json()["error"] == "The snapshot could not be saved."
    assert DashboardSnapshot.query.count() == 0


def test_settings_rejects_a_body_that_is_not_json(client):
    response = client.post("/dashboard/api/settings", data="use_mock_data=false",
                           content_type="text/plain")
    assert response.status_code == 400
    assert response.get_json()["error"] == "Send the settings as a JSON object."


def test_settings_rejects_unknown_keys(client):
    response = client.post("/dashboard/api/settings", json={"colour": "green"})
    assert response.status_code == 400
    assert response.get_json()["field"] == "colour"


def test_invalid_setting_is_rolled_back_completely(client):
    # The first value is valid, the second is not: neither may be saved.
    response = client.post("/dashboard/api/settings", json={"use_mock_data": False, "time_range_days": 0})
    assert response.status_code == 400
    current = client.get("/dashboard/api/settings").get_json()
    assert current["use_mock_data"] is True
    assert current["time_range_days"] == 14


def test_unknown_dashboard_url_returns_json_404(client):
    response = client.get("/dashboard/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["type"] == "NotFound"


def test_wrong_http_method_returns_json_405(client):
    response = client.delete("/dashboard/api/settings")
    assert response.status_code == 405
    assert response.get_json()["type"] == "MethodNotAllowed"


def test_unexpected_bug_returns_friendly_500(client, monkeypatch):
    def bug(*args, **kwargs):
        raise ZeroDivisionError("division by zero in from_scans")

    monkeypatch.setattr(services.DashboardSnapshot, "from_scans", bug)
    response = client.get("/dashboard/api/stats")
    assert response.status_code == 500
    assert response.get_json()["error"] == DashboardErrorHandler.UNEXPECTED_MESSAGE
    assert "division" not in response.get_data(as_text=True)


# --- Error handling on the data page (combined Home Assignments 3 + 4) ----------------

def test_data_page_with_invalid_days_shows_message(client):
    response = client.get("/dashboard/data?days=abc")
    assert response.status_code == 400
    assert "days must be a whole number." in response.get_data(as_text=True)


def test_data_page_when_database_is_down_shows_message(client, monkeypatch):
    def database_down(*args, **kwargs):
        raise DB_DOWN

    monkeypatch.setattr(services.db.session, "query", database_down)
    response = client.get("/dashboard/data")
    assert response.status_code == 503
    assert "The filter options could not be loaded." in response.get_data(as_text=True)
