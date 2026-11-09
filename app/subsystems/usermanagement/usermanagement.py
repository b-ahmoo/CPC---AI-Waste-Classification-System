"""
Subsystem 1 Implementation: Account Service, Authentication, and Integration
"""

from typing import List, Optional
from flask import Blueprint, render_template, request, redirect, url_for, flash
user_bp = Blueprint('usermanagement', __name__, template_folder='templates')

@user_bp.route('/')
def index():
    return render_template('usermanagement/user_profile.html')

from app.models.usermanagement_models import Country, User
from app.subsystems.usermanagement.exceptions import UserNotFoundError, DuplicateEmailError, InactiveUserError
# Create a Flask Blueprint for Subsystem 1 routes
user_bp = Blueprint('usermanagement', __name__, template_folder='templates')


class AccountService:
    """Service class managing user registration, lookup, authentication, and deactivation."""
    
    def __init__(self):
        self._users: List[User] = []

    def create_account(self, user_id: str, username: str, email: str, country: Country) -> User:
        """Registers a new user within the system (Sign Up)."""
        if self.find_user_by_email(email):
            raise DuplicateEmailError()
        user = User(user_id=user_id, username=username, email=email, country=country)
        self._users.append(user)
        return user

    def login(self, email: str) -> User:
        """Handles user login authentication with exception checks."""
        user = self.find_user_by_email(email)
        if not user:
            raise UserNotFoundError()
        if not user.is_active:
            raise InactiveUserError()
        return user

    def logout(self, user_id: str) -> bool:
        """Handles user logout workflow."""
        user = self.find_user_by_id(user_id)
        return user is not None

    def deactivate_user_account(self, user_id: str) -> bool:
        """Deactivates a user account by ID."""
        user = self.find_user_by_id(user_id)
        if user:
            user.deactivate_account()
            return True
        return False

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
        Fulfills cross-subsystem integration requirements.
        """
        country_code = user.country.code
        return {
            "user": user.username,
            "applicable_country": user.country.name,
            "local_disposal_guidelines": f"Standard sorting rules applied for region {country_code}"
        }


# Initialize Account Service and sample seed data for the web route
account_service = AccountService()
default_country = Country(country_id="c1", name="Germany", code="DE")
account_service.create_account(user_id="u1", username="Max", email="max@uni.edu", country=default_country)


@user_bp.route('/user/profile/<user_id>')
def user_profile(user_id):
    """Web page route showing user profile and their connected waste rules."""
    user = account_service.find_user_by_id(user_id)
    if not user:
        return "User not found", 404
        
    integration_data = WasteIntegration.get_user_waste_regulations(user)
    return render_template('user_profile.html', user=user.to_dict(), rules=integration_data)
