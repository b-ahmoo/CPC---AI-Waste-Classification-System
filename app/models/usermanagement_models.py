"""
Subsystem 1: Data Models (Country & User)
"""

from typing import Optional


class Country:
    """Represents geographical location metadata for a user."""
    
    def __init__(self, country_id: str, name: str, code: str):
        self.country_id = country_id
        self.name = name
        self.code = code

    def get_details(self) -> dict:
        """Returns country metadata as a dictionary."""
        return {
            "country_id": self.country_id,
            "name": self.name,
            "code": self.code
        }


class User:
    """Represents a system user and their location profile."""
    
    def __init__(self, user_id: str, username: str, email: str, country: Country):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.country = country
        self.is_active = True

    def update_profile(self, username: Optional[str] = None, country: Optional[Country] = None) -> None:
        """Updates user details."""
        if username:
            self.username = username
        if country:
            self.country = country

    def deactivate_account(self) -> None:
        """Deactivates user account."""
        self.is_active = False

    def to_dict(self) -> dict:
        """Serializes user data for integration with other subsystems."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "country": self.country.get_details(),
            "is_active": self.is_active
        }
