from app.extensions import db
from datetime import datetime, timezone

class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'

    # State / Attributes
    _session_id = db.Column('session_id',db.Integer, primary_key=True)
    _user_id = db.Column(db.String(50), nullable=True)
    _created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    _updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    _active = db.Column(db.Boolean, default=True)
    

    # Relationship link to messages
    #backref = true automatically generates an attribute session in ChatMessage
    # lazy = true prevents app from immediately loading all chat sessions, waits for query instead
    messages = db.relationship('ChatMessage', backref='session', lazy=True)

    def __init__(self,session_id=None, user_id=None, active=True):
        if session_id:
            self._session_id = session_id
        self._user_id = user_id
        self._active = active

    # Encapsulation (Getters and Setters)
    def get_session_id(self):
        return self._session_id

    def set_session_id(self, session_id):
        self._session_id = session_id

    def get_user_id(self):
        return self._user_id

    def set_user_id(self, user_id):
        self._user_id = user_id

    def get_created_at(self):
        return self._created_at

    def set_created_at(self, created_at):
        self._created_at = created_at

    def get_updated_at(self):
        return self._updated_at

    def set_updated_at(self, updated_at):
        self._updated_at = updated_at

    def get_active(self):
        return self._active

    def set_active(self, active):
        self._active = active