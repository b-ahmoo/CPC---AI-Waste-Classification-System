from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from app.subsystems.usermanagement.usermanagement_services import AccountService
from app.models.usermanagement_models import Country, User
from app.exceptions import ValidationError, NotFoundError
from app.subsystems.usermanagement.waste_integration import WasteIntegration

user_bp = Blueprint('user_management', __name__, template_folder='templates')

# Initialize Account Service and sample seed data for the web route
account_service = AccountService()
default_country = Country(country_id="c1", name="Germany", code="DE")
try:
    account_service.create_account(user_id="u1", username="Max", email="max@uni.edu", country=default_country)
except Exception:
    pass  # Seed data might already exist

@user_bp.route('/user/profile/<user_id>')
def user_profile(user_id):
    """Web page route showing user profile and their connected waste rules."""
    user = account_service.find_user_by_id(user_id)
    if not user:
        return "User not found", 404

    integration_data = WasteIntegration.get_user_waste_regulations(user)
    return render_template('usermanagement/user_profile.html', user=user.to_dict(), rules=integration_data)

@user_bp.route('/login/<user_id>', methods=['GET', 'POST'])
def login(user_id):
    """Simulates a login by setting the user_id and country_code in the session."""
    user = account_service.find_user_by_id(user_id)
    if not user:
        return "User not found", 404
    
    session['user_id'] = user.user_id
    session['country_code'] = user.country.code if user.country else 'DE'
    
    return redirect(url_for('user_management.user_profile', user_id=user.user_id))

@user_bp.route('/api/users', methods=['POST'])
def api_create_user():
    data = request.get_json() or {}
    try:
        user = account_service.create_account(
            user_id=data.get('user_id'),
            username=data.get('username'),
            email=data.get('email'),
            country=data.get('country')
        )
        return jsonify(user.to_dict()), 201
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400

@user_bp.route('/api/users/<user_id>', methods=['GET'])
def api_get_user(user_id):
    user = account_service.find_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict()), 200
