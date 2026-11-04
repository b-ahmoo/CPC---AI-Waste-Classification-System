import pytest
from app.models import ChatSession, ChatMessage, WasteRule
from app.subsystems.chatbot.chatbot_service import ChatbotService
from app.extensions import db

# Unit Tests

def test_01_waste_rule_constructor_and_getters(app):
    """UNIT TEST 1: Verifies WasteRule constructor and getters work."""
    with app.app_context():
        # Create a rule using constructor
        rule = WasteRule(
            country="Germany", 
            material_type="Paper", 
            bin="Blue Bin", 
            instruction="Clean paper goes here."
        )
        # Test the getters
        assert rule.get_country() == "Germany"
        assert rule.get_bin() == "Blue Bin"
        assert rule.get_instruction() == "Clean paper goes here."

def test_02_chat_session_constructor_and_setters(app):
    """UNIT TEST 2: Verifies ChatSession state initialization and setters."""
    with app.app_context():
        # Test constructor defaults
        session = ChatSession(user_id=99)
        assert session.get_user_id() == 99
        assert session.get_active() is True
        
        # Test the setter
        session.set_active(False)
        assert session.get_active() is False

def test_03_chat_message_database_save(app):
    """UNIT TEST 3: Verifies ChatMessage can be saved and retrieved from database."""
    with app.app_context():
        # 1. Create and save a  session first
        session = ChatSession()
        db.session.add(session)
        db.session.commit()
        
        # 2. Create and save the message
        msg = ChatMessage(session_id=session.session_id, sender="user", message="Hello")
        db.session.add(msg)
        db.session.commit()
        
        # 3. Retrieveand verify
        saved_msg = ChatMessage.query.first()
        assert saved_msg.get_sender() == "user"
        assert saved_msg.get_message() == "Hello"

def test_04_service_find_rule_success(app):
    """UNIT TEST 4: Verifies ChatbotService finds existing rules in the DB."""
    with app.app_context():
        # 1. Insert rule into the test database
        rule = WasteRule(country="France", material_type="Glass", bin="Green Bin", instruction="Empty jars.")
        db.session.add(rule)
        db.session.commit()
        
        # 2. Testservice method
        service = ChatbotService(session_id=1, message="Where does glass go?")
        result = service.find_rule("France")
        
        assert "Green Bin" in result
        assert "Empty jars." in result

def test_05_service_find_rule_fallback(app):
    """UNIT TEST 5: Verifies ChatbotService returns fallback if rule doesn't exist."""
    with app.app_context():
        service = ChatbotService(session_id=1, message="Where does this go?")
        # Asking for a country/material not in the DB
        result = service.find_rule("Mars")
        
        assert result == "Follow standard municipal sorting guidelines."