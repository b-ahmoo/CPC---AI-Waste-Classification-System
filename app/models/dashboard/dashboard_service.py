"""DashboardService: connects the data source to the dashboard UI."""

from .mock_data_generator import MockDataGenerator, DEFAULT_CATEGORIES
from .statistics_analyzer import StatisticsAnalyzer


class DashboardService:
    """Chooses the data source (mock or real) and prepares data for the UI.

    The Flask app calls get_dashboard_data() and sends the result to the
    browser, where Chart.js draws the cards and charts.
    """

    def __init__(self, use_mock_data=True, categories=None, record_provider=None):
        """Store the configuration. Call initialize() before using the service."""
        self._use_mock_data = True
        self._categories = []
        self._record_provider = None
        self._generator = None
        self._analyzer = None
        self._initialized = False

        self.set_use_mock_data(use_mock_data)
        self.set_categories(categories or DEFAULT_CATEGORIES)
        self.set_record_provider(record_provider)

    # ------------------------------------------------------------------
    # Initialization methods
    # ------------------------------------------------------------------
    def initialize(self, seed=None):
        """Create the mock generator and analyzer, then load the first data."""
        # Default categories keep their realistic weights; custom ones are equal.
        custom = None if self._categories == DEFAULT_CATEGORIES else self._categories
        self._generator = MockDataGenerator(categories=custom, seed=seed)
        self._analyzer = StatisticsAnalyzer(categories=self._categories)
        self._initialized = True
        self.refresh()

    def refresh(self):
        """Reload records from the current data source."""
        if not self._initialized:
            raise RuntimeError("call initialize() first")
        if self._use_mock_data:
            records = self._generator.generate()
        else:
            if self._record_provider is None:
                raise RuntimeError("real data mode needs a record_provider")
            records = self._record_provider()
        self._analyzer.load_records(records)

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------
    def get_dashboard_data(self):
        """Return everything the dashboard page needs, as plain data."""
        if not self._initialized:
            raise RuntimeError("call initialize() first")
        stats = self._analyzer.summary()
        activity = stats["daily_activity"]
        distribution = stats["category_distribution"]
        return {
            "source": "mock" if self._use_mock_data else "live",
            "cards": {
                "total_classifications": stats["total_classifications"],
                "waste_categories": stats["category_count"],
                "accuracy": stats["accuracy"],
            },
            "category_chart": {
                "labels": list(distribution.keys()),
                "values": list(distribution.values()),
            },
            "activity_chart": {
                "labels": list(activity.keys()),
                "values": list(activity.values()),
            },
        }

    # ------------------------------------------------------------------
    # Getters and setters
    # ------------------------------------------------------------------
    def get_use_mock_data(self):
        return self._use_mock_data

    def set_use_mock_data(self, use_mock_data):
        if not isinstance(use_mock_data, bool):
            raise ValueError("use_mock_data must be True or False")
        self._use_mock_data = use_mock_data

    def get_categories(self):
        return list(self._categories)

    def set_categories(self, categories):
        if not categories:
            raise ValueError("categories must not be empty")
        self._categories = list(categories)
        if self._analyzer is not None:
            self._analyzer.set_categories(self._categories)

    def get_record_provider(self):
        return self._record_provider

    def set_record_provider(self, record_provider):
        """Function that returns real ClassificationRecord objects."""
        if record_provider is not None and not callable(record_provider):
            raise ValueError("record_provider must be a function")
        self._record_provider = record_provider

    def get_analyzer(self):
        return self._analyzer

    def is_initialized(self):
        return self._initialized
