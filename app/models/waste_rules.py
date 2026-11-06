from app.extensions import db
from datetime import datetime, timezone

class WasteRule(db.Model):
    __tablename__ = 'waste_rules'

    # State / Attributes
    rule_id = db.Column(db.Integer, primary_key=True)
    country = db.Column(db.String(50), nullable=False, index=True)
    material_type = db.Column(db.String(50), nullable=False)
    bin = db.Column(db.String(50), nullable=False)
    instruction = db.Column(db.Text, nullable=False)

    # Encapsulation (Getters and Setters)
    def get_rule_id(self):
        return self.rule_id

    def set_rule_id(self, rule_id):
        self.rule_id = rule_id

    def get_country(self):
        return self.country

    def set_country(self, country):
        self.country = country

    def get_material_type(self):
        return self.material_type

    def set_material_type(self, material_type):
        self.material_type = material_type

    def get_bin(self):
        return self.bin

    def set_bin(self, bin):
        self.bin = bin

    def get_instruction(self):
        return self.instruction

    def set_instruction(self, instruction):
        self.instruction = instruction