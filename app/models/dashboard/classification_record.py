"""ClassificationRecord: one result produced by the waste classifier."""

from datetime import datetime


class ClassificationRecord:
    """Stores a single waste classification result.

    This is the data the Dashboard & Analysis subsystem receives from the
    classification subsystem. Each record represents one classified item.
    """

    def __init__(self, record_id, predicted_category, confidence,
                 timestamp=None, actual_category=None):
        """Create a record and validate its values through the setters."""
        self._record_id = None
        self._predicted_category = None
        self._actual_category = None
        self._confidence = 0.0
        self._timestamp = None

        self.set_record_id(record_id)
        self.set_predicted_category(predicted_category)
        self.set_confidence(confidence)
        self.set_timestamp(timestamp if timestamp is not None else datetime.now())
        self.set_actual_category(actual_category)

    # ------------------------------------------------------------------
    # Initialization methods
    # ------------------------------------------------------------------
    @classmethod
    def from_dict(cls, data):
        """Build a record from a dictionary (e.g. JSON from the classifier)."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return cls(
            record_id=data["id"],
            predicted_category=data["predicted"],
            confidence=data.get("confidence", 0.0),
            timestamp=timestamp,
            actual_category=data.get("actual"),
        )

    def to_dict(self):
        """Convert the record to a dictionary, ready to send as JSON."""
        return {
            "id": self._record_id,
            "predicted": self._predicted_category,
            "actual": self._actual_category,
            "confidence": self._confidence,
            "timestamp": self._timestamp.isoformat(),
        }

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------
    def has_ground_truth(self):
        """True if the correct (actual) category is known."""
        return self._actual_category is not None

    def is_correct(self):
        """True if the prediction matches the actual category."""
        return self.has_ground_truth() and self._predicted_category == self._actual_category

    # ------------------------------------------------------------------
    # Getters and setters
    # ------------------------------------------------------------------
    def get_record_id(self):
        return self._record_id

    def set_record_id(self, record_id):
        if not isinstance(record_id, int) or record_id < 1:
            raise ValueError("record_id must be a positive integer")
        self._record_id = record_id

    def get_predicted_category(self):
        return self._predicted_category

    def set_predicted_category(self, category):
        if not isinstance(category, str) or not category.strip():
            raise ValueError("predicted_category must be a non-empty string")
        self._predicted_category = category.strip()

    def get_actual_category(self):
        return self._actual_category

    def set_actual_category(self, category):
        if category is not None and (not isinstance(category, str) or not category.strip()):
            raise ValueError("actual_category must be a non-empty string or None")
        self._actual_category = category.strip() if category else None

    def get_confidence(self):
        return self._confidence

    def set_confidence(self, confidence):
        if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be a number between 0 and 1")
        self._confidence = float(confidence)

    def get_timestamp(self):
        return self._timestamp

    def set_timestamp(self, timestamp):
        if not isinstance(timestamp, datetime):
            raise ValueError("timestamp must be a datetime object")
        self._timestamp = timestamp

    def __repr__(self):
        return (f"ClassificationRecord(id={self._record_id}, "
                f"predicted={self._predicted_category!r}, "
                f"actual={self._actual_category!r}, "
                f"confidence={self._confidence:.2f})")
