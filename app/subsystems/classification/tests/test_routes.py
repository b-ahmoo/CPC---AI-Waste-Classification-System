"""Tests for the Flask page and the database. No API key or internet needed."""

import io

import pytest

from app import create_app
from app.config import Config
from app.subsystems.classification import routes
from app.subsystems.classification.models import Scan, find_by_hash, save_results

FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"  # in-memory database


@pytest.fixture
def app(monkeypatch):
    # Template placeholders, like a fresh copy of .env.example: classifier runs in demo mode
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "your-openai-api-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "your-open-ai-api-endpoint")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    routes._classifier = None
    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()


def test_page_loads(client):
    response = client.get("/classify/")
    assert response.status_code == 200
    assert b"Identify &amp; Classify" in response.data
    assert b"Demo mode" in response.data


def test_upload_shows_results(client):
    response = client.post(
        "/classify/",
        data={"image": (io.BytesIO(FAKE_PNG), "bottle.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert b"PET Bottle" in response.data
    assert b"Pfandautomat" in response.data


def test_non_image_shows_error(client):
    response = client.post(
        "/classify/",
        data={"image": (io.BytesIO(b"not an image"), "notes.txt")},
        content_type="multipart/form-data",
    )
    assert b"Only JPEG and PNG images are supported." in response.data


def test_database_saves_and_finds_by_hash(app):
    with app.app_context():
        save_results([{"timestamp": "2026-10-29T10:00:00+00:00", "item_name": "PET Bottle",
                       "material": "Kunststoff", "bin_type": "Pfandautomat", "is_pfand": True}],
                     "abc123", user_id=7)
        found = find_by_hash("abc123")
        assert found[0]["item_name"] == "PET Bottle"
        assert found[0]["is_pfand"] is True
        assert Scan.query.first().user_id == 7
        assert find_by_hash("other") == []


def test_settings_prefer_azure_and_skip_placeholders(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "your-openai-api-key")   # placeholder: skipped
    monkeypatch.setenv("OPENAI_API_KEY", "real-fallback-key")
    assert routes._setting("AZURE_OPENAI_API_KEY", "OPENAI_API_KEY") == "real-fallback-key"
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "real-azure-key")
    assert routes._setting("AZURE_OPENAI_API_KEY", "OPENAI_API_KEY") == "real-azure-key"
