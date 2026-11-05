import pytest
import sqlalchemy
from unittest.mock import patch
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


def test_06_history_route_success(client, app):
    """Regression Test 6: Fetching history for an existing session returns correct data."""
    with app.app_context():
        # Setup: Create a session and messages manually
        session = ChatSession(session_id=101)
        msg1 = ChatMessage(session_id=101, sender="user", message="Hi")
        msg2 = ChatMessage(session_id=101, sender="assistant", message="Hello")
        db.session.add_all([session, msg1, msg2])
        db.session.commit()
        
    # Action: Request the history
    response = client.get('/chat/history/101')
    
    # Verify: The route should return the messages
    assert response.status_code == 200
    assert len(response.json["history"]) == 2
    assert response.json["history"][0]["sender"] == "user"

def test_07_history_route_not_found(client):
    """Regression Test 7: Fetching history for a non-existent session returns 404."""
    response = client.get('/chat/history/99999')
    assert response.status_code == 404
    assert "error" in response.json

def test_08_session_reuse(client, app):
    """Regression Test 8: Sending multiple messages to the same session appends to history."""
    # First message creates the session dynamically
    client.post('/chat/ask', json={"message": "First", "session_id": 202})
    # Second message reuses the session
    client.post('/chat/ask', json={"message": "Second", "session_id": 202})
    
    with app.app_context():
        messages = ChatMessage.query.filter_by(session_id=202, sender="user").all()
        assert len(messages) == 2
        assert messages[0].get_message() == "First"
        assert messages[1].get_message() == "Second"

def test_09_empty_payload_validation(client):
    """Regression Test 9: Submitting a completely empty JSON payload returns a 400 Bad Request."""
    response = client.post('/chat/ask', json={})
    assert response.status_code == 400
    assert "error" in response.json

def test_10_default_country_fallback(client, app):
    """Regression Test 10: Missing country in request defaults to Germany."""
    response = client.post('/chat/ask', json={
        "message": "Where does paper go?", 
        "session_id": 303
        
    })
    
    assert response.status_code == 200
    with app.app_context():
        session = ChatSession.query.get(303)
        assert session is not None

def test_11_service_concatenation_logic(app):
    """Integration Test 6: Verifies find_rule bundles multiple rules into a single context string."""
    with app.app_context():
        r1 = WasteRule(country="Italy", material_type="Paper", bin="White", instruction="Clean paper.")
        r2 = WasteRule(country="Italy", material_type="Glass", bin="Green", instruction="Empty jars.")
        r3 = WasteRule(country="Italy", material_type="Plastic", bin="Yellow", instruction="Rinsed plastic.")
        db.session.add_all([r1, r2, r3])
        db.session.commit()
        
        service = ChatbotService(session_id=1, message="Help")
        combined_string = service.find_rule("Italy")
        
        # Check if all instructions were bundled
        assert "White" in combined_string
        assert "Green" in combined_string
        assert "Yellow" in combined_string

def test_12_api_failure_graceful_handling(app):
    """Integration Test 7: Simulates an Azure OpenAI crash to ensure the service doesn't break the server."""
    with app.app_context():
        service = ChatbotService(session_id=1, message="Crash test")
        
        # We use 'patch' to temporarily mock the Azure client inside the service and force an error
        with patch.object(service.client.responses, 'create', side_effect=Exception("Azure Timeout")):
            reply = service.send_reply(user_country="Germany", user_id=1)
            
            # The try/except block in send_reply should catch this and return a fallback string
            assert "Error connecting" in reply

def test_13_chat_session_toggle_active(app):
    """Integration Test 8: Verifies the session can be explicitly closed (active=False)."""
    with app.app_context():
        session = ChatSession(session_id=404)
        db.session.add(session)
        db.session.commit()
        
        # Update state via setter
        session.set_active(False)
        db.session.commit()
        
        updated_session = ChatSession.query.get(404)
        assert updated_session.get_active() is False

def test_14_database_integrity_missing_fields(app):
    """Integration Test 9: Tests SQLAlchemy constraints when a required field is missing."""
    with app.app_context():
        # Missing 'sender' and 'message' which are nullable=False
        invalid_msg = ChatMessage(session_id=505, sender=None, message=None)
        db.session.add(invalid_msg)
        
        try:
            db.session.commit()
            assert False  # Should not reach here
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            assert True

def test_15_timestamp_auto_generation(app):
    """Integration Test 10: Verifies timestamps are generated automatically by the DB on insert."""
    with app.app_context():
        session = ChatSession(session_id=606)
        msg = ChatMessage(session_id=606, sender="user", message="Time check")
        db.session.add_all([session, msg])
        db.session.commit()
        
        saved_msg = ChatMessage.query.first()
        # Ensure the timestamp was automatically populated by the default=lambda function
        assert saved_msg.get_time_sent() is not None