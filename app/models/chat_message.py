from app.extensions import db
from datetime import datetime, timezone

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    # State / Attributes
    message_id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.session_id'), nullable=False)
    sender = db.Column(db.String(20), nullable=False)
    time_sent = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    message = db.Column(db.Text, nullable=False)

    # Encapsulation (Getters and Setters)
    def get_message_id(self):
        return self.message_id

    def set_message_id(self, message_id):
        self.message_id = message_id

    def get_session_id(self):
        return self.session_id

    def set_session_id(self, session_id):
        self.session_id = session_id

    def get_sender(self):
        return self.sender

    def set_sender(self, sender):
        self.sender = sender

    def get_time_sent(self):
        return self.time_sent

    def set_time_sent(self, time_sent):
        self.time_sent = time_sent

    def get_message(self):
        return self.message

    def set_message(self, message):
        self.message = message