"""Tests for the Dashboard models, services and routes. No API key or internet needed.

Run inside Docker:  docker compose exec web pytest app/subsystems/dashboard/tests
"""

from datetime import date

import pytest
from sqlalchemy import inspect

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.dashboard import BinStatistic, DailyActivity, DashboardSetting, DashboardSnapshot
from app.models.scan import save_results
from app.subsystems.dashboard.services import build_snapshot, generate_mock_scans


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


SCANS = [
    {"timestamp": "2026-10-30T10:00:00+00:00", "item_name": "PET bottle", "material": "Kunststoff",
     "bin_type": "Pfandautomat", "is_pfand": True},
    {"timestamp": "2026-10-30T11:00:00+00:00", "item_name": "Yogurt cup", "material": "Kunststoff",
     "bin_type": "Gelbe Tonne", "is_pfand": False},
    {"timestamp": "2026-10-31T09:00:00+00:00", "item_name": "Newspaper", "material": "Papier",
     "bin_type": "Papiertonne", "is_pfand": False},
    {"timestamp": "2026-10-31T09:30:00+00:00", "item_name": "Tin can", "material": "Metall",
     "bin_type": "Gelbe Tonne", "is_pfand": False},
]


# --- Tables -----------------------------------------------------------------

def test_create_all_makes_dashboard_tables(app):
    tables = inspect(db.engine).get_table_names()
    for name in ("dashboard_settings", "dashboard_snapshots", "bin_statistics", "daily_activity"):
        assert name in tables


# --- DashboardSetting -------------------------------------------------------

def test_setting_defaults_and_get_or_create_returns_one_row(app):
    first = DashboardSetting.get_or_create()
    second = DashboardSetting.get_or_create()
    assert first.id == second.id
    assert first.get_use_mock_data() is True
    assert first.get_time_range_days() == 14
    assert DashboardSetting.query.count() == 1


def test_setting_setters_validate(app):
    setting = DashboardSetting()
    setting.set_time_range_days(30)
    assert setting.get_time_range_days() == 30
    with pytest.raises(ValueError):
        setting.set_use_mock_data("yes")
    with pytest.raises(ValueError):
        setting.set_time_range_days(0)


# --- DashboardSnapshot, BinStatistic, DailyActivity -------------------------

def test_snapshot_from_scans_calculates_statistics(app):
    snapshot = DashboardSnapshot.from_scans(SCANS, "live")
    assert snapshot.get_total_items() == 4
    assert snapshot.get_pfand_items() == 1
    assert snapshot.get_material_count() == 3
    assert snapshot.pfand_share() == 25.0
    bins = {s.get_bin_type(): s.get_item_count() for s in snapshot.bin_statistics}
    assert bins == {"Gelbe Tonne": 2, "Pfandautomat": 1, "Papiertonne": 1}
    days = {a.get_activity_date(): a.get_item_count() for a in snapshot.daily_activity}
    assert days == {date(2026, 10, 30): 2, date(2026, 10, 31): 2}


def test_snapshot_is_saved_with_its_rows(app):
    db.session.add(DashboardSnapshot.from_scans(SCANS, "live"))
    db.session.commit()
    saved = DashboardSnapshot.query.one()
    assert len(saved.bin_statistics) == 3
    assert BinStatistic.query.count() == 3
    assert DailyActivity.query.count() == 2
    assert saved.bin_statistics[0].get_snapshot() is saved

    db.session.delete(saved)  # deleting a snapshot also deletes its rows
    db.session.commit()
    assert BinStatistic.query.count() == 0
    assert DailyActivity.query.count() == 0


def test_empty_snapshot(app):
    snapshot = DashboardSnapshot.from_scans([], "live")
    assert snapshot.get_total_items() == 0
    assert snapshot.pfand_share() is None
    assert snapshot.to_dict()["bin_chart"] == {"labels": [], "values": []}


def test_snapshot_setters_validate(app):
    with pytest.raises(ValueError):
        DashboardSnapshot(source="other")
    snapshot = DashboardSnapshot(source="mock")
    with pytest.raises(ValueError):
        snapshot.set_total_items(-1)
    with pytest.raises(ValueError):
        BinStatistic("", 3)
    with pytest.raises(ValueError):
        DailyActivity("2026-10-31", 3)
    with pytest.raises(TypeError):
        snapshot.add_bin_statistic("Gelbe Tonne")


def test_bin_share(app):
    assert BinStatistic("Gelbe Tonne", 2).share_of(4) == 50.0
    assert BinStatistic("Gelbe Tonne", 2).share_of(0) == 0.0


# --- Services ---------------------------------------------------------------

def test_mock_scans_follow_the_bin_rules(app):
    scans = generate_mock_scans(count=100, seed=1)
    assert len(scans) == 100
    for scan in scans:
        if scan["is_pfand"]:
            assert scan["bin_type"] == "Pfandautomat"
        elif scan["material"] in ("Kunststoff", "Metall", "Verbundstoff"):
            assert scan["bin_type"] == "Gelbe Tonne"


def test_build_snapshot_uses_live_scans_when_mock_is_off(app):
    setting = DashboardSetting.get_or_create()
    setting.set_use_mock_data(False)
    db.session.commit()
    today = date.today().isoformat() + "T12:00:00+00:00"
    save_results([{"timestamp": today, "item_name": "Glass jar", "material": "Glas",
                   "bin_type": "Altglas", "is_pfand": False}], image_hash="abc")

    snapshot = build_snapshot()
    assert snapshot.get_source() == "live"
    assert snapshot.get_total_items() == 1
    assert DashboardSnapshot.query.count() == 1


# --- Routes -----------------------------------------------------------------

def test_dashboard_page_loads(client):
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"Items Classified" in response.data


def test_stats_api_returns_and_saves_mock_data(client):
    data = client.get("/dashboard/api/stats").get_json()
    assert data["source"] == "mock"
    assert data["cards"]["total_items"] == 250
    assert len(data["bin_chart"]["labels"]) > 0
    assert DashboardSnapshot.query.count() == 1


def test_settings_api_switches_to_live(client):
    response = client.post("/dashboard/api/settings", json={"use_mock_data": False})
    assert response.status_code == 200
    assert response.get_json()["use_mock_data"] is False
    assert client.get("/dashboard/api/stats").get_json()["source"] == "live"


def test_settings_api_rejects_bad_values(client):
    response = client.post("/dashboard/api/settings", json={"time_range_days": 0})
    assert response.status_code == 400
