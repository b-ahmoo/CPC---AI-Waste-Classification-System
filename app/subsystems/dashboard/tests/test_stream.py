"""Tests for the dashboard's event-driven stream processing framework (Home Assignment 2).

Run inside Docker:  docker compose exec web pytest app/subsystems/dashboard/tests
"""

import inspect

import pytest

from app.subsystems.dashboard.stream import (
    BoundingBoxFilter, ConfidenceFilter, DashboardAggregator, EventFilter, EventTransformer,
    MaterialCategoryTransformer, ProcessingPipeline, RoutingCodeTransformer, SorterEventStream,
    SortingEvent, StreamProcessor, build_default_pipeline, tumbling_windows)


def event(tags=("pet",), confidence=0.9, size=100, belt="belt-A", event_id=1):
    return SortingEvent(event_id, belt, list(tags), confidence, (0, 0, size, size))


# --- 1. Abstract Base Classes -------------------------------------------------

@pytest.mark.parametrize("abstract_class", [StreamProcessor, EventFilter, EventTransformer])
def test_abstract_classes_cannot_be_instantiated(abstract_class):
    with pytest.raises(TypeError):
        abstract_class()


def test_abstract_methods_are_declared():
    assert StreamProcessor.__abstractmethods__ == {"process"}
    assert EventFilter.__abstractmethods__ == {"accepts"}
    assert EventTransformer.__abstractmethods__ == {"transform"}


def test_subclass_missing_abstract_method_fails():
    class Incomplete(EventFilter):
        pass

    with pytest.raises(TypeError):
        Incomplete()


# --- 2. Inheritance & polymorphism ---------------------------------------------

def test_every_stage_is_a_stream_processor():
    for stage in build_default_pipeline():
        assert isinstance(stage, StreamProcessor)


def test_confidence_filter():
    f = ConfidenceFilter(min_confidence=0.75)
    assert f.process(event(confidence=0.5)) is None
    kept = event(confidence=0.8)
    assert f.process(kept) is kept
    assert (f.passed, f.dropped) == (1, 1)


def test_bounding_box_filter_drops_tiny_detections():
    f = BoundingBoxFilter(min_area=400)
    assert f.process(event(size=10)) is None       # 100 px²
    assert f.process(event(size=40)) is not None   # 1600 px²


@pytest.mark.parametrize("tags, category", [
    (["pet", "water bottle"], "PET"),
    (["milk jug"], "HDPE"),
    (["drink can"], "Aluminium"),
    (["Aluminum"], "Aluminium"),
    (["glass", "jar"], "Glass"),
    (["food scraps"], "Residual"),
])
def test_material_category_transformer(tags, category):
    assert MaterialCategoryTransformer().process(event(tags=tags)).material_category == category


@pytest.mark.parametrize("tags, size, code", [
    (["pet"], 40, "L1-PET-S"),        # 1 600 px²
    (["hdpe"], 100, "L2-HDPE-M"),     # 10 000 px²
    (["drink can"], 160, "L3-Aluminium-L"),
    (["food scraps"], 90, "L0-Residual-M"),
])
def test_routing_code_transformer(tags, size, code):
    e = MaterialCategoryTransformer().process(event(tags=tags, size=size))
    assert RoutingCodeTransformer().process(e).routing_code == code


def test_routing_needs_a_category_first():
    with pytest.raises(ValueError):
        RoutingCodeTransformer().process(event())


def test_same_call_different_behaviour():
    """Polymorphism: one loop, one method name, four different behaviours."""
    stages = [ConfidenceFilter(), BoundingBoxFilter(), MaterialCategoryTransformer(), RoutingCodeTransformer()]
    e = event(tags=["milk jug"], confidence=0.95, size=100)
    for stage in stages:
        e = stage.process(e)
    assert (e.material_category, e.routing_code) == ("HDPE", "L2-HDPE-M")


# --- 3. Operator overloading ----------------------------------------------------

def test_plus_builds_a_flat_pipeline():
    a, b, c = ConfidenceFilter(), BoundingBoxFilter(), MaterialCategoryTransformer()
    pipeline = a + b + c
    assert isinstance(pipeline, ProcessingPipeline)
    assert list(pipeline) == [a, b, c]


def test_pipeline_plus_pipeline_joins_stages():
    left = ConfidenceFilter() + BoundingBoxFilter()
    right = MaterialCategoryTransformer() + RoutingCodeTransformer()
    assert len(left + right) == 4


def test_adding_something_else_is_rejected():
    with pytest.raises(TypeError):
        ConfidenceFilter() + 5


def test_pipeline_stops_at_first_drop():
    aggregator = DashboardAggregator()
    pipeline = ConfidenceFilter(0.9) + MaterialCategoryTransformer() + aggregator
    assert pipeline.process(event(confidence=0.5)) is None
    assert aggregator.total == 0


# --- 4. Iterators & generators --------------------------------------------------

def test_sorter_stream_is_an_iterator():
    stream = SorterEventStream(count=3, seed=1)
    assert iter(stream) is stream
    assert [next(stream).event_id for _ in range(3)] == [1, 2, 3]
    with pytest.raises(StopIteration):
        next(stream)


def test_sorter_stream_is_repeatable_with_a_seed():
    first = [(e.visual_tags, e.confidence) for e in SorterEventStream(count=20, seed=5)]
    second = [(e.visual_tags, e.confidence) for e in SorterEventStream(count=20, seed=5)]
    assert first == second


def test_endless_stream_is_lazy():
    stream = SorterEventStream(count=None, seed=1)
    assert [next(stream).event_id for _ in range(1000)][-1] == 1000


def test_pipeline_stream_is_a_generator():
    pipeline = build_default_pipeline()
    result = pipeline.stream(SorterEventStream(count=50, seed=2))
    assert inspect.isgenerator(result)
    for e in result:
        assert e.confidence >= 0.75 and e.area >= 400 and e.routing_code


def test_tumbling_windows():
    windows = list(tumbling_windows(range(10), 4))
    assert windows == [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]]
    assert inspect.isgenerator(tumbling_windows([], 3))
    with pytest.raises(ValueError):
        list(tumbling_windows([1], 0))


# --- Dashboard statistics end to end ---------------------------------------------

def test_aggregator_builds_dashboard_statistics():
    aggregator = DashboardAggregator()
    pipeline = build_default_pipeline(aggregator=aggregator)
    events = [event(["pet"], 0.9, 100, "belt-A", 1), event(["pet"], 0.8, 100, "belt-B", 2),
              event(["drink can"], 1.0, 100, "belt-A", 3), event(["glass"], 0.3, 100, "belt-A", 4)]
    passed = list(pipeline.stream(events))
    stats = aggregator.snapshot()
    assert len(passed) == 3
    assert stats["total_items"] == 3
    assert stats["average_confidence"] == 0.9
    assert stats["category_share"] == {"PET": 66.7, "Aluminium": 33.3}
    assert stats["items_per_lane"] == {"L1": 2, "L3": 1}
    assert stats["items_per_belt"] == {"belt-A": 2, "belt-B": 1}


def test_empty_aggregator():
    assert DashboardAggregator().snapshot()["average_confidence"] is None


def test_invalid_event_values():
    with pytest.raises(ValueError):
        event(confidence=1.5)
    with pytest.raises(ValueError):
        SortingEvent(1, "belt-A", ["pet"], 0.9, (0, 0, -5, 10))
