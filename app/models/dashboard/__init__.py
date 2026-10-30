"""Dashboard subsystem classes (statistical dashboard and analysis).

Classes:
    ClassificationRecord  - one classification result
    MockDataGenerator     - creates mock records while the classifier is in development
    StatisticsAnalyzer    - calculates the dashboard statistics
    DashboardService      - picks the data source and prepares data for the UI
"""

from .classification_record import ClassificationRecord
from .mock_data_generator import MockDataGenerator
from .statistics_analyzer import StatisticsAnalyzer
from .dashboard_service import DashboardService

__all__ = [
    "ClassificationRecord",
    "MockDataGenerator",
    "StatisticsAnalyzer",
    "DashboardService",
]
