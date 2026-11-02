"""Tests for the event-driven stream processing framework (Home Assignment 2)."""

import pytest

from app.subsystems.classification.stream import (
    ConfidenceFilter, ConveyorStream, DetectionEvent, MaterialRoutingTransformer,
    Pipeline, RoutedItem, StreamProcessor, synthetic_detection_stream)


# --- Abstract Base Class -----------------------------------------------------

def test_stream_processor_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        StreamProcessor()


# --- Inheritance & polymorphism ----------------------------------------------

def test_confidence_filter_drops_low_confidence_item():
    event = DetectionEvent("Can", "Metall", confidence=0.3, bounding_box=(0, 0, 10, 10))
    assert ConfidenceFilter(min_confidence=0.7).process(event) is None


def test_confidence_filter_keeps_high_confidence_item():
    event = DetectionEvent("Can", "Metall", confidence=0.9, bounding_box=(0, 0, 10, 10))
    result = ConfidenceFilter(min_confidence=0.7).process(event)
    assert result is event


def test_material_routing_transformer_maps_known_material():
    event = DetectionEvent("PET Bottle", "Kunststoff", confidence=0.95, bounding_box=(0, 0, 10, 10))
    routed = MaterialRoutingTransformer().process(event)
    assert isinstance(routed, RoutedItem)
    assert routed.material_category == "Plastic"
    assert routed.routing_code == "R-01"


def test_material_routing_transformer_falls_back_for_unknown_material():
    event = DetectionEvent("Mystery", "Rest", confidence=0.95, bounding_box=(0, 0, 10, 10))
    routed = MaterialRoutingTransformer().process(event)
    assert routed.material_category == "Unsorted"
    assert routed.routing_code == "R-00"


# --- Operator overloading -----------------------------------------------------

def test_pipe_operator_chains_two_stages_into_a_pipeline():
    pipeline = ConfidenceFilter(0.7) | MaterialRoutingTransformer()
    assert isinstance(pipeline, Pipeline)
    assert len(pipeline.stages) == 2


def test_pipeline_drops_low_confidence_before_transforming():
    pipeline = ConfidenceFilter(0.7) | MaterialRoutingTransformer()
    event = DetectionEvent("Can", "Metall", confidence=0.1, bounding_box=(0, 0, 10, 10))
    assert pipeline.process(event) is None


def test_pipeline_transforms_item_that_passes_the_filter():
    pipeline = ConfidenceFilter(0.7) | MaterialRoutingTransformer()
    event = DetectionEvent("Jar", "Glas", confidence=0.8, bounding_box=(0, 0, 10, 10))
    routed = pipeline.process(event)
    assert routed.material_category == "Glass"


def test_extending_a_pipeline_with_or_appends_rather_than_nests():
    stage_a = ConfidenceFilter(0.5)
    stage_b = MaterialRoutingTransformer()
    stage_c = ConfidenceFilter(0.9)
    pipeline = (stage_a | stage_b) | stage_c
    assert pipeline.stages == [stage_a, stage_b, stage_c]


# --- Iterators & generators ---------------------------------------------------

def test_synthetic_detection_stream_yields_requested_count():
    events = list(synthetic_detection_stream(count=5, seed=1))
    assert len(events) == 5
    assert all(isinstance(e, DetectionEvent) for e in events)


def test_synthetic_detection_stream_is_reproducible_with_a_seed():
    first = [e.material for e in synthetic_detection_stream(count=5, seed=42)]
    second = [e.material for e in synthetic_detection_stream(count=5, seed=42)]
    assert first == second


def test_conveyor_stream_only_yields_items_that_pass_the_pipeline():
    events = [
        DetectionEvent("A", "Metall", confidence=0.9, bounding_box=(0, 0, 1, 1)),
        DetectionEvent("B", "Glas", confidence=0.2, bounding_box=(0, 0, 1, 1)),  # dropped
        DetectionEvent("C", "Papier", confidence=0.8, bounding_box=(0, 0, 1, 1)),
    ]
    pipeline = ConfidenceFilter(0.7) | MaterialRoutingTransformer()
    results = list(ConveyorStream(events, pipeline))
    assert [r.item_name for r in results] == ["A", "C"]


def test_conveyor_stream_is_its_own_iterator():
    events = [DetectionEvent("A", "Metall", confidence=0.9, bounding_box=(0, 0, 1, 1))]
    stream = ConveyorStream(events, ConfidenceFilter(0.7) | MaterialRoutingTransformer())
    assert iter(stream) is stream


def test_conveyor_stream_raises_stop_iteration_when_exhausted():
    stream = ConveyorStream([], ConfidenceFilter(0.7) | MaterialRoutingTransformer())
    with pytest.raises(StopIteration):
        next(stream)