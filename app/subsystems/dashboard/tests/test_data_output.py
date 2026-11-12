"""Tests for the MySQL data output page (Home Assignment 3). Uses an in-memory database.

Run inside Docker:  docker compose exec web python -m pytest app/subsystems/dashboard/tests
"""

from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from app.config import Config
from app.models.scan import Scan, save_results
from app.subsystems.dashboard.services import (
    SAMPLE_HASH, add_sample_scans, filter_options, query_scans, recent_snapshots, remove_sample_scans)


USER = "tester@example.com"  # every test client is logged in as this user


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


@pytest.fixture
def client(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = USER  # what /user/login stores
    return client


def iso(days_ago):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(timespec="seconds")


@pytest.fixture
def scans(app):
    save_results([
        {"timestamp": iso(0), "item_name": "PET bottle", "material": "Kunststoff",
         "bin_type": "Pfandautomat", "is_pfand": True},
        {"timestamp": iso(1), "item_name": "Newspaper", "material": "Papier",
         "bin_type": "Papiertonne", "is_pfand": False},
        {"timestamp": iso(20), "item_name": "Yogurt cup", "material": "Kunststoff",
         "bin_type": "Gelbe Tonne", "is_pfand": False},
    ], image_hash="real", user_id=USER)


def test_query_scans_filters(scans):
    assert len(query_scans(USER)) == 3
    assert {s.item_name for s in query_scans(USER, material="Kunststoff")} == {"PET bottle", "Yogurt cup"}
    assert [s.item_name for s in query_scans(USER, bin_type="Papiertonne")] == ["Newspaper"]
    assert len(query_scans(USER, days=7)) == 2
    assert query_scans(USER)[0].item_name == "PET bottle"  # newest first


def test_filter_options(scans):
    materials, bins = filter_options(USER)
    assert materials == ["Kunststoff", "Papier"]
    assert bins == ["Gelbe Tonne", "Papiertonne", "Pfandautomat"]


def test_sample_data_can_be_added_and_removed_without_touching_real_scans(scans):
    assert add_sample_scans(USER, count=10, seed=1) == 10
    assert Scan.query.filter_by(image_hash=SAMPLE_HASH).count() == 10
    assert remove_sample_scans(USER) == 10
    assert Scan.query.count() == 3  # the real scans are still there


def test_data_page_shows_rows_from_the_database(client, scans):
    page = client.get("/dashboard/data").get_data(as_text=True)
    assert "Showing 3 of 3 rows" in page
    assert "Newspaper" in page and "Pfandautomat" in page
    assert "Srivaishnavi Jakku (7225998)" in page


def test_data_page_filters_from_the_url(client, scans):
    page = client.get("/dashboard/data?material=Papier").get_data(as_text=True)
    assert "Showing 1 of 3 rows" in page
    assert "Newspaper" in page and "Yogurt cup" not in page


def test_empty_data_page(client):
    page = client.get("/dashboard/data").get_data(as_text=True)
    assert "No scans match" in page and "No snapshots yet" in page


def test_snapshots_appear_after_visiting_the_overview(client):
    client.get("/dashboard/api/stats")
    assert len(recent_snapshots(USER)) == 1
    assert "mock" in client.get("/dashboard/data").get_data(as_text=True)


def test_sample_buttons(client):
    response = client.post("/dashboard/data/sample", follow_redirects=True)
    assert "Added 60 sample scans" in response.get_data(as_text=True)
    response = client.post("/dashboard/data/sample/clear", follow_redirects=True)
    assert "Removed 60 sample scans" in response.get_data(as_text=True)


def test_overview_has_navigation_and_identification(client):
    page = client.get("/dashboard/").get_data(as_text=True)
    assert 'href="/dashboard/data"' in page
    assert "Srivaishnavi Jakku" in page
