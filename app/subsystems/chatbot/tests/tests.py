import pytest
import sqlalchemy
from unittest.mock import patch, MagicMock
from app.models import ChatSession, ChatMessage, WasteRule
from app.models.usermanagement_models import User
from app.subsystems.chatbot.chatbot_service import ChatbotService
from app.extensions import db

# Unit Tests. to run : docker compose exec web python -m pytest --cov=app/subsystems/chatbot app/subsystems/chatbot/tests/tests.py::test_10_default_country_fallback
@pytest.fixture(autouse=True)
def mock_azure_openai():
    """
    Automatically mocks the OpenAI client across ALL tests so real API credits 
    are never used, while still allowing ChatbotService to save replies to the DB.
    """
    with patch("app.subsystems.chatbot.chatbot_service.OpenAI") as mock_openai_class:
        #  fake client instance
        mock_client_instance = MagicMock()
        
        #  fake response object with .output_text
        mock_response = MagicMock()
        mock_response.output_text = "Mocked AI Reply: Follow local municipal guidelines."
        
        #  return the fake response
        mock_client_instance.responses.create.return_value = mock_response
        mock_openai_class.return_value = mock_client_instance
        
        yield mock_client_instance

    
def test_01_waste_rule_constructor_and_getters(app):
    """UNIT TEST 1: Verifies WasteRule constructor and getters work."""
    #checked
    with app.app_context():
        # Create a rule using constructor
        rule = WasteRule(
            country="Italy", 
            material_type="Paper", 
            bin="Blue Bin", 
            instruction="Clean paper and cardboard goes here."
        )
        # Test the getters
        assert rule.get_country() == "Italy"
        assert rule.get_bin() == "Blue Bin"
        assert rule.get_instruction() == "Clean paper and cardboard goes here."

def test_02_chat_session_constructor_and_setters(app):
    """UNIT TEST 2: Verifies ChatSession state initialization and setters."""
    #checked
    with app.app_context():
        # Test constructor defaults
        session = ChatSession(user_id="testuser@user.com")
        assert session.get_user_id() == "testuser@user.com"
        assert session.get_active() is True
        
        # Test the setter
        session.set_active(False)
        assert session.get_active() is False

def test_03_chat_message_database_save(app):
    """UNIT TEST 3: Verifies ChatMessage can be saved and retrieved from database."""
    #checked
    with app.app_context():
        # 1. Create and save a  session first
        session = ChatSession(user_id="testuser@email.com")
        db.session.add(session)
        db.session.commit()
        
        # 2. Create and save the message
        msg = ChatMessage(session_id=session._session_id, sender="user", message="Hello")
        db.session.add(msg)
        db.session.commit()
        
        # 3. Retrieveand verify
        saved_msg = ChatMessage.query.filter_by(session_id = session._session_id).first()
        assert saved_msg.get_sender() == "user"
        assert saved_msg.get_message() == "Hello"

def test_04_service_find_rule_success(app):
    """UNIT TEST 4: Verifies ChatbotService finds existing rules in the DB."""
    #checked
    with app.app_context():
        # 1. Insert rule into the test database
        rule = WasteRule(country="Italy", material_type="Glass", bin="Green Bin", instruction="Empty glass jars, empty glass bottles.")
        db.session.add(rule)
        db.session.commit()
        
        # 2. Testservice method
        service = ChatbotService(session_id=1, message="Where does glass go?")
        result = service.find_rule("Italy")
        
        assert "Green Bin" in result
        assert "Empty glass jars, empty glass bottles." in result

def test_05_service_find_rule_fallback(app):
    """UNIT TEST 5: Verifies ChatbotService returns fallback if rule doesn't exist."""
    #checked
    with app.app_context():
        new_session = ChatSession(session_id=1, user_id="test1@email.com")
        db.session.add(new_session)
        db.session.commit()
        service = ChatbotService(session_id=1, message="Where does this go?")
        # Asking for a country/material not in the DB
        result = service.find_rule("Mars")
        
        assert result == "Follow standard municipal sorting guidelines for Mars."


