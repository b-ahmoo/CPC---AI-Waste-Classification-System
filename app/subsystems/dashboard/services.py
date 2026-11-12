"""Dashboard logic: where the data comes from and how a snapshot is built.

Live data comes from the classification subsystem's scans table. Until there are
real scans, mock scans are generated with the same material -> bin rules
(app/subsystems/classification/rules.json), so the dashboard looks realistic.
"""

import json
import logging
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import false, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.dashboard import DashboardSetting, DashboardSnapshot, _scan_date
from app.models.scan import Scan
from app.subsystems.dashboard.errors import DataSourceError, InvalidFilterError

logger = logging.getLogger(__name__)

RULES_PATH = Path(__file__).resolve().parent.parent / "classification" / "rules.json"

# (item name, material, is Pfand, how common)
MOCK_ITEMS = [
    ("PET bottle", "Kunststoff", True, 12),
    ("Yogurt cup", "Kunststoff", False, 10),
    ("Drink can", "Metall", True, 8),
    ("Tin can", "Metall", False, 5),
    ("Juice carton", "Verbundstoff", False, 6),
    ("Newspaper", "Papier", False, 9),
    ("Cardboard box", "Pappe", False, 8),
    ("Glass jar", "Glas", False, 6),
    ("Banana peel", "Bio", False, 10),
    ("Battery", "Batterie", False, 2),
    ("Old phone charger", "Elektro", False, 2),
    ("Used tissue", "Rest", False, 7),
]


def load_bin_rules(path=RULES_PATH):
    """The classification subsystem's rules: material -> bin, and the Pfand bin."""
    try:
        with open(path, encoding="utf-8") as f:
            rules = json.load(f)
        return rules["material_to_bin"], rules["pfand"]["bin"], rules["unknown_label"]
    except (OSError, json.JSONDecodeError, KeyError) as error:
        # Chain the original error so the log shows the real cause.
        raise DataSourceError("The bin rules could not be loaded.") from error


def generate_mock_scans(count=250, days=14, seed=None):
    """Create fake scans, shaped like Scan.to_dict(), spread over the last `days` days."""
    material_to_bin, pfand_bin, unknown = load_bin_rules()
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    weights = [item[3] for item in MOCK_ITEMS]
    scans = []
    for _ in range(count):
        name, material, is_pfand, _ = rng.choices(MOCK_ITEMS, weights=weights)[0]
        moment = now - timedelta(seconds=rng.uniform(0, days * 86400))
        scans.append({
            "timestamp": moment.isoformat(timespec="seconds"),
            "item_name": name,
            "material": material,
            "bin_type": pfand_bin if is_pfand else material_to_bin.get(material, unknown),
            "is_pfand": is_pfand,
        })
    return scans


def _own_scans(user_id):
    """SQL condition for one user's scans. Without a user it matches nothing, never everyone's."""
    return Scan.user_id == user_id if user_id else false()


def parse_days(value, maximum=DashboardSetting.MAX_DAYS):
    """Validate an optional ?days= filter. Returns None when it isn't given."""
    if value is None or value == "":
        return None
    try:
        days = int(value)
    except (TypeError, ValueError) as error:
        raise InvalidFilterError("days must be a whole number.", field="days") from error
    if not 1 <= days <= maximum:
        raise InvalidFilterError(f"days must be between 1 and {maximum}.", field="days")
    return days


def load_live_scans(days=14, user_id=None):
    """Real scans of one user from the classification subsystem, from the last `days` days.

    Rows with an unreadable timestamp are skipped (and logged) instead of
    breaking the whole dashboard.
    """
    first_day = date.today() - timedelta(days=days - 1)
    try:
        rows = Scan.query.filter(_own_scans(user_id)).all()
    except SQLAlchemyError as error:
        raise DataSourceError("The classification results could not be read.") from error

    scans, skipped = [], 0
    for row in rows:
        try:
            day = _scan_date(row.timestamp)
        except (TypeError, ValueError):
            skipped += 1
            continue
        else:
            if day >= first_day:
                scans.append(row.to_dict())
    if skipped:
        logger.warning("Skipped %d scan(s) with an invalid timestamp.", skipped)
    return scans


