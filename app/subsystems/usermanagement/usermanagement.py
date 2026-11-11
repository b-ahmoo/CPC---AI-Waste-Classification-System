
from typing import Optional
from flask import Blueprint, render_template, request, redirect, url_for, session
from app.models.usermanagement_models import Country, User, RecyclingRule
from app.subsystems.usermanagement.exceptions import UserNotFoundError, DuplicateEmailError, InactiveUserError
from app import db

user_bp = Blueprint('usermanagement', __name__, template_folder='templates')

class AccountService:
    def __init__(self):
        self.db_path = 'sqlite:///app.db'

    def register_user(self, user_id: str, username: str, email: str, country: Country) -> User:
        if self.find_user_by_email(email):
            raise DuplicateEmailError()
        user = User(user_id=user_id, username=username, email=email, selected_country_id=country.country_id if country else None)
        db.session.add(user)
        db.session.commit()
        return user

    def authenticate(self, email: str) -> User:
        user = self.find_user_by_email(email)
        if not user:
            raise UserNotFoundError()
        if not user.is_active:
            raise InactiveUserError()
        session['user_id'] = user.user_id
        session['country_code'] = user.country.code if user.country else 'DE'
        return user

    def update_profile(self, user_id: str, username: str, country_id: str) -> bool:
        user = self.find_user_by_id(user_id)
        if user:
            user.username = username
            user.selected_country_id = country_id
            db.session.commit()
            return True
        return False

    def statistics_query(self, user_id: str) -> dict:
        return {"total_scans": 12, "efficiency": "94%"}

    def delete_account(self, user_id: str) -> bool:
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

account_service = AccountService()

def seed_database():
    if not Country.query.first():
        de = Country(country_id="c1", name="Germany", code="DE", rules_file="rules_de.json")
        fr = Country(country_id="c2", name="France", code="FR", rules_file="rules_fr.json")
        db.session.add_all([de, fr])
        db.session.commit()

@user_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    seed_database()
    countries = Country.query.all()
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        country_id = request.form.get('country_id')
        country = Country.query.filter_by(country_id=country_id).first()
        try:
            account_service.register_user(user_id=email, username=username, email=email, country=country)
            session['user_id'] = email
            return redirect(url_for('usermanagement.user_profile'))
        except DuplicateEmailError:
            return render_template('usermanagement/signup.html', countries=countries, error="Email already registered.")
    return render_template('usermanagement/signup.html', countries=countries)

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        try:
            account_service.authenticate(email)
            return redirect(url_for('usermanagement.user_profile'))
        except (UserNotFoundError, InactiveUserError):
            return render_template('usermanagement/login.html', error="Invalid email or inactive account.")
    return render_template('usermanagement/login.html')

@user_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('usermanagement.login'))

@user_bp.route('/profile')
def user_profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('usermanagement.login'))
    user = account_service.find_user_by_id(user_id)
    if not user:
        return redirect(url_for('usermanagement.login'))
    stats = account_service.statistics_query(user_id)
    return render_template('usermanagement/user_profile.html', user=user, stats=stats)