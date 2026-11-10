"""Tests for error handling in the classification subsystem (Home Assignment 4).

Follows the Flask testing guide: an app made by the app factory with a test
config, a test client that sends real requests, and an in-memory database.
"""

import io
import logging

import pytest
from sqlalchemy.exc import OperationalError

from app import create_app
from app.config import Config
from app.subsystems.classification import routes
from app.subsystems.classification.classifier import ClassificationError, WasteClassifier
from app.subsystems.classification.errors import ClassificationErrorHandler

FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100
DB_DOWN = OperationalError("SELECT ...", {}, Exception("database is down"))


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


def upload(client, data, filename="photo.png"):
    return client.post(
        "/classify/",
        data={"image": (io.BytesIO(data), filename)},
        content_type="multipart/form-data",
    )


# --- The error-handling class on its own -------------------------------------

def test_handler_returns_message_of_classification_error():
    handler = ClassificationErrorHandler()
    assert handler.handle(ClassificationError("Image is larger than 10 MB.")) == "Image is larger than 10 MB."


def test_handler_returns_database_message_for_database_error(app):
    with app.app_context():
        assert ClassificationErrorHandler().handle(DB_DOWN) == ClassificationErrorHandler.DATABASE_MESSAGE


def test_handler_returns_generic_message_for_unexpected_error():
    message = ClassificationErrorHandler().handle(KeyError("bug"))
    assert message == ClassificationErrorHandler.UNEXPECTED_MESSAGE


def test_handler_writes_errors_to_the_log(caplog):
    with caplog.at_level(logging.WARNING):
        ClassificationErrorHandler().handle(ClassificationError("API timed out"))
    assert "API timed out" in caplog.text


# --- Error handling through the real page (Flask test client) ----------------

def test_no_file_chosen_shows_message(client):
    response = client.post("/classify/", data={}, content_type="multipart/form-data")
    assert response.status_code == 200
    assert b"Please choose an image first." in response.data


def test_wrong_file_type_shows_message(client):
    response = upload(client, b"just some text", filename="notes.txt")
    assert response.status_code == 200
    assert b"Only JPEG and PNG images are supported." in response.data


def test_image_over_10_mb_shows_message(client):
    too_big = b"\x89PNG\r\n\x1a\n" + b"0" * (10 * 1024 * 1024)
    response = upload(client, too_big)
    assert response.status_code == 200
    assert b"Image is larger than 10 MB." in response.data


def test_api_failure_shows_message(client, monkeypatch):
    class FailingClient:  # behaves like the OpenAI client when the network is down
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise TimeoutError("request timed out")

    monkeypatch.setattr(routes, "_classifier", WasteClassifier(client=FailingClient()))
    monkeypatch.setattr(routes, "_demo_mode", False)
    response = upload(client, FAKE_PNG)
    assert response.status_code == 200
    assert b"Classification failed: request timed out" in response.data


def test_database_down_during_upload_shows_message(client, monkeypatch):
    def broken_find_by_hash(image_hash):
        raise DB_DOWN

    monkeypatch.setattr(routes, "find_by_hash", broken_find_by_hash)
    response = upload(client, FAKE_PNG)
    assert response.status_code == 200
    assert b"The database is not available right now." in response.data


def test_page_still_loads_when_database_is_down(client, monkeypatch):
    def broken_recent_scans(limit=10):
        raise DB_DOWN

    monkeypatch.setattr(routes, "recent_scans", broken_recent_scans)
    response = client.get("/classify/")
    assert response.status_code == 200
    assert b"Identify &amp; Classify" in response.data