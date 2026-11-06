"""Event-driven stream processing for the Statistical Dashboard subsystem (Home Assignment 2).

Scenario: AI-Powered Waste Sorting & Recycling Assistant. Optical sorters on the
conveyor belts send a continuous stream of image-recognition payloads. The
dashboard pipeline:

    1. filters out low-confidence predictions (and tiny noise detections),
    2. transforms visual tags and bounding boxes into material categories
       (PET, HDPE, Aluminium, ...) and conveyor routing codes,
    3. aggregates the processed stream into live dashboard statistics.

OOP concepts demonstrated:
    Abstract Base Classes   StreamProcessor, EventFilter, EventTransformer (@abstractmethod)
    Inheritance/polymorphism  every stage is used through the same process() call
    Operator overloading    stage_a + stage_b builds a ProcessingPipeline (__add__)
    Iterators & generators  SorterEventStream (__iter__/__next__), stream(), tumbling_windows()
"""

import random
from abc import ABC, abstractmethod
from collections import Counter
from datetime import datetime, timedelta, timezone


# --- Events -------------------------------------------------------------------

class SortingEvent:
    """One raw payload from a conveyor belt's optical sorter."""

    def __init__(self, event_id, belt_id, visual_tags, confidence, bounding_box, timestamp=None):
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if len(bounding_box) != 4 or bounding_box[2] < 0 or bounding_box[3] < 0:
            raise ValueError("bounding_box must be (x, y, width, height) with a non-negative size")
        self.event_id = event_id
        self.belt_id = belt_id
        self.visual_tags = [tag.lower() for tag in visual_tags]
        self.confidence = confidence
        self.bounding_box = tuple(bounding_box)  # (x, y, width, height) in pixels
        self.timestamp = timestamp or datetime.now(timezone.utc)
        # Filled in by the transform stages:
        self.material_category = None
        self.routing_code = None

    @property
    def area(self):
        """Bounding box area in pixels, used as a size estimate."""
        return self.bounding_box[2] * self.bounding_box[3]

    def __repr__(self):
        return (f"SortingEvent(id={self.event_id}, belt={self.belt_id}, tags={self.visual_tags}, "
                f"confidence={self.confidence}, category={self.material_category}, "
                f"route={self.routing_code})")


# --- 1. Abstract Base Classes ---------------------------------------------------

class StreamProcessor(ABC):
    """Interface contract for every pipeline stage."""

    @abstractmethod
    def process(self, event):
        """Return the (possibly updated) event, or None to drop it from the stream."""

    @property
    def name(self):
        return type(self).__name__

    # --- 3. Operator overloading -----------------------------------------------
    def __add__(self, other):
        """stage_a + stage_b  ->  ProcessingPipeline([stage_a, stage_b])"""
        if not isinstance(other, StreamProcessor):
            return NotImplemented
        return ProcessingPipeline([self]) + other

    def __repr__(self):
        return f"{self.name}()"


class EventFilter(StreamProcessor):
    """A stage that keeps or drops events. Subclasses only decide *whether* to keep."""

    def __init__(self):
        self.passed = 0
        self.dropped = 0

    @abstractmethod
    def accepts(self, event):
        """True if the event should stay in the stream."""

    def process(self, event):
        if self.accepts(event):
            self.passed += 1
            return event
        self.dropped += 1
        return None


class EventTransformer(StreamProcessor):
    """A stage that changes events. Subclasses only decide *how* to change them."""

    @abstractmethod
    def transform(self, event):
        """Return the transformed event."""

    def process(self, event):
        return self.transform(event)


# --- 2. Inheritance & polymorphism: concrete stages ---------------------------

class ConfidenceFilter(EventFilter):
    """Drops predictions the optical sorter wasn't confident about."""

    def __init__(self, min_confidence=0.75):
        super().__init__()
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")
        self.min_confidence = min_confidence

    def accepts(self, event):
        return event.confidence >= self.min_confidence

    def __repr__(self):
        return f"ConfidenceFilter(min_confidence={self.min_confidence})"


