"""Database models for the Dashboard subsystem.

The dashboard reads classification results from the scans table (app/models/scan.py)
and stores its own data in four tables:

    dashboard_settings   DashboardSetting   where the dashboard gets its data from
    dashboard_snapshots  DashboardSnapshot  the summary numbers shown on the cards
    bin_statistics       BinStatistic       items per bin, for the doughnut chart
    daily_activity       DailyActivity      items per day, for the line chart

Columns are stored in "private" attributes (e.g. _total_items) and accessed through
getters and setters, which validate the values before they reach the database.
"""

from collections import Counter
from datetime import date, datetime, timezone

from app.extensions import db


def _now():
    """Current UTC time without timezone info (MySQL DATETIME has no timezone)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _scan_date(timestamp):
    """Day of a scan. Scan timestamps are ISO strings like '2026-10-31T18:05:12+00:00'."""
    if isinstance(timestamp, datetime):
        return timestamp.date()
    return date.fromisoformat(str(timestamp)[:10])


def _non_negative_int(value, name):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a whole number of 0 or more")
    return value


def _non_empty_text(value, name, max_length):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty text")
    if len(value.strip()) > max_length:
        raise ValueError(f"{name} must be at most {max_length} characters")
    return value.strip()


class DashboardSetting(db.Model):
    """How the dashboard gets its data: mock data or live scans, and how many days back."""

    __tablename__ = "dashboard_settings"

    id = db.Column(db.Integer, primary_key=True)
    _use_mock_data = db.Column("use_mock_data", db.Boolean, nullable=False, default=True)
    _time_range_days = db.Column("time_range_days", db.Integer, nullable=False, default=14)
    _updated_at = db.Column("updated_at", db.DateTime, nullable=False, default=_now)

    MAX_DAYS = 365

    def __init__(self, use_mock_data=True, time_range_days=14):
        super().__init__()
        self.set_use_mock_data(use_mock_data)
        self.set_time_range_days(time_range_days)

    # Initialization method
    @classmethod
    def get_or_create(cls):
        """Load the saved settings, or create and save the default settings."""
        setting = cls.query.first()
        if setting is None:
            setting = cls()
            db.session.add(setting)
            db.session.commit()
        return setting

    def to_dict(self):
        return {
            "use_mock_data": self._use_mock_data,
            "time_range_days": self._time_range_days,
            "updated_at": self._updated_at.isoformat() if self._updated_at else None,
        }

    # Getters and setters
    def get_use_mock_data(self):
        return self._use_mock_data

    def set_use_mock_data(self, use_mock_data):
        if not isinstance(use_mock_data, bool):
            raise ValueError("use_mock_data must be True or False")
        self._use_mock_data = use_mock_data
        self._updated_at = _now()

    def get_time_range_days(self):
        return self._time_range_days

    def set_time_range_days(self, days):
        _non_negative_int(days, "time_range_days")
        if not 1 <= days <= self.MAX_DAYS:
            raise ValueError(f"time_range_days must be between 1 and {self.MAX_DAYS}")
        self._time_range_days = days
        self._updated_at = _now()

    def get_updated_at(self):
        return self._updated_at

    def __repr__(self):
        return f"<DashboardSetting mock={self._use_mock_data} days={self._time_range_days}>"


class DashboardSnapshot(db.Model):
    """The dashboard's statistics at one point in time (one row per refresh)."""

    __tablename__ = "dashboard_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    _created_at = db.Column("created_at", db.DateTime, nullable=False, default=_now)
    _source = db.Column("source", db.String(10), nullable=False)
    _total_items = db.Column("total_items", db.Integer, nullable=False, default=0)
    _pfand_items = db.Column("pfand_items", db.Integer, nullable=False, default=0)
    _material_count = db.Column("material_count", db.Integer, nullable=False, default=0)

    bin_statistics = db.relationship("BinStatistic", back_populates="snapshot",
                                     cascade="all, delete-orphan", order_by="BinStatistic.id")
    daily_activity = db.relationship("DailyActivity", back_populates="snapshot",
                                     cascade="all, delete-orphan", order_by="DailyActivity.id")

    SOURCES = ("mock", "live")

    def __init__(self, source, total_items=0, pfand_items=0, material_count=0):
        super().__init__()
        self._created_at = _now()
        self.set_source(source)
        self.set_total_items(total_items)
        self.set_pfand_items(pfand_items)
        self.set_material_count(material_count)

    # Initialization method
    @classmethod
    def from_scans(cls, scans, source):
        """Calculate all statistics from a list of scans (dicts shaped like Scan.to_dict())."""
        snapshot = cls(
            source=source,
            total_items=len(scans),
            pfand_items=sum(1 for s in scans if s.get("is_pfand")),
            material_count=len({s["material"] for s in scans}),
        )
        for bin_type, count in Counter(s["bin_type"] for s in scans).most_common():
            snapshot.add_bin_statistic(BinStatistic(bin_type, count))
        per_day = Counter(_scan_date(s["timestamp"]) for s in scans)
        for day in sorted(per_day):
            snapshot.add_daily_activity(DailyActivity(day, per_day[day]))
        return snapshot

    def add_bin_statistic(self, statistic):
        if not isinstance(statistic, BinStatistic):
            raise TypeError("statistic must be a BinStatistic")
        self.bin_statistics.append(statistic)

    def add_daily_activity(self, activity):
        if not isinstance(activity, DailyActivity):
            raise TypeError("activity must be a DailyActivity")
        self.daily_activity.append(activity)

    def pfand_share(self):
        """Percentage of items that are Pfand (deposit) items, or None if there are no items."""
        if self._total_items == 0:
            return None
        return round(self._pfand_items / self._total_items * 100, 1)

    def to_dict(self):
        """Everything the dashboard page needs, ready to send as JSON."""
        return {
            "source": self._source,
            "created_at": self._created_at.isoformat(),
            "cards": {
                "total_items": self._total_items,
                "pfand_items": self._pfand_items,
                "pfand_share": self.pfand_share(),
                "material_count": self._material_count,
            },
            "bin_chart": {
                "labels": [s.get_bin_type() for s in self.bin_statistics],
                "values": [s.get_item_count() for s in self.bin_statistics],
            },
            "activity_chart": {
                "labels": [a.get_activity_date().isoformat() for a in self.daily_activity],
                "values": [a.get_item_count() for a in self.daily_activity],
            },
        }

    # Getters and setters
    def get_created_at(self):
        return self._created_at

    def get_source(self):
        return self._source

    def set_source(self, source):
        if source not in self.SOURCES:
            raise ValueError(f"source must be one of {self.SOURCES}")
        self._source = source

    def get_total_items(self):
        return self._total_items

    def set_total_items(self, total_items):
        self._total_items = _non_negative_int(total_items, "total_items")

    def get_pfand_items(self):
        return self._pfand_items

    def set_pfand_items(self, pfand_items):
        self._pfand_items = _non_negative_int(pfand_items, "pfand_items")

    def get_material_count(self):
        return self._material_count

    def set_material_count(self, material_count):
        self._material_count = _non_negative_int(material_count, "material_count")

    def __repr__(self):
        return f"<DashboardSnapshot {self._source} total={self._total_items}>"


