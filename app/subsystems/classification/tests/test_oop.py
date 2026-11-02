"""Tests for the constructors, initialization methods, getters and setters
of the three classification classes (Home Assignment 1)."""

import json

import pytest

from app.subsystems.classification.classifier import (
    BinMapper, ClassificationResult, FakeClient, WasteClassifier)


# --- ClassificationResult ----------------------------------------------------

def test_result_constructor_sets_attributes_and_timestamp():
    result = ClassificationResult("PET Bottle", "Kunststoff", "Pfandautomat", True)
    assert result.item_name == "PET Bottle"
    assert result.material == "Kunststoff"
    assert result.bin_type == "Pfandautomat"
    assert result.is_pfand is True
    assert result.timestamp.endswith("+00:00")


def test_result_setters_change_values():
    result = ClassificationResult("Can", "Metall", "Gelbe Tonne")
    result.bin_type = "Pfandautomat"
    result.is_pfand = 1
    assert result.bin_type == "Pfandautomat"
    assert result.is_pfand is True


def test_result_setter_rejects_empty_text():
    result = ClassificationResult("Can", "Metall", "Gelbe Tonne")
    with pytest.raises(ValueError):
        result.item_name = "  "


def test_result_from_dict_round_trip():
    original = ClassificationResult("Newspaper", "Papier", "Papiertonne", False)
    copy = ClassificationResult.from_dict(original.to_dict())
    assert copy.to_dict() == original.to_dict()


# --- BinMapper ---------------------------------------------------------------

def test_bin_mapper_constructor_loads_rules():
    mapper = BinMapper()
    assert mapper.rules_path == "rules.json"
    assert mapper.unknown_label == "nicht erkannt"
    assert mapper.pfand_bin == "Pfandautomat"


def test_bin_mapper_rules_path_setter_loads_new_file(tmp_path):
    rules = {
        "material_to_bin": {"Kunststoff": "Plastic bin"},
        "pfand": {"bin": "Deposit machine", "logo_visible_means_pfand": True,
                  "beverage_containers": [], "keywords": []},
        "unknown_label": "unknown",
    }
    other_file = tmp_path / "other_rules.json"
    other_file.write_text(json.dumps(rules), encoding="utf-8")

    mapper = BinMapper()
    mapper.rules_path = str(other_file)
    assert mapper.map_to_bin("Kunststoff") == "Plastic bin"
    assert mapper.unknown_label == "unknown"


def test_bin_mapper_rules_setter_rejects_incomplete_rules():
    mapper = BinMapper()
    with pytest.raises(ValueError):
        mapper.rules = {"material_to_bin": {}}


# --- WasteClassifier ---------------------------------------------------------

def test_classifier_constructor_and_getters():
    client = FakeClient()
    classifier = WasteClassifier(client=client, model="gpt-4o-mini", timeout=15)
    assert classifier.client is client
    assert classifier.model == "gpt-4o-mini"
    assert classifier.timeout == 15
    assert isinstance(classifier.bin_mapper, BinMapper)


def test_classifier_setters_validate():
    classifier = WasteClassifier(client=FakeClient())
    classifier.model = "gemini-3.5-flash-lite"
    assert classifier.model == "gemini-3.5-flash-lite"
    with pytest.raises(ValueError):
        classifier.timeout = 0
    with pytest.raises(ValueError):
        classifier.bin_mapper = "not a mapper"


def test_classifier_builds_its_own_client_when_none_given():
    classifier = WasteClassifier(api_key="test-key", base_url="http://localhost:1/v1")
    assert classifier.client is not None
    old_client = classifier.client
    classifier.timeout = 20           # changing a setting rebuilds the connection
    assert classifier.client is not old_client