class BoundingBoxFilter(EventFilter):
    """Drops detections too small to be a real item (dust, reflections, label scraps)."""

    def __init__(self, min_area=400):
        super().__init__()
        if min_area < 0:
            raise ValueError("min_area must be 0 or more")
        self.min_area = min_area

    def accepts(self, event):
        return event.area >= self.min_area

    def __repr__(self):
        return f"BoundingBoxFilter(min_area={self.min_area})"


class MaterialCategoryTransformer(EventTransformer):
    """Turns the model's visual tags into a recycling material category."""

    # First matching tag wins, so the more specific tags come first.
    TAG_TO_CATEGORY = {
        "pet": "PET", "water bottle": "PET", "soda bottle": "PET",
        "hdpe": "HDPE", "milk jug": "HDPE", "detergent bottle": "HDPE", "shampoo bottle": "HDPE",
        "aluminium": "Aluminium", "aluminum": "Aluminium", "drink can": "Aluminium", "foil": "Aluminium",
        "tin can": "Steel", "steel": "Steel",
        "glass": "Glass", "jar": "Glass",
        "cardboard": "Cardboard", "carton box": "Cardboard",
        "paper": "Paper", "newspaper": "Paper",
        "tetra pak": "Composite", "beverage carton": "Composite",
    }
    UNKNOWN = "Residual"

    def transform(self, event):
        event.material_category = next(
            (self.TAG_TO_CATEGORY[tag] for tag in event.visual_tags if tag in self.TAG_TO_CATEGORY),
            self.UNKNOWN,
        )
        return event


class RoutingCodeTransformer(EventTransformer):
    """Builds the conveyor routing code: <lane>-<category>-<size>, e.g. 'L1-PET-M'.

    The lane tells the diverter which output chute to use; the size class
    (from the bounding box area) lets the sorter adjust its air-jet strength.
    """

    LANES = {"PET": "L1", "HDPE": "L2", "Aluminium": "L3", "Steel": "L3", "Glass": "L4",
             "Paper": "L5", "Cardboard": "L5", "Composite": "L6"}
    REJECT_LANE = "L0"
    SIZE_LIMITS = ((5_000, "S"), (20_000, "M"))  # area in pixels; anything larger is "L"

    def size_class(self, area):
        for limit, label in self.SIZE_LIMITS:
            if area < limit:
                return label
        return "L"

    def transform(self, event):
        if event.material_category is None:
            raise ValueError("run MaterialCategoryTransformer before RoutingCodeTransformer")
        lane = self.LANES.get(event.material_category, self.REJECT_LANE)
        event.routing_code = f"{lane}-{event.material_category}-{self.size_class(event.area)}"
        return event


