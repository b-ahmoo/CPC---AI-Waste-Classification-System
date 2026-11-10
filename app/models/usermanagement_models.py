"""
Subsystem 1: SQLAlchemy Models (Country & User)
"""

from app.extensions import db


class Country(db.Model):
    """Represents geographical location metadata table for a user."""
    __tablename__ = 'countries'

    country_id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), nullable=False)

    def get_details(self) -> dict:
        return {
            "country_id": self.country_id,
            "name": self.name,
            "code": self.code
        }


class User(db.Model):
    """Represents the system users table."""
    __tablename__ = 'users'

    user_id = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    country_id = db.Column(db.String(50), db.ForeignKey('countries.country_id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    # Relationship to Country
    country = db.relationship('Country', backref=db.backref('users', lazy=True))

    def update_profile(self, username=None, country_id=None):
        if username:
            self.username = username
        if country_id:
            self.country_id = country_id

    def deactivate_account(self):
        self.is_active = False

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "country": self.country.get_details() if self.country else None,
            "is_active": self.is_active
        }
