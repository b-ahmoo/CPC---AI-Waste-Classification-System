from flask import Flask
from app.config import Config
from app.extensions import db  # shared SQLAlchemy database for all subsystems


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="../templates")
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Register Blueprints for each Subsystem
    # from app.subsystems.auth.routes import auth_bp
    from app.subsystems.classification.routes import classification_bp
    from app.subsystems.chatbot.routes import chatbot_bp
    from app.subsystems.dashboard.routes import dashboard_bp

    #  app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(classification_bp, url_prefix='/classify')
    app.register_blueprint(chatbot_bp, url_prefix='/chat')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    # Create database tables that don't exist yet
    with app.app_context():
        from app import models  # noqa: F401  (registers the dummy_items table)
        
        db.create_all()

    @app.route('/')
    def index():
        return {"status": "healthy", "service": "AI Waste Assistant MVP"}

    return app