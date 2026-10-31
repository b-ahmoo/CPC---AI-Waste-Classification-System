from app.extensions import db
from datetime import datetime, timezone

class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'

    # State / Attributes
    session_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    active = db.Column(db.Boolean, default=True)

    # Relationship link to messages
    messages = db.relationship('ChatMessage', backref='session', lazy=True)

    # Encapsulation (Getters and Setters)
    def get_session_id(self):
        return self.session_id

    def set_session_id(self, session_id):
        self.session_id = session_id

    def get_user_id(self):
        return self.user_id

    def set_user_id(self, user_id):
        self.user_id = user_id

    def get_created_at(self):
        return self.created_at

    def set_created_at(self, created_at):
        self.created_at = created_at

    def get_updated_at(self):
        return self.updated_at

    def set_updated_at(self, updated_at):
        self.updated_at = updated_at

    def get_active(self):
        return self.active

    def set_active(self, active):
        self.active = active