"""Tests for the stream pipeline running inside the classifier.

Home Assignment 2 built the pipeline as a standalone framework; these tests
cover what happens once WasteClassifier actually runs it on real detections.
"""

import pytest

from app import create_app
from app.config import Config
from app.subsystems.classification import routes
from app.subsystems.classification.classifier import FakeClient, WasteClassifier

FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def detection(name, material, confidence, box, **extra):
    """One raw item, shaped the way the AI returns it."""
    item = {
        "item_name": name,
        "material": material,
        "container": extra.get("container", "other"),
        "beverage": extra.get("beverage", False),
        "pfand_logo_visible": extra.get("pfand_logo_visible", False),
        "confidence": confidence,
        "bounding_box": box,
    }
    if extra.get("drop_confidence"):
        del item["confidence"]
    if extra.get("drop_box"):
        del item["bounding_box"]
    return item


def classify(items, **kwargs):
    classifier = WasteClassifier(client=FakeClient(items=items), **kwargs)
    return classifier.classify_image(FAKE_PNG)


# --- Goal 1: filter out low-confidence predictions ---------------------------

def test_low_confidence_detection_is_dropped():
    results = classify([
        detection("Blurry thing", "Kunststoff", 0.21, [0, 0, 80, 80]),
        detection("Drink Can", "Metall", 0.93, [0, 0, 80, 80], container="can", beverage=True),
    ])
    assert [r.item_name for r in results] == ["Drink Can"]


# --- Goal 2: visual tags become categories and routing codes -----------------

def test_visual_tag_sets_the_material_category_and_routing_code():
    results = classify([
        detection("Drink Can", "Metall", 0.9, [0, 0, 80, 80], container="can", beverage=True),
    ])
    assert results[0].material_category == "Aluminium"
    assert results[0].routing_code == "R-03"


# --- Goal 2: bounding box metrics affect the routing code --------------------

def test_oversize_bounding_box_is_routed_to_the_oversize_lane():
    results = classify([
        detection("Pallet", "Papier", 0.9, [0, 0, 300, 300]),
    ])
    assert results[0].routing_code == "R-09"


# --- Where the routing code goes: the database, not the page -----------------

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "your-openai-api-key")  # demo mode
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    routes._classifier = None
    return create_app(TestConfig)


def test_routing_code_is_saved_to_the_database(app):
    """The code is never shown to the user, so the database is where it must land."""
    with app.app_context():
        from app.models.scan import Scan, save_results
        results = [r.to_dict() for r in
                   WasteClassifier(client=FakeClient()).classify_image(FAKE_PNG)]
        save_results(results, "hash-for-this-test")
        codes = [row.routing_code for row in Scan.query.order_by(Scan.id).all()]
    assert codes == ["R-01", "R-06"]


# --- Safety: a sloppy answer from the AI must not empty the page -------------

def test_missing_confidence_and_box_are_not_dropped():
    """If the model ignores the new prompt fields, nothing may disappear."""
    results = classify([
        detection("Newspaper", "Papier", 0.0, [0, 0, 0, 0],
                  drop_confidence=True, drop_box=True),
    ])
    assert [r.item_name for r in results] == ["Newspaper"]
    assert results[0].confidence == 1.0
    assert results[0].routing_code == "R-06"


# --- The scans.user_id column must hold the ids the user subsystem issues -----

def test_user_id_column_accepts_the_string_ids_used_by_user_management():
    """SQLite ignores column types, so assert the declared type directly.

    users.user_id is a String(50) primary key. If scans.user_id were an Integer,
    MySQL would reject every scan made by a logged-in user with
    "Incorrect integer value", even though the SQLite tests would still pass.
    """
    from sqlalchemy import String

    from app.models.scan import Scan

    column = Scan.__table__.columns["user_id"]
    assert isinstance(column.type, String), (
        f"scans.user_id is {column.type!r}; it must be a String to match "
        f"users.user_id in the user management subsystem"
    )
    assert column.type.length >= 50
