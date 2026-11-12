"""Tests that every user sees only their own data on the dashboard. Uses an in-memory database.

The user management subsystem stores the logged-in user in session["user_id"],
and the classification subsystem saves each scan with that user id.

Run inside Docker:  docker compose exec web python -m pytest app/subsystems/dashboard/tests
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, text

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.dashboard import DashboardSetting, DashboardSnapshot
from app.models.scan import Scan, save_results
from app.subsystems.dashboard.services import (
    add_sample_scans, build_snapshot, count_scans, ensure_snapshot_user_column, filter_options,
    load_live_scans, query_scans, recent_snapshots, remove_sample_scans)

ALICE = "alice@example.com"
BOB = "bob@example.com"


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "your-openai-api-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "your-open-ai-api-endpoint")
    app = create_app(TestConfig)
    with app.app_context():
        yield app


def login(app, user_id):
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = user_id
    return client


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@pytest.fixture
def two_users(app):
    """Alice has 3 plastic scans, Bob has 5 paper scans, and there is 1 scan without a user."""
    save_results([{"timestamp": now(), "item_name": "PET bottle", "material": "Kunststoff",
                   "bin_type": "Gelbe Tonne", "is_pfand": False}] * 3, image_hash="a", user_id=ALICE)
    save_results([{"timestamp": now(), "item_name": "Newspaper", "material": "Papier",
                   "bin_type": "Papiertonne", "is_pfand": False}] * 5, image_hash="b", user_id=BOB)
    save_results([{"timestamp": now(), "item_name": "Glass jar", "material": "Glas",
                   "bin_type": "Altglas", "is_pfand": False}], image_hash="c", user_id=None)
    setting = DashboardSetting.get_or_create()
    setting.set_use_mock_data(False)  # live data, so the numbers come from the scans table
    db.session.commit()


# --- Fetching data for different user ids -------------------------------------------

def test_live_scans_are_fetched_per_user(two_users):
    assert len(load_live_scans(days=7, user_id=ALICE)) == 3
    assert len(load_live_scans(days=7, user_id=BOB)) == 5


def test_data_queries_are_per_user(two_users):
    assert count_scans(ALICE) == 3 and count_scans(BOB) == 5
    assert {s.item_name for s in query_scans(ALICE)} == {"PET bottle"}
    assert {s.item_name for s in query_scans(BOB)} == {"Newspaper"}
    assert filter_options(ALICE) == (["Kunststoff"], ["Gelbe Tonne"])
    assert filter_options(BOB) == (["Papier"], ["Papiertonne"])


def test_without_a_user_nothing_is_returned(two_users):
    # The scan without a user must not show up as "nobody's data" either.
    assert load_live_scans(days=7, user_id=None) == []
    assert query_scans(None) == [] and count_scans(None) == 0
    assert filter_options(None) == ([], [])


def test_snapshots_belong_to_their_user(two_users):
    build_snapshot(user_id=ALICE)
    build_snapshot(user_id=BOB)
    build_snapshot(user_id=BOB)
    assert [s.get_user_id() for s in recent_snapshots(ALICE)] == [ALICE]
    assert len(recent_snapshots(BOB)) == 2
    assert recent_snapshots(ALICE)[0].get_total_items() == 3


# --- A user only sees his own data in the browser ---------------------------------

def test_stats_api_shows_only_own_items(app, two_users):
    alice = login(app, ALICE).get("/dashboard/api/stats").get_json()
    bob = login(app, BOB).get("/dashboard/api/stats").get_json()
    assert alice["source"] == "live" and alice["cards"]["total_items"] == 3
    assert alice["bin_chart"]["labels"] == ["Gelbe Tonne"]
    assert bob["cards"]["total_items"] == 5
    assert bob["bin_chart"]["labels"] == ["Papiertonne"]


def test_data_page_shows_only_own_rows(app, two_users):
    page = login(app, ALICE).get("/dashboard/data").get_data(as_text=True)
    assert "Showing 3 of 3 rows" in page
    assert "PET bottle" in page
    assert "Newspaper" not in page and "Glass jar" not in page
    assert f"Logged in as {ALICE}" in page


def test_data_page_shows_only_own_snapshots(app, two_users):
    bob = login(app, BOB)
    bob.get("/dashboard/api/stats")
    assert DashboardSnapshot.query.count() == 1
    assert "No snapshots yet" in login(app, ALICE).get("/dashboard/data").get_data(as_text=True)
    assert "No snapshots yet" not in bob.get("/dashboard/data").get_data(as_text=True)


def test_sample_scans_only_affect_own_account(app, two_users):
    alice = login(app, ALICE)
    alice.post("/dashboard/data/sample")
    assert count_scans(ALICE) == 63 and count_scans(BOB) == 5
    response = login(app, BOB).post("/dashboard/data/sample/clear", follow_redirects=True)
    assert "Removed 0 sample scans" in response.get_data(as_text=True)
    assert count_scans(ALICE) == 63  # Bob cannot remove Alice's sample scans
    assert remove_sample_scans(ALICE) == 60 and count_scans(ALICE) == 3


def test_add_sample_scans_saves_the_user_id(app):
    add_sample_scans(ALICE, count=5, seed=1)
    assert {s.user_id for s in Scan.query.all()} == {ALICE}


# --- Logged-out visitors ---------------------------------------------------------------

def test_logged_out_pages_redirect_to_login(app, two_users):
    client = app.test_client()
    for response in (client.get("/dashboard/"), client.get("/dashboard/data"),
                     client.post("/dashboard/data/sample"), client.post("/dashboard/data/sample/clear")):
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/user/login")
    assert count_scans(ALICE) == 3  # the POSTs changed nothing


def test_logged_out_stats_api_returns_401(app, two_users):
    response = app.test_client().get("/dashboard/api/stats")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Please log in to see your dashboard.", "type": "NotLoggedInError"}
    assert DashboardSnapshot.query.count() == 0


# --- Upgrading an older database --------------------------------------------------------

def test_missing_user_column_is_added_to_an_old_snapshots_table(app):
    db.session.remove()
    with db.engine.begin() as connection:
        connection.execute(text("DROP TABLE daily_activity"))
        connection.execute(text("DROP TABLE bin_statistics"))
        connection.execute(text("DROP TABLE dashboard_snapshots"))
        connection.execute(text(
            "CREATE TABLE dashboard_snapshots (id INTEGER PRIMARY KEY, created_at DATETIME NOT NULL, "
            "source VARCHAR(10) NOT NULL, total_items INTEGER NOT NULL, pfand_items INTEGER NOT NULL, "
            "material_count INTEGER NOT NULL)"))
    assert ensure_snapshot_user_column() is True
    columns = {c["name"] for c in inspect(db.engine).get_columns("dashboard_snapshots")}
    assert "user_id" in columns
    assert ensure_snapshot_user_column() is False  # running it again changes nothing
