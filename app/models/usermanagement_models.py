from app import db

class Country(db.Model):
    __tablename__ = 'countries'
    country_id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), nullable=False, unique=True)
    rules_file = db.Column(db.String(255), nullable=True)

    def get_rules(self):
        return f"Standard sorting rules applied for region {self.code}"

class RecyclingRule(db.Model):
    __tablename__ = 'recycling_rules'
    rule_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    material = db.Column(db.String(100), nullable=False)
    bin_type = db.Column(db.String(100), nullable=False)

    def get_rule_id(self):
        return self.rule_id

    def get_material(self):
        return self.material

    def get_bin_type(self):
        return self.bin_type

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    selected_country_id = db.Column(db.String(36), db.ForeignKey('countries.country_id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    country = db.relationship('Country', backref=db.backref('users', lazy=True))

    def register(self):
        db.session.add(self)
        db.session.commit()

    def login(self):
        return self.is_active

    def get_user_name(self):
        return self.username

    def get_country(self):
        return self.country.name if self.country else "Germany"

    def deactivate_account(self):
        self.is_active = False

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "country": self.get_country(),
            "is_active": self.is_active
        }