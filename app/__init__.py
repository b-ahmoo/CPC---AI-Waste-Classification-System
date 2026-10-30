from flask import Flask
from app.config import Config
from app.extensions import db  # e.g., SQLAlchemy

def create_app(config_class=Config):
    app = Flask(__name__, template_folder="../templates")
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)

    # Register Blueprints for each Subsystem
    from app.subsystems.chatbot.routes import chatbot_bp

    app.register_blueprint(chatbot_bp, url_prefix='/chat')
    # app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    with app.app_context():
      from app import models  
      db.create_all()         
    

    @app.route('/')
    def index():
        return {"status": "healthy", "service": "AI Waste Assistant MVP"}

    return app