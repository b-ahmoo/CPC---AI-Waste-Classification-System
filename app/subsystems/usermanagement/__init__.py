import os
from flask import Flask, jsonify

def create_app(test_config=None):
    # Initialize Flask Application
    app = Flask(__name__, instance_relative_config=True)

    # Basic App Configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key'),
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    # Health Check Route
    @app.route('/')
    def index():
        return jsonify({
            "service": "AI Waste Assistant MVP",
            "status": "healthy"
        })

    # Register Subsystem Blueprints
    from app.subsystems.chatbot.chatbot import chatbot_bp
    app.register_blueprint(chatbot_bp, url_prefix='/chat')

    from app.subsystems.dashboard.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    # Register User Management Subsystem Blueprint
    from app.subsystems.usermanagement.usermanagement import user_bp
    app.register_blueprint(user_bp, url_prefix='/usermanagement')

    return app
