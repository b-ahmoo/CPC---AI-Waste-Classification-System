"""Database storage for classification results (the scans table)."""

from app.extensions import db


class Scan(db.Model):
    __tablename__ = "scans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)  # becomes a ForeignKey to users.id once auth exists
    timestamp = db.Column(db.String(32), nullable=False)
    image_hash = db.Column(db.String(64), nullable=False, index=True)
    item_name = db.Column(db.String(200), nullable=False)
    material = db.Column(db.String(50), nullable=False)
    bin_type = db.Column(db.String(50), nullable=False)
    is_pfand = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "item_name": self.item_name,
            "material": self.material,
            "bin_type": self.bin_type,
            "is_pfand": self.is_pfand,
        }


def save_results(results, image_hash, user_id=None):
    """Insert one row per identified item."""
    for r in results:
        db.session.add(Scan(
            user_id=user_id,
            timestamp=r["timestamp"],
            image_hash=image_hash,
            item_name=r["item_name"],
            material=r["material"],
            bin_type=r["bin_type"],
            is_pfand=bool(r["is_pfand"]),
        ))
    db.session.commit()


def find_by_hash(image_hash):
    """Return earlier results for the same image, so the API isn't called twice."""
    latest = (Scan.query.filter_by(image_hash=image_hash)
              .order_by(Scan.timestamp.desc()).first())
    if latest is None:
        return []
    rows = Scan.query.filter_by(image_hash=image_hash, timestamp=latest.timestamp).all()
    return [row.to_dict() for row in rows]


def recent_scans(limit=10):
    return [row.to_dict() for row in Scan.query.order_by(Scan.id.desc()).limit(limit).all()]