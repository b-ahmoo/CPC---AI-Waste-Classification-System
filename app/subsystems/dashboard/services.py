"""Dashboard logic: where the data comes from and how a snapshot is built.

Live data comes from the classification subsystem's scans table. Until there are
real scans, mock scans are generated with the same material -> bin rules
(app/subsystems/classification/rules.json), so the dashboard looks realistic.
"""

import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.extensions import db
from app.models.dashboard import DashboardSetting, DashboardSnapshot, _scan_date
from app.models.scan import Scan

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
    with open(path, encoding="utf-8") as f:
        rules = json.load(f)
    return rules["material_to_bin"], rules["pfand"]["bin"], rules["unknown_label"]


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


def load_live_scans(days=14):
    """Real scans from the classification subsystem, from the last `days` days."""
    first_day = date.today() - timedelta(days=days - 1)
    return [s.to_dict() for s in Scan.query.all() if _scan_date(s.timestamp) >= first_day]


def build_snapshot(save=True):
    """Calculate the current statistics and (by default) store them in the database."""
    setting = DashboardSetting.get_or_create()
    days = setting.get_time_range_days()
    if setting.get_use_mock_data():
        snapshot = DashboardSnapshot.from_scans(generate_mock_scans(days=days), "mock")
    else:
        snapshot = DashboardSnapshot.from_scans(load_live_scans(days), "live")
    if save:
        db.session.add(snapshot)
        db.session.commit()
    return snapshot
