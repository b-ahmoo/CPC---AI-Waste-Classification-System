"""StatisticsAnalyzer: calculates the statistics shown on the dashboard."""

from collections import Counter

from .classification_record import ClassificationRecord


class StatisticsAnalyzer:
    """Computes totals, category distribution, accuracy and daily activity."""

    def __init__(self, records=None, categories=None):
        """Store the records to analyse and the list of known categories."""
        self._records = []
        self._categories = []
        self.load_records(records or [])
        self.set_categories(categories or [])

    # ------------------------------------------------------------------
    # Initialization methods
    # ------------------------------------------------------------------
    def load_records(self, records):
        """Load (or replace) the records to analyse."""
        self.set_records(records)

    def add_record(self, record):
        """Add one new record, e.g. when the classifier produces a result."""
        if not isinstance(record, ClassificationRecord):
            raise TypeError("record must be a ClassificationRecord")
        self._records.append(record)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    def total_classifications(self):
        return len(self._records)

    def category_distribution(self):
        """Number of items per predicted category (known categories first)."""
        counts = Counter(r.get_predicted_category() for r in self._records)
        distribution = {c: counts.get(c, 0) for c in self._categories}
        for category, count in counts.items():
            if category not in distribution:
                distribution[category] = count
        return distribution

    def category_count(self):
        """How many different categories actually appear in the data."""
        return sum(1 for count in self.category_distribution().values() if count > 0)

    def accuracy(self):
        """Percentage of correct predictions, or None if nothing can be checked."""
        labelled = [r for r in self._records if r.has_ground_truth()]
        if not labelled:
            return None
        correct = sum(1 for r in labelled if r.is_correct())
        return round(correct / len(labelled) * 100, 1)

    def average_confidence(self):
        if not self._records:
            return None
        return round(sum(r.get_confidence() for r in self._records) / len(self._records), 2)

    def daily_activity(self):
        """Classifications per day, sorted by date: {'2026-10-27': 14, ...}."""
        counts = Counter(r.get_timestamp().date().isoformat() for r in self._records)
        return dict(sorted(counts.items()))

    def summary(self):
        """All statistics in one dictionary."""
        return {
            "total_classifications": self.total_classifications(),
            "category_count": self.category_count(),
            "accuracy": self.accuracy(),
            "average_confidence": self.average_confidence(),
            "category_distribution": self.category_distribution(),
            "daily_activity": self.daily_activity(),
        }

    # ------------------------------------------------------------------
    # Getters and setters
    # ------------------------------------------------------------------
    def get_records(self):
        return list(self._records)

    def set_records(self, records):
        if not all(isinstance(r, ClassificationRecord) for r in records):
            raise TypeError("all records must be ClassificationRecord objects")
        self._records = list(records)

    def get_categories(self):
        return list(self._categories)

    def set_categories(self, categories):
        if not all(isinstance(c, str) and c.strip() for c in categories):
            raise ValueError("categories must be non-empty strings")
        self._categories = list(categories)
