"""Event-driven stream processing for the Waste Identification & Classification
subsystem (Home Assignment 2).

Simulates the conveyor-belt optical sorter described in the assignment: a stream
of raw detection events flows through a small pipeline of processing stages
(filter out low-confidence predictions, then transform into a material category
and a conveyor routing code).
"""

import random
from abc import ABC, abstractmethod


class DetectionEvent:
    """One raw detection payload, as if read off the conveyor belt's optical sorter."""

    def __init__(self, item_name: str, material: str, confidence: float, bounding_box: tuple):
        self.item_name = item_name
        self.material = material
        self.confidence = confidence
        self.bounding_box = bounding_box  # (x, y, width, height)

    def __repr__(self) -> str:
        return (f"DetectionEvent(item_name={self.item_name!r}, material={self.material!r}, "
                f"confidence={self.confidence})")


class RoutedItem:
    """Output of the pipeline: a detection that passed every stage, ready for routing."""

    def __init__(self, item_name: str, material: str, confidence: float,
                 material_category: str, routing_code: str):
        self.item_name = item_name
        self.material = material
        self.confidence = confidence
        self.material_category = material_category
        self.routing_code = routing_code

    def __repr__(self) -> str:
        return (f"RoutedItem(item_name={self.item_name!r}, category={self.material_category!r}, "
                f"routing_code={self.routing_code!r})")


# --- 1. Abstract Base Class --------------------------------------------------

class StreamProcessor(ABC):
    """One stage of the pipeline. Every stage must know how to process one item."""

    @abstractmethod
    def process(self, item):
        """Return the (possibly transformed) item, or None to drop it from the stream."""
        raise NotImplementedError

    # --- 3. Operator overloading --------------------------------------------

    def __or__(self, other):
        """`stage_a | stage_b` chains two stages into a Pipeline."""
        if not isinstance(other, StreamProcessor):
            return NotImplemented
        return Pipeline([self, other])


# --- 2. Inheritance & polymorphism: two concrete stages ---------------------

class ConfidenceFilter(StreamProcessor):
    """Drops detections the optical sorter wasn't confident about."""

    def __init__(self, min_confidence: float = 0.7):
        self.min_confidence = min_confidence

    def process(self, item: DetectionEvent):
        if item.confidence < self.min_confidence:
            return None  # dropped: low-confidence prediction
        return item


MATERIAL_ROUTING = {
    "Kunststoff": ("Plastic", "R-01"),
    "Metall": ("Metal", "R-02"),
    "Verbundstoff": ("Composite", "R-03"),
    "Papier": ("Paper", "R-04"),
    "Pappe": ("Paper", "R-04"),
    "Glas": ("Glass", "R-05"),
}
UNKNOWN_ROUTING = ("Unsorted", "R-00")


class MaterialRoutingTransformer(StreamProcessor):
    """Turns a confirmed detection into a material category and conveyor routing code."""

    def process(self, item: DetectionEvent) -> RoutedItem:
        category, code = MATERIAL_ROUTING.get(item.material, UNKNOWN_ROUTING)
        return RoutedItem(item.item_name, item.material, item.confidence, category, code)


# --- Pipeline: a chain of stages, built up with `|` --------------------------

class Pipeline(StreamProcessor):
    """A sequence of stages. Runs each one in order and stops early if an item is dropped."""

    def __init__(self, stages: list):
        self.stages = list(stages)

    def process(self, item):
        for stage in self.stages:
            if item is None:
                break
            item = stage.process(item)
        return item

    def __or__(self, other):
        """Extending a pipeline with `|` appends the new stage rather than nesting pipelines."""
        if isinstance(other, Pipeline):
            return Pipeline(self.stages + other.stages)
        if isinstance(other, StreamProcessor):
            return Pipeline(self.stages + [other])
        return NotImplemented


# --- 4. Iterators & generators ----------------------------------------------

def synthetic_detection_stream(count: int = 10, seed: int = None):
    """Generator: stands in for the conveyor belt, emitting one detection at a time."""
    rng = random.Random(seed)
    materials = list(MATERIAL_ROUTING.keys()) + ["Rest"]
    for i in range(count):
        yield DetectionEvent(
            item_name=f"item-{i}",
            material=rng.choice(materials),
            confidence=round(rng.uniform(0.4, 1.0), 2),
            bounding_box=(rng.randint(0, 500), rng.randint(0, 500), 80, 80),
        )


class ConveyorStream:
    """Consumes a raw event stream through a pipeline, yielding only what passes every stage.

    Implements the iterator protocol directly (__iter__/__next__) so it can be
    looped over with a plain `for item in ConveyorStream(...)`.
    """

    def __init__(self, events, pipeline: StreamProcessor):
        self._events = iter(events)
        self._pipeline = pipeline

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            raw_event = next(self._events)  # raises StopIteration once the stream ends
            result = self._pipeline.process(raw_event)
            if result is not None:
                return result