def build_snapshot(save=True, days=None, user_id=None):
    """Calculate the statistics of one user and (by default) store them in the database.

    `days` overrides the saved time range for this one request (from ?days=).
    """
    setting = DashboardSetting.get_or_create()
    days = days or setting.get_time_range_days()
    if setting.get_use_mock_data():
        snapshot = DashboardSnapshot.from_scans(generate_mock_scans(days=days), "mock", user_id)
    else:
        snapshot = DashboardSnapshot.from_scans(load_live_scans(days, user_id), "live", user_id)
    if save:
        try:
            db.session.add(snapshot)
            db.session.commit()
        except SQLAlchemyError as error:
            db.session.rollback()
            raise DataSourceError("The snapshot could not be saved.") from error
        finally:
            logger.debug("Snapshot save attempted (source=%s).", snapshot.get_source())
    return snapshot



# --- Data output (Home Assignment 3): reading and filtering MySQL rows ---------

SAMPLE_HASH = "dashboard-sample-data"  # marks sample rows so they can be removed again


def query_scans(user_id, material=None, bin_type=None, days=None, limit=100):
    """One user's rows from the scans table, newest first, filtered by the selected fields."""
    try:
        query = Scan.query.filter(_own_scans(user_id))
        if material:
            query = query.filter(Scan.material == material)
        if bin_type:
            query = query.filter(Scan.bin_type == bin_type)
        if days:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
            query = query.filter(Scan.timestamp >= cutoff)  # ISO timestamps sort as text
        return query.order_by(Scan.timestamp.desc()).limit(limit).all()
    except SQLAlchemyError as error:
        raise DataSourceError("The classification results could not be read.") from error


def count_scans(user_id):
    try:
        return Scan.query.filter(_own_scans(user_id)).count()
    except SQLAlchemyError as error:
        raise DataSourceError("The classification results could not be read.") from error


def filter_options(user_id):
    """The distinct materials and bins in one user's scans, for the filter dropdowns."""
    try:
        own = db.session.query(Scan).filter(_own_scans(user_id))
        materials = [row[0] for row in own.with_entities(Scan.material).distinct().order_by(Scan.material)]
        bins = [row[0] for row in own.with_entities(Scan.bin_type).distinct().order_by(Scan.bin_type)]
    except SQLAlchemyError as error:
        raise DataSourceError("The filter options could not be loaded.") from error
    return materials, bins


def recent_snapshots(user_id, limit=10):
    """One user's latest saved dashboard snapshots, newest first."""
    try:
        return (DashboardSnapshot.query.filter(DashboardSnapshot._user_id == user_id if user_id else false())
                .order_by(DashboardSnapshot.id.desc()).limit(limit).all())
    except SQLAlchemyError as error:
        raise DataSourceError("The saved snapshots could not be read.") from error


def add_sample_scans(user_id, count=60, seed=None):
    """Insert sample rows for one user into the scans table so the data page has something to show."""
    try:
        for scan in generate_mock_scans(count=count, days=14, seed=seed):
            db.session.add(Scan(user_id=user_id, image_hash=SAMPLE_HASH, **scan))
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        raise DataSourceError("The sample scans could not be saved.") from error
    return count


def remove_sample_scans(user_id):
    """Delete only this user's rows added by add_sample_scans(); real scans are untouched."""
    try:
        removed = Scan.query.filter(_own_scans(user_id), Scan.image_hash == SAMPLE_HASH).delete(
            synchronize_session=False)
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        raise DataSourceError("The sample scans could not be removed.") from error
    return removed


# --- Database upgrade ------------------------------------------------------------

def ensure_snapshot_user_column():
    """Add dashboard_snapshots.user_id to databases created before snapshots belonged to users.

    db.create_all() only creates missing tables, it never adds columns to existing ones,
    so without this an older MySQL database would fail with "Unknown column".
    Returns True if the column had to be added.
    """
    inspector = inspect(db.engine)
    if "dashboard_snapshots" not in inspector.get_table_names():
        return False  # create_all() will create the table with the column
    columns = {column["name"] for column in inspector.get_columns("dashboard_snapshots")}
    if "user_id" in columns:
        return False
    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE dashboard_snapshots ADD COLUMN user_id VARCHAR(50) NULL"))
    logger.info("Added the user_id column to dashboard_snapshots.")
    return True
