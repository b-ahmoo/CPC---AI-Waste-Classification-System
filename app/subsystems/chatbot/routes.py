from flask import Blueprint, render_template, request, jsonify, session
from sqlalchemy import func
from app.extensions import db
from app.models.dummy import DummyItem
from app.models.chat_message import ChatMessage
from app.models.chat_sessions import ChatSession
from app.models.scan import Scan
from app.subsystems.chatbot.chatbot_service import ChatbotService

chatbot_bp = Blueprint('chatbot_bp', __name__)

@chatbot_bp.route('/')
def chat_home():
    if 'chat_history' not in session:
        session['chat_history'] = []
    return render_template('chatbot/chat.html')



# API call to bridge gap between frontend and backend. /ask accepts user data from frontend, formats it, then forwrds it to the backedn
# via the chatbot service class, which connects to Open AI API.
# also saves user and bot messages to database
# sends message from chatbot service to front end
@chatbot_bp.route('/ask', methods=['POST'])
def ask_chatbot():
    #Get the data from the user's interface (frontend)
    data = request.get_json()
    user_text = data.get('message')
    user_id = data.get('user_id')
    session_id = data.get('session_id')
    user_country = data.get('country', 'Germany')
    user_material = data.get('material_type', 'General')

  

    if not data or not user_text or not session_id:
        return jsonify({"error": "Message and session_id are required", "status_code":400}), 400

    try:
        session = ChatSession.query.get(session_id)
        print(f"session = {session}")
        if not session:
            # If the session doesn't exist, create it and save it to the DB
            new_session = ChatSession(session_id=session_id)
            db.session.add(new_session)
            db.session.commit()
        

        # Save the User's message to the database
        user_message = ChatMessage(
            session_id=session_id,
            sender="user",
            message=user_text
        )
        db.session.add(user_message)
        db.session.commit()

        # Instantiate new Service Class
        
        ai_service = ChatbotService(session_id=session_id, message=user_text)

        # Trigger the business logic to get the AI response
        
        ai_reply_text = ai_service.send_reply(user_country, user_id)

        # Send the AI's text back to the frontend interface
        return jsonify({
            "status": "success",
            "reply": ai_reply_text
        }), 200

    except Exception as e:
        db.session.rollback()
        
        print(f"Error in ask_chatbot route: {e}")
        
       
        return jsonify({
            "status": "error", 
            "message": "An error occurred processing your request."
        }), 400



@chatbot_bp.route('/sessions', methods=['GET'])
def get_sessions():

    try:
   
        # Query the database for all sessions, ordered from newest to oldest
        sessions = ChatSession.query.order_by(ChatSession.session_id.desc()).all()
        
        # Format into a JSON list
        session_list = [{"session_id": s.session_id, "created_at": s.created_at.isoformat() if s.created_at else None} for s in sessions]
        
        return jsonify({"status": "success", "sessions": session_list})
    
    except Exception as e:
        print(f"Error in /sessions route: {e}")
            
        return jsonify({
                    "status": "error", 
                    "message": "An error occurred when finding past sessions."
                }), 500



@chatbot_bp.route('/history/<int:session_id>', methods=['GET'])
def get_chat_history(session_id):
    """Fetches all messages from DB table chat_messages for a specific chat session."""
    # Query messages ordered by time sent

    try:
        messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.time_sent.asc()).all()

        if messages:
        
            # Format the data into a JSON list
            message_list = [
                {
                    "sender": msg.sender, 
                    "message": msg.message
                } for msg in messages
            ]
            
            return jsonify({"status": "success", "messages": message_list})
        else:
            return jsonify({
                                "status": "error", 
                                "message": "An error occurred fetching chat history from database."
                            }), 404


    except Exception as e:
          print(f"Error in history route: {e}")
          return jsonify({
                    "status": "error", 
                    "message": "An error occurred fetching chat history from database."
                }), 404


