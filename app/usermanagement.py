"""
Subsystem 1: User Management, Country Metadata & Web Integration
OOP Implementation for Home Assignment 1
"""

from typing import List, Optional
from flask import Blueprint, render_template
from app.models.usermanagement_models import Country, User
# Create a Flask Blueprint for Subsystem 1 routes
user_bp = Blueprint('usermanagement', __name__, template_folder='templates')


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
        """Serializes user data for integration with other subsystems (e.g., WasteRules)."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "country": self.country.get_details(),
            "is_active": self.is_active
        }


class AccountService:
    """Service class managing user registration, lookup, and active accounts."""
    
    def __init__(self):
        self._users: List[User] = []

    def create_account(self, user_id: str, username: str, email: str, country: Country) -> User:
        """Registers a new user within the system."""
        user = User(user_id=user_id, username=username, email=email, country=country)
        self._users.append(user)
        return user

    def find_user_by_id(self, user_id: str) -> Optional[User]:
        """Finds a user by unique user_id."""
        for user in self._users:
            if user.user_id == user_id:
                return user
        return None

    def find_user_by_email(self, email: str) -> Optional[User]:
        """Finds a user by email address."""
        for user in self._users:
            if user.email == email:
                return user
        return None


class WasteIntegration:
    """Bridges Subsystem 1 (User/Country) with Subsystem 2 (Waste Rules)."""
    
    @staticmethod
    def get_user_waste_regulations(user: User) -> dict:
        """
        Fetches waste classification rules specific to the user's country.
        Fulfills cross-subsystem integration and end-to-end user scenario mapping.
        """
        country_code = user.country.code
        return {
            "user": user.username,
            "applicable_country": user.country.name,
            "local_disposal_guidelines": f"Standard rules applied for region {country_code}"
        }


# Initialize Account Service and sample seed data for the web route
account_service = AccountService()
default_country = Country("c1", "Germany", "DE")
account_service.create_account("u1", "Sejal", "sejal@uni.edu", default_country)


@user_bp.route('/user/profile/<user_id>')
def user_profile(user_id):
    """Web page route showing user profile and their connected waste rules."""
    user = account_service.find_user_by_id(user_id)
    if not user:
        return "User not found", 404
        
    # Connect Subsystem 1 data to Subsystem 2 / Waste rules integration
    integration_data = WasteIntegration.get_user_waste_regulations(user)
    
    # Renders the template connecting user data and waste rules
    return render_template('user_profile.html', user=user.to_dict(), rules=integration_data)
