"""MockDataGenerator: creates realistic fake classification records.

Used while the classification subsystem is still being developed, so the
dashboard can be built and tested with data in the correct format.
"""

import random
from datetime import datetime, timedelta

from .classification_record import ClassificationRecord

DEFAULT_CATEGORIES = ["Plastic", "Paper", "Glass", "Metal", "Organic", "E-waste"]
DEFAULT_WEIGHTS = [0.30, 0.22, 0.10, 0.12, 0.20, 0.06]


class MockDataGenerator:
    """Generates mock ClassificationRecord objects."""

    def __init__(self, categories=None, weights=None, record_count=250,
                 days=14, accuracy=0.87, seed=None):
        """Store the generator settings and prepare the random generator."""
        self._categories = []
        self._weights = []
        self._record_count = 0
        self._days = 0
        self._accuracy = 0.0
        self._rng = None

        self.set_categories(categories or DEFAULT_CATEGORIES,
                            weights or (DEFAULT_WEIGHTS if categories is None else None))
        self.set_record_count(record_count)
        self.set_days(days)
        self.set_accuracy(accuracy)
        self.initialize_random(seed)

    # ------------------------------------------------------------------
    # Initialization methods
    # ------------------------------------------------------------------
    def initialize_random(self, seed=None):
        """Set up the random generator. A fixed seed gives repeatable data."""
        self._rng = random.Random(seed)

    def configure(self, record_count=None, days=None, accuracy=None):
        """Change several settings at once."""
        if record_count is not None:
            self.set_record_count(record_count)
        if days is not None:
            self.set_days(days)
        if accuracy is not None:
            self.set_accuracy(accuracy)

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------
    def generate(self):
        """Create the list of mock classification records."""
        now = datetime.now()
        records = []
        for record_id in range(1, self._record_count + 1):
            actual = self._rng.choices(self._categories, weights=self._weights)[0]
            correct = self._rng.random() < self._accuracy
            if correct or len(self._categories) == 1:
                predicted = actual
                confidence = self._rng.uniform(0.70, 1.00)
            else:
                others = [c for c in self._categories if c != actual]
                predicted = self._rng.choice(others)
                confidence = self._rng.uniform(0.40, 0.75)

            timestamp = now - timedelta(seconds=self._rng.uniform(0, self._days * 86400))
            records.append(ClassificationRecord(
                record_id=record_id,
                predicted_category=predicted,
                confidence=round(confidence, 2),
                timestamp=timestamp,
                actual_category=actual,
            ))
        return records

    # ------------------------------------------------------------------
    # Getters and setters
    # ------------------------------------------------------------------
    def get_categories(self):
        return list(self._categories)

    def get_weights(self):
        return list(self._weights)

    def set_categories(self, categories, weights=None):
        """Set the categories and (optionally) how often each one appears."""
        if not categories:
            raise ValueError("categories must not be empty")
        if weights is None:
            weights = [1.0] * len(categories)
        if len(weights) != len(categories):
            raise ValueError("weights must have one value per category")
        if any(w < 0 for w in weights) or sum(weights) == 0:
            raise ValueError("weights must be non-negative and not all zero")
        self._categories = list(categories)
        self._weights = list(weights)

    def get_record_count(self):
        return self._record_count

    def set_record_count(self, record_count):
        if not isinstance(record_count, int) or record_count < 1:
            raise ValueError("record_count must be a positive integer")
        self._record_count = record_count

    def get_days(self):
        return self._days

    def set_days(self, days):
        if not isinstance(days, int) or days < 1:
            raise ValueError("days must be a positive integer")
        self._days = days

    def get_accuracy(self):
        return self._accuracy

    def set_accuracy(self, accuracy):
        if not isinstance(accuracy, (int, float)) or not 0.0 <= accuracy <= 1.0:
            raise ValueError("accuracy must be between 0 and 1")
        self._accuracy = float(accuracy)
