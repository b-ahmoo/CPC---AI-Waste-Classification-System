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

    __mapper_args__ = {
        'polymorphic_on': sender,
        'polymorphic_identity': 'generic'
    }

    def __init__(self, session_id: int, sender: str, message: str, time_sent=None):
        self.session_id = session_id
        self.sender = sender
        self.message = message
        if time_sent:
            self.time_sent = time_sent

    # Encapsulation (Getters and Setters)

    def display_format(self):
        return f"[{self.time_sent}] {self.sender}: {self.message}"
    
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


class UserMessage(ChatMessage):
    # Maps automatically when sender == 'user'
    __mapper_args__ = {
        'polymorphic_identity': 'user'
    }

    # 3. Override the base method (Polymorphism execution)
    def display_format(self):
        return f"User says: {self.get_message()}"


class BotMessage(ChatMessage):
    # Maps automatically when sender == 'assistant'
    __mapper_args__ = {
        'polymorphic_identity': 'assistant'
    }

    # 3. Override 
    def display_format(self):
        return f"AI Assistant says: {self.get_message()}"