class DashboardAggregator(StreamProcessor):
    """Keeps running statistics for the dashboard while letting every event pass through."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.total = 0
        self.by_category = Counter()
        self.by_lane = Counter()
        self.by_belt = Counter()
        self._confidence_sum = 0.0

    def process(self, event):
        self.total += 1
        self.by_category[event.material_category or MaterialCategoryTransformer.UNKNOWN] += 1
        if event.routing_code:
            self.by_lane[event.routing_code.split("-")[0]] += 1
        self.by_belt[event.belt_id] += 1
        self._confidence_sum += event.confidence
        return event

    def snapshot(self):
        """The current statistics, in the shape the dashboard displays them."""
        return {
            "total_items": self.total,
            "average_confidence": round(self._confidence_sum / self.total, 3) if self.total else None,
            "category_share": {c: round(n / self.total * 100, 1)
                               for c, n in self.by_category.most_common()} if self.total else {},
            "items_per_lane": dict(sorted(self.by_lane.items())),
            "items_per_belt": dict(sorted(self.by_belt.items())),
        }


# --- The pipeline: a chain of stages, built with + ---------------------------

class ProcessingPipeline(StreamProcessor):
    """Runs its stages in order and stops as soon as a stage drops the event."""

    def __init__(self, stages=None):
        self.stages = []
        for stage in stages or []:
            self.add_stage(stage)

    def add_stage(self, stage):
        if not isinstance(stage, StreamProcessor):
            raise TypeError("a stage must be a StreamProcessor")
        self.stages.append(stage)

    def process(self, event):
        for stage in self.stages:
            event = stage.process(event)  # polymorphism: each stage does its own thing
            if event is None:
                return None
        return event

    def __add__(self, other):
        """pipeline + stage appends the stage; pipeline + pipeline joins both (no nesting)."""
        if isinstance(other, ProcessingPipeline):
            return ProcessingPipeline(self.stages + other.stages)
        if isinstance(other, StreamProcessor):
            return ProcessingPipeline(self.stages + [other])
        return NotImplemented

    def __len__(self):
        return len(self.stages)

    def __iter__(self):
        return iter(self.stages)

    # --- 4. Generator: process a stream lazily, one event at a time ------------
    def stream(self, events):
        """Yield only the events that make it through every stage."""
        for event in events:
            result = self.process(event)
            if result is not None:
                yield result

    def __repr__(self):
        return " + ".join(repr(stage) for stage in self.stages) or "ProcessingPipeline([])"


# --- 4. Iterators & generators: the event source and windowing ---------------

class SorterEventStream:
    """Simulated optical-sorter feed, implementing the iterator protocol directly.

    `for event in SorterEventStream(count=100)` pulls events one by one; nothing
    is generated before it is asked for. count=None makes an endless stream.
    """

    ITEMS = [
        (["pet", "water bottle"], 12), (["hdpe", "milk jug"], 7), (["detergent bottle"], 4),
        (["aluminium", "drink can"], 9), (["tin can"], 4), (["glass", "jar"], 5),
        (["cardboard"], 8), (["newspaper", "paper"], 6), (["tetra pak"], 5),
        (["food scraps"], 3), (["dust"], 2),
    ]

    def __init__(self, count=100, belts=("belt-A", "belt-B"), seed=None,
                 start=None, interval_seconds=0.5):
        if count is not None and count < 0:
            raise ValueError("count must be 0 or more (or None for an endless stream)")
        self.count = count
        self.belts = list(belts)
        self._rng = random.Random(seed)
        self._clock = start or datetime.now(timezone.utc)
        self._interval = timedelta(seconds=interval_seconds)
        self._emitted = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.count is not None and self._emitted >= self.count:
            raise StopIteration
        self._emitted += 1
        tags = self._rng.choices([i[0] for i in self.ITEMS], weights=[i[1] for i in self.ITEMS])[0]
        size = self._rng.choice((10, 40, 90, 160))  # tiny boxes are noise
        event = SortingEvent(
            event_id=self._emitted,
            belt_id=self._rng.choice(self.belts),
            visual_tags=tags,
            confidence=round(self._rng.triangular(0.4, 1.0, 0.95), 2),  # mostly confident
            bounding_box=(self._rng.randint(0, 600), self._rng.randint(0, 400), size, size),
            timestamp=self._clock,
        )
        self._clock += self._interval
        return event


def tumbling_windows(events, size):
    """Generator: group a stream into consecutive batches of `size` events.

    The dashboard refreshes once per window instead of once per event.
    """
    if size < 1:
        raise ValueError("size must be at least 1")
    window = []
    for event in events:
        window.append(event)
        if len(window) == size:
            yield window
            window = []
    if window:
        yield window


def build_default_pipeline(min_confidence=0.75, min_area=400, aggregator=None):
    """The dashboard's standard pipeline, composed with the + operator."""
    return (ConfidenceFilter(min_confidence)
            + BoundingBoxFilter(min_area)
            + MaterialCategoryTransformer()
            + RoutingCodeTransformer()
            + (aggregator or DashboardAggregator()))


if __name__ == "__main__":
    aggregator = DashboardAggregator()
    pipeline = build_default_pipeline(aggregator=aggregator)
    print("Pipeline:", pipeline)
    for number, window in enumerate(tumbling_windows(pipeline.stream(SorterEventStream(count=200, seed=7)), 25), 1):
        stats = aggregator.snapshot()
        print(f"Window {number}: {len(window)} items | total {stats['total_items']} | "
              f"avg confidence {stats['average_confidence']} | top {list(stats['category_share'].items())[:3]}")
    confidence_filter, box_filter = pipeline.stages[0], pipeline.stages[1]
    print(f"Dropped: {confidence_filter.dropped} low-confidence, {box_filter.dropped} too small")
    print("Lanes:", aggregator.snapshot()["items_per_lane"])
