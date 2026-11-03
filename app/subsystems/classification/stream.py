"""Event-driven stream processing for the Waste Identification & Classification
subsystem (Home Assignment 2).

Simulates the conveyor-belt optical sorter described in the assignment: a stream
of raw detection events flows through a small pipeline of processing stages
(filter out low-confidence predictions, then transform the bounding box metrics
and visual tags into a material category and a conveyor routing code).
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
                 material_category: str, routing_code: str,
                 area: int = 0, size_class: str = "normal"):
        self.item_name = item_name
        self.material = material
        self.confidence = confidence
        self.material_category = material_category
        self.routing_code = routing_code
        self.area = area              # from the bounding box, in pixels
        self.size_class = size_class  # "small", "normal" or "oversize"

    def __repr__(self) -> str:
        return (f"RoutedItem(item_name={self.item_name!r}, category={self.material_category!r}, "
                f"routing_code={self.routing_code!r}, size_class={self.size_class!r})")


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


# Default category and conveyor lane for each material the classifier reports.
MATERIAL_ROUTING = {
    "Kunststoff": ("HDPE", "R-02"),
    "Metall": ("Steel", "R-04"),
    "Verbundstoff": ("Composite", "R-05"),
    "Papier": ("Paper", "R-06"),
    "Pappe": ("Cardboard", "R-07"),
    "Glas": ("Glass", "R-08"),
}

# A finer category when the visual tag (the item name) names the exact type.
# Keyed by material first, so a glass "Flasche" is never mistaken for PET.
TAG_ROUTING = {
    "Kunststoff": {
        "pet": ("PET", "R-01"),
        "flasche": ("PET", "R-01"),
        "bottle": ("PET", "R-01"),
    },
    "Metall": {
        "alu": ("Aluminium", "R-03"),
        "dose": ("Aluminium", "R-03"),
        "can": ("Aluminium", "R-03"),
    },
}

UNKNOWN_ROUTING = ("Unsorted", "R-00")
OVERSIZE_ROUTING = ("Oversize", "R-09")

# Bounding box area thresholds, in pixels.
SMALL_AREA = 2_500       # smaller than 50 x 50
OVERSIZE_AREA = 40_000   # larger than 200 x 200


def bounding_box_area(bounding_box: tuple) -> int:
    """Area of an (x, y, width, height) bounding box."""
    _x, _y, width, height = bounding_box
    return width * height


def size_class_for(area: int) -> str:
    """Turn a bounding box area into a size class the sorter can act on."""
    if area < SMALL_AREA:
        return "small"
    if area > OVERSIZE_AREA:
        return "oversize"
    return "normal"


class MaterialRoutingTransformer(StreamProcessor):
    """Turns a confirmed detection into a material category and conveyor routing code.

    Uses both halves of the payload: the visual tags (material + item name) decide
    the category, and the bounding box decides whether the item still fits the
    normal lane or has to go to the oversize lane.
    """

    def process(self, item: DetectionEvent) -> RoutedItem:
        category, code = self._category_for(item)

        area = bounding_box_area(item.bounding_box)
        size_class = size_class_for(area)
        if size_class == "oversize":
            code = OVERSIZE_ROUTING[1]  # too big for the normal lane

        return RoutedItem(item.item_name, item.material, item.confidence,
                          category, code, area, size_class)

    @staticmethod
    def _category_for(item: DetectionEvent) -> tuple:
        """Most specific match wins: the visual tag first, then the plain material."""
        tag = item.item_name.lower()
        for keyword, routing in TAG_ROUTING.get(item.material, {}).items():
            if keyword in tag:
                return routing
        return MATERIAL_ROUTING.get(item.material, UNKNOWN_ROUTING)


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
        side = rng.choice([30, 80, 80, 120, 250])  # mostly normal, a few small/oversize
        yield DetectionEvent(
            item_name=f"item-{i}",
            material=rng.choice(materials),
            confidence=round(rng.uniform(0.4, 1.0), 2),
            bounding_box=(rng.randint(0, 500), rng.randint(0, 500), side, side),
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
