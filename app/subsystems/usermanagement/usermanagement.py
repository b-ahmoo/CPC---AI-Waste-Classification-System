"""User Management subsystem: accounts, login and the user profile page.

Users and countries are stored in the database (the `users` and `countries`
tables). Logging in puts the user's id into the Flask session, which is what
the other subsystems read to know who is using the application.
"""

from typing import List, Optional

from flask import (Blueprint, redirect, render_template, request, session,
                   url_for)

from app.extensions import db
from app.models.usermanagement_models import Country, User
from app.subsystems.usermanagement.exceptions import (DuplicateEmailError,
                                                      DuplicateUsernameError,
                                                      InactiveUserError,
                                                      UserNotFoundError)

user_bp = Blueprint('usermanagement', __name__)


class AccountService:
    """Creates, finds and deactivates accounts. All data lives in the database."""

    def create_account(self, user_id: str, username: str, email: str,
                       country: Country) -> User:
        if self.find_user_by_email(email):
            raise DuplicateEmailError()
        if self.find_user_by_id(user_id):
            raise DuplicateUsernameError()
        user = User(user_id=user_id, username=username, email=email, country=country)
        db.session.add(user)
        db.session.commit()
        return user

    def login(self, email: str) -> User:
        """Check the account, then remember the user in the session."""
        user = self.find_user_by_email(email)
        if not user:
            raise UserNotFoundError()
        if not user.is_active:
            raise InactiveUserError()
        session['user_id'] = user.user_id      # <-- what the other subsystems read
        session['username'] = user.username
        return user

    def logout(self, user_id: str = None) -> bool:
        session.pop('user_id', None)
        session.pop('username', None)
        return True

    def deactivate_user_account(self, user_id: str) -> bool:
        user = self.find_user_by_id(user_id)
        if user:
            user.deactivate_account()
            db.session.commit()
            return True
        return False

    def find_user_by_id(self, user_id: str) -> Optional[User]:
        return User.query.filter_by(user_id=user_id).first()

    def find_user_by_email(self, email: str) -> Optional[User]:
        return User.query.filter_by(email=email).first()

    def all_countries(self) -> List[Country]:
        return Country.query.order_by(Country.name).all()


class WasteIntegration:
    """Connects a user to the recycling rules that apply in their country."""

    @staticmethod
    def get_user_activity(user: User, limit: int = 5) -> dict:
        """The user's own scans, read from the classification subsystem's table."""
        from app.models.scan import Scan
        rows = (Scan.query.filter_by(user_id=user.user_id)
                .order_by(Scan.id.desc()).limit(limit).all())
        return {
            "scan_count": Scan.query.filter_by(user_id=user.user_id).count(),
            "recent_scans": rows,
        }

    @staticmethod
    def get_user_waste_regulations(user: User) -> dict:
        country_code = user.country.code
        return {
            "user": user.username,
            "applicable_country": user.country.name,
            "local_disposal_guidelines":
                f"Standard sorting rules applied for region {country_code}",
        }


account_service = AccountService()


def seed_countries():
    """Create the selectable countries once. Safe to call on every start."""
    if Country.query.count() == 0:
        db.session.add(Country(country_id="c1", name="Germany", code="DE"))
        db.session.add(Country(country_id="c2", name="France", code="FR"))
        db.session.commit()


def current_user() -> Optional[User]:
    """The logged-in user, or None."""
    user_id = session.get('user_id')
    return account_service.find_user_by_id(user_id) if user_id else None


# --- routes -----------------------------------------------------------------

@user_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Create an account and choose a country."""
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip()
        country_id = request.form.get('country_id')

        if not username or not email or not country_id:
            return render_template('usermanagement/signup.html',
                                   countries=account_service.all_countries(),
                                   error="Please fill in every field.")
        country = Country.query.filter_by(country_id=country_id).first()
        if not country:
            return render_template('usermanagement/signup.html',
                                   countries=account_service.all_countries(),
                                   error="Please choose a country.")
        try:
            user = account_service.create_account(
                user_id=username, username=username, email=email, country=country)
        except (DuplicateEmailError, DuplicateUsernameError) as error:
            return render_template('usermanagement/signup.html',
                                   countries=account_service.all_countries(),
                                   error=str(error))
        account_service.login(user.email)
        return redirect(url_for('usermanagement.profile'))

    return render_template('usermanagement/signup.html',
                           countries=account_service.all_countries())


@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Log in with an email address."""
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        try:
            account_service.login(email)
        except (UserNotFoundError, InactiveUserError) as error:
            return render_template('usermanagement/login.html', error=str(error))
        return redirect(url_for('usermanagement.profile'))

    return render_template('usermanagement/login.html')


@user_bp.route('/logout')
def logout():
    account_service.logout()
    return redirect(url_for('usermanagement.login'))


@user_bp.route('/profile')
def profile():
    """The logged-in user's own profile, with their own scan history."""
    user = current_user()
    if not user:
        return redirect(url_for('usermanagement.login'))
    return render_template('usermanagement/user_profile.html',
                           user=user.to_dict(),
                           rules=WasteIntegration.get_user_waste_regulations(user),
                           **WasteIntegration.get_user_activity(user))


@user_bp.route('/profile/<user_id>')
def user_profile(user_id):
    """Profile page for a specific user id."""
    user = account_service.find_user_by_id(user_id)
    if not user:
        return "User not found", 404
    return render_template('usermanagement/user_profile.html',
                           user=user.to_dict(),
                           rules=WasteIntegration.get_user_waste_regulations(user),
                           **WasteIntegration.get_user_activity(user))
