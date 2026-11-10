
from typing import List, Optional
from flask import Blueprint, render_template, request, redirect, url_for
from app.models.usermanagement_models import Country, User
from app.subsystems.usermanagement.exceptions import UserNotFoundError, DuplicateEmailError, InactiveUserError

user_bp = Blueprint('usermanagement', __name__, template_folder='templates')

class AccountService:
    def __init__(self):
        self._users: List[User] = []

    def create_account(self, user_id: str, username: str, email: str, country: Country) -> User:
        if self.find_user_by_email(email):
            raise DuplicateEmailError()
        user = User(user_id=user_id, username=username, email=email, country=country)
        self._users.append(user)
        return user

    def login(self, email: str) -> User:
        user = self.find_user_by_email(email)
        if not user:
            raise UserNotFoundError()
        if not user.is_active:
            raise InactiveUserError()
        return user

    def logout(self, user_id: str) -> bool:
        user = self.find_user_by_id(user_id)
        return user is not None

    def deactivate_user_account(self, user_id: str) -> bool:
        user = self.find_user_by_id(user_id)
        if user:
            user.deactivate_account()
            return True
        return False

    def find_user_by_id(self, user_id: str) -> Optional[User]:
        for user in self._users:
            if user.user_id == user_id:
                return user
        return None

    def find_user_by_email(self, email: str) -> Optional[User]:
        for user in self._users:
            if user.email == email:
                return user
        return None

class WasteIntegration:
    @staticmethod
    def get_user_waste_regulations(user: User) -> dict:
        country_code = user.country.code
        return {
            "user": user.username,
            "applicable_country": user.country.name,
            "local_disposal_guidelines": f"Standard sorting rules applied for region {country_code}"
        }

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