def test_06_history_route_success(client, app):
    """Regression Test 6: Fetching history for an existing session returns correct data."""
    #checked - change session id before testing
    with app.app_context():
        new_id = 103
        # Setup: Create a session and messages manually
        newsession = ChatSession(session_id=new_id, user_id="test2@email.com")
        msg1 = ChatMessage(session_id=new_id, sender="user", message="Hi")
        msg2 = ChatMessage(session_id=new_id, sender="assistant", message="Hello")
        db.session.add_all([newsession, msg1, msg2])
        db.session.commit()
        
    # Action: Request the history
    response = client.get(f'/chat/history/{new_id}')
    
    # Verify: The route should return the messages
    assert response.status_code == 200
    assert len(response.json["messages"]) == 2
    assert response.json["messages"][0]["sender"] == "user"

def test_07_history_route_not_found(client):
    """Regression Test 7: Fetching history for a non-existent session returns 404."""
    #checked
    response = client.get('/chat/history/99999')
    assert response.status_code == 404
    assert "error" in response.json['status']

def test_08_session_reuse(client, app):
    """Regression Test 8: Sending multiple messages to the same session appends to history."""
    #checked 
    # First message creates the session dynamically
    new_id = 203
    # Setup: Create a session and messages manually
    newsession = ChatSession(session_id=new_id, user_id="test1@email.com")
    db.session.add(newsession)
    db.session.commit()
    client.post('/chat/ask', json={"message": "Where do plastic pens go?", "session_id": new_id, "user_id":"test1@email.com", "country": "c1"})
    # Second message reuses the session
    client.post('/chat/ask', json={"message": "Where do old metal cutlery go?", "session_id": new_id,  "user_id":"test1@email.com", "country": "c1"})
    
    with app.app_context():
        messages = ChatMessage.query.filter_by(session_id=new_id, sender="user").all()
        assert len(messages) == 2
        assert messages[0].get_message() == "Where do plastic pens go?"
        assert messages[1].get_message() == "Where do old metal cutlery go?"

def test_09_empty_payload_validation(client):
    """Regression Test 9: Submitting a completely empty JSON payload returns a 400 Bad Request."""
    #checked
    response = client.post('/chat/ask', json={})
    assert response.status_code == 400
    assert "error" in response.json

def test_10_default_country_fallback(client, app):
    """Regression Test 10: Missing country in request defaults to Germany."""
    #checked
    new_id = 403
    # Setup: Create a session and messages manually
    newsession = ChatSession(session_id=new_id, user_id="test1@email.com")
    db.session.add(newsession)
    db.session.commit()
    response = client.post('/chat/ask', json={
        "message": "Where does paper go?", 
        "session_id": new_id,
        "user_id": "test1@email.com",
        "country":""
        
    })
    
    assert response.status_code == 200
    with app.app_context():
        session = ChatSession.query.get(new_id)
        assert session is not None

def test_11_service_concatenation_logic(app):
    """Integration Test 6: Verifies find_rule bundles multiple rules into a single context string."""
    #checked
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
    #checked
    with app.app_context():
        service = ChatbotService(session_id=103, message="Crash test")
        
        #use 'patch' to temporarily mock the Azure client inside the service and force an error
        with patch.object(service.client.responses, 'create', side_effect=Exception("Azure Timeout")):
            reply = service.send_reply(user_country="Germany", user_id="test1@email.com")
            
            # The try/except block in send_reply should catch this and return a fallback string
            assert "Error connecting to Azure OpenAI" in reply

def test_13_chat_session_toggle_active(app):
    """Integration Test 8: Verifies the session can be explicitly closed (active=False)."""
    with app.app_context():
        session = ChatSession(session_id=404, user_id="test2@email.com")
        db.session.add(session)
        db.session.commit()
        
        # Update state via setter
        session.set_active(False)
        db.session.commit()
        
        updated_session = ChatSession.query.get(404)
        assert updated_session.get_active() is False

def test_14_database_integrity_missing_fields(app):
    """Integration Test 9: Tests SQLAlchemy constraints when a required field is missing."""
    #checked
    with app.app_context():
        # Missing 'sender' and 'message' which are nullable=False
        invalid_msg = ChatMessage(session_id=103, sender=None, message=None)
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
        session = ChatSession(session_id=606, user_id="test1@email.com")
        msg = ChatMessage(session_id=606, sender="user", message="Time check")
        db.session.add_all([session, msg])
        db.session.commit()
        
        saved_msg = ChatMessage.query.first()
        # Ensure the timestamp was automatically populated by the default=lambda function
        assert saved_msg.get_time_sent() is not None