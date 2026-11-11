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
    from app.subsystems.usermanagement.usermanagement import user_bp

    #  app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(classification_bp, url_prefix='/classify')
    app.register_blueprint(chatbot_bp, url_prefix='/chat')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(user_bp, url_prefix='/user')


    # Create database tables that don't exist yet
    with app.app_context():
        from app import models
        from app.models import WasteRule 

        
        db.create_all() #create all tables when docker starts


        #populate waste rules with dummy but real rules for querying the database and sending rule to open ai later.

        if not WasteRule.query.first():
            dummy_rules = [
                # --- GERMANY ---
                WasteRule(country="Germany", material_type="Paper", bin="Blaue Tonne (Blue Bin)", 
                          instruction="Clean paper, newspapers, magazines, and flattened cardboard boxes. Do not include dirty pizza boxes or coated paper."),
                WasteRule(country="Germany", material_type="Plastic", bin="Gelbe Tonne / Gelber Sack (Yellow Bin/Bag)", 
                          instruction="Lightweight packaging, plastic bottles, yogurt cups, and foil. Containers should be empty but do not need to be washed."),
                WasteRule(country="Germany", material_type="Glass", bin="Altglascontainer (Glass Bank)", 
                          instruction="Sort by color (white, brown, green). Do not throw in drinking glasses, mirrors, or light bulbs. Remove lids if possible."),
                WasteRule(country="Germany", material_type="Bio", bin="Biotonne (Brown/Green Bin)", 
                          instruction="Organic waste like food scraps, eggshells, coffee grounds, and garden waste. Do not use standard plastic bags; use paper bags or certified compostable bags."),
                WasteRule(country="Germany", material_type="Metal", bin="Gelbe Tonne / Gelber Sack (Yellow Bin/Bag)", 
                          instruction="Tin cans, aluminum foil, and metal caps go here. Large metal items must go to a Recyclinghof (recycling center)."),

                # --- FRANCE ---
                WasteRule(country="France", material_type="Paper", bin="Poubelle Jaune (Yellow Bin)", 
                          instruction="All paper, newspapers, magazines, envelopes (even with windows), and cardboard packaging."),
                WasteRule(country="France", material_type="Plastic", bin="Poubelle Jaune (Yellow Bin)", 
                          instruction="All plastic packaging including bottles, flasks, yogurt pots, plastic film, and trays. Empty them completely, no need to rinse. Leave caps on bottles."),
                WasteRule(country="France", material_type="Glass", bin="Colonne à Verre (Green Glass Bank)", 
                          instruction="Glass bottles, jars, and pots. Remove corks, plastic, or metal lids before dropping them in. No broken dishes, mirrors, or window glass."),
                WasteRule(country="France", material_type="Bio", bin="Composteur / Bac Brun (Compost/Brown Bin)", 
                          instruction="Fruit and vegetable peels, tea bags, coffee grounds, and eggshells. Under recent French law, sorting bio-waste is mandatory."),
                WasteRule(country="France", material_type="Metal", bin="Poubelle Jaune (Yellow Bin)", 
                          instruction="Tin cans, aerosols, aluminum trays, foil, and metal syrup bottles.")
            ]
            
            db.session.add_all(dummy_rules)
            db.session.commit()
            print("Successfully populated dummy recycling rules for Germany and France.")



    @app.route('/')
    def index():
        return {"status": "healthy", "service": "AI Waste Assistant MVP"}

    return app