class BinStatistic(db.Model):
    """How many items went into one bin type (e.g. Gelbe Tonne) in a snapshot."""

    __tablename__ = "bin_statistics"

    id = db.Column(db.Integer, primary_key=True)
    snapshot_id = db.Column(db.Integer, db.ForeignKey("dashboard_snapshots.id"), nullable=False)
    _bin_type = db.Column("bin_type", db.String(50), nullable=False)
    _item_count = db.Column("item_count", db.Integer, nullable=False)

    snapshot = db.relationship("DashboardSnapshot", back_populates="bin_statistics")

    def __init__(self, bin_type, item_count):
        super().__init__()
        self.set_bin_type(bin_type)
        self.set_item_count(item_count)

    def share_of(self, total_items):
        """This bin's percentage of all items."""
        if total_items <= 0:
            return 0.0
        return round(self._item_count / total_items * 100, 1)

    # Getters and setters
    def get_bin_type(self):
        return self._bin_type

    def set_bin_type(self, bin_type):
        self._bin_type = _non_empty_text(bin_type, "bin_type", 50)

    def get_item_count(self):
        return self._item_count

    def set_item_count(self, item_count):
        self._item_count = _non_negative_int(item_count, "item_count")

    def get_snapshot(self):
        return self.snapshot

    def __repr__(self):
        return f"<BinStatistic {self._bin_type}={self._item_count}>"


class DailyActivity(db.Model):
    """How many items were classified on one day in a snapshot."""

    __tablename__ = "daily_activity"

    id = db.Column(db.Integer, primary_key=True)
    snapshot_id = db.Column(db.Integer, db.ForeignKey("dashboard_snapshots.id"), nullable=False)
    _activity_date = db.Column("activity_date", db.Date, nullable=False)
    _item_count = db.Column("item_count", db.Integer, nullable=False)

    snapshot = db.relationship("DashboardSnapshot", back_populates="daily_activity")

    def __init__(self, activity_date, item_count):
        super().__init__()
        self.set_activity_date(activity_date)
        self.set_item_count(item_count)

    # Getters and setters
    def get_activity_date(self):
        return self._activity_date

    def set_activity_date(self, activity_date):
        if isinstance(activity_date, datetime) or not isinstance(activity_date, date):
            raise ValueError("activity_date must be a date")
        self._activity_date = activity_date

    def get_item_count(self):
        return self._item_count

    def set_item_count(self, item_count):
        self._item_count = _non_negative_int(item_count, "item_count")

    def get_snapshot(self):
        return self.snapshot

    def __repr__(self):
        return f"<DailyActivity {self._activity_date}={self._item_count}>"
