"""Unit tests for the Dashboard & Analysis subsystem.

Run from the project root:  python -m unittest tests.test_dashboard
"""

import unittest
from datetime import datetime

from app.subsystems.dashboard import (
    ClassificationRecord, MockDataGenerator, StatisticsAnalyzer, DashboardService,
)


def make_record(record_id, predicted, actual=None, day="2026-10-27"):
    return ClassificationRecord(record_id, predicted, 0.9,
                                datetime.fromisoformat(day + "T10:00:00"), actual)


class TestClassificationRecord(unittest.TestCase):
    def test_constructor_and_getters(self):
        r = make_record(1, "Plastic", "Plastic")
        self.assertEqual(r.get_predicted_category(), "Plastic")
        self.assertTrue(r.is_correct())

    def test_setter_validation(self):
        r = make_record(1, "Plastic")
        with self.assertRaises(ValueError):
            r.set_confidence(1.5)
        with self.assertRaises(ValueError):
            r.set_predicted_category("")

    def test_dict_round_trip(self):
        r = make_record(3, "Glass", "Metal")
        copy = ClassificationRecord.from_dict(r.to_dict())
        self.assertEqual(copy.to_dict(), r.to_dict())
        self.assertFalse(copy.is_correct())


class TestMockDataGenerator(unittest.TestCase):
    def test_generates_requested_amount(self):
        gen = MockDataGenerator(record_count=50, seed=1)
        self.assertEqual(len(gen.generate()), 50)

    def test_seed_gives_same_data(self):
        a = [r.get_predicted_category() for r in MockDataGenerator(seed=7).generate()]
        b = [r.get_predicted_category() for r in MockDataGenerator(seed=7).generate()]
        self.assertEqual(a, b)

    def test_setter_validation(self):
        gen = MockDataGenerator()
        with self.assertRaises(ValueError):
            gen.set_accuracy(2)
        with self.assertRaises(ValueError):
            gen.set_record_count(0)


class TestStatisticsAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = StatisticsAnalyzer(
            records=[
                make_record(1, "Plastic", "Plastic", "2026-10-26"),
                make_record(2, "Plastic", "Paper", "2026-10-27"),
                make_record(3, "Paper", "Paper", "2026-10-27"),
                make_record(4, "Glass"),  # no ground truth
            ],
            categories=["Plastic", "Paper", "Glass", "Metal"],
        )

    def test_totals(self):
        self.assertEqual(self.analyzer.total_classifications(), 4)
        self.assertEqual(self.analyzer.category_count(), 3)

    def test_distribution_includes_empty_categories(self):
        self.assertEqual(self.analyzer.category_distribution(),
                         {"Plastic": 2, "Paper": 1, "Glass": 1, "Metal": 0})

    def test_accuracy_ignores_unlabelled(self):
        self.assertEqual(self.analyzer.accuracy(), 66.7)

    def test_daily_activity(self):
        self.assertEqual(self.analyzer.daily_activity(),
                         {"2026-10-26": 1, "2026-10-27": 3})

    def test_empty_data(self):
        empty = StatisticsAnalyzer()
        self.assertEqual(empty.total_classifications(), 0)
        self.assertIsNone(empty.accuracy())


class TestDashboardService(unittest.TestCase):
    def test_mock_mode(self):
        service = DashboardService()
        service.initialize(seed=1)
        data = service.get_dashboard_data()
        self.assertEqual(data["source"], "mock")
        self.assertEqual(data["cards"]["total_classifications"], 250)

    def test_real_mode_uses_provider(self):
        service = DashboardService(use_mock_data=False,
                                   record_provider=lambda: [make_record(1, "Metal", "Metal")])
        service.initialize()
        data = service.get_dashboard_data()
        self.assertEqual(data["source"], "live")
        self.assertEqual(data["cards"]["accuracy"], 100.0)

    def test_must_initialize_first(self):
        with self.assertRaises(RuntimeError):
            DashboardService().get_dashboard_data()


if __name__ == "__main__":
    unittest.main()
