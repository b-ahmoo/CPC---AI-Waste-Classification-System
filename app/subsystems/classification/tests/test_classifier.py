"""Unit tests. They use FakeClient, so they run without an API key or internet."""

import pytest


from app.subsystems.classification.classifier import (BinMapper, ClassificationError, FakeClient,
                        WasteClassifier)

FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100
FAKE_JPEG = b"\xff\xd8\xff" + b"0" * 100


def make_classifier(items):
    return WasteClassifier(client=FakeClient(items=items))


def test_bin_mapper_maps_materials():
    mapper = BinMapper()
    assert mapper.map_to_bin("Kunststoff") == "Gelbe Tonne"
    assert mapper.map_to_bin("Papier") == "Papiertonne"
    assert mapper.map_to_bin("Glas") == "Altglas"
    assert mapper.map_to_bin("Unbekannt") == "nicht erkannt"


def test_bin_mapper_detects_pfand():
    mapper = BinMapper()
    assert mapper.is_pfand("PET Bottle") is True
    assert mapper.is_pfand("Beer can") is True
    assert mapper.is_pfand("Yoghurt cup") is False


def test_pfand_item_goes_to_pfandautomat():
    results = make_classifier([{"item_name": "PET Bottle", "material": "Kunststoff"}]).classify_image(FAKE_PNG)
    assert results[0].bin_type == "Pfandautomat"
    assert results[0].is_pfand is True


def test_drink_can_with_pfand_logo_goes_to_pfandautomat():
    """The tonic water can that was wrongly sent to the Gelbe Tonne."""
    item = {"item_name": "Tonic Water Can", "material": "Metall", "container": "can",
            "beverage": True, "pfand_logo_visible": True}
    result = make_classifier([item]).classify_image(FAKE_JPEG)[0]
    assert result.is_pfand is True
    assert result.bin_type == "Pfandautomat"


def test_drink_can_without_visible_logo_is_still_pfand():
    item = {"item_name": "Energy drink can", "material": "Metall", "container": "can",
            "beverage": True, "pfand_logo_visible": False}
    assert make_classifier([item]).classify_image(FAKE_JPEG)[0].bin_type == "Pfandautomat"


def test_food_tin_is_not_pfand():
    item = {"item_name": "Tomato tin", "material": "Metall", "container": "can",
            "beverage": False, "pfand_logo_visible": False}
    result = make_classifier([item]).classify_image(FAKE_JPEG)[0]
    assert result.is_pfand is False
    assert result.bin_type == "Gelbe Tonne"


def test_wine_bottle_without_logo_goes_to_altglas():
    item = {"item_name": "Wine bottle", "material": "Glas", "container": "glass_bottle",
            "beverage": True, "pfand_logo_visible": False}
    assert make_classifier([item]).classify_image(FAKE_JPEG)[0].bin_type == "Altglas"


def test_multi_item_image_gives_one_result_per_item():
    items = [
        {"item_name": "Newspaper", "material": "Papier"},
        {"item_name": "Banana peel", "material": "Bio"},
        {"item_name": "Glass jar", "material": "Glas"},
    ]
    results = make_classifier(items).classify_image(FAKE_JPEG)
    assert [r.bin_type for r in results] == ["Papiertonne", "Biotonne", "Altglas"]


def test_nothing_recognised_returns_nicht_erkannt():
    results = make_classifier([]).classify_image(FAKE_PNG)
    assert results[0].bin_type == "nicht erkannt"


def test_rejects_non_image_file():
    with pytest.raises(ClassificationError):
        make_classifier([]).classify_image(b"this is not an image")


def test_rejects_file_over_10_mb():
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (10 * 1024 * 1024)
    with pytest.raises(ClassificationError):
        make_classifier([]).classify_image(big)


def test_retries_without_json_mode_and_strips_code_fence():
    """Providers like Gemini may reject JSON mode or wrap JSON in ```json fences."""
    from types import SimpleNamespace

    class BadRequestError(Exception):
        pass

    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        if "response_format" in kwargs:
            raise BadRequestError("response_format not supported")
        text = '```json\n{"items": [{"item_name": "Drink can", "material": "Metall"}]}\n```'
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    results = WasteClassifier(client=client).classify_image(FAKE_PNG)
    assert len(calls) == 2
    assert results[0].bin_type == "Pfandautomat"
