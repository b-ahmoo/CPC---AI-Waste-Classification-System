from flask import Blueprint, render_template, request, jsonify, session
from app.subsystems.chatbot.rag_service import get_chatbot_response
from app.extensions import db
from app.models.dummy import DummyItem
from app.models.chat_message import ChatMessage
from app.models.chat_sessions import ChatSession
from app.subsystems.chatbot.chatbot_service import ChatbotService

chatbot_bp = Blueprint('chatbot_bp', __name__)

@chatbot_bp.route('/test-dummy', methods=['GET'])
def test_create_dummy():
    try:
        # 1. Instantiate the dummy entity object
        item = DummyItem(name="Test Recyclable", description="Checking if MySQL is saving data.")
        
        # 2. Add to the database session and commit
        db.session.add(item)
        db.session.commit()

        # 3. Query all items back to verify
        all_items = DummyItem.query.all()
        item_names = [i.name for i in all_items]

        return jsonify({
            "status": "success",
            "message": "Dummy entity created and saved to MySQL successfully!",
            "saved_items_in_db": item_names
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@chatbot_bp.route('/')
def chat_home():
    if 'chat_history' not in session:
        session['chat_history'] = []
    return render_template('chatbot/chat.html')

# @chatbot_bp.route('/send', methods=['POST'])
# def send_message():
#     data = request.get_json()
#     user_query = data.get('message', '').strip()

#     selected_country = data.get('country', 'Germany')

#     if not user_query:
#         return jsonify({'response': 'Please enter a valid question.'}), 400

#     # Retrieve past conversation turns from the Flask session
#     history = session.get('chat_history', [])

#     # Call Azure OpenAI via our service
#     ai_response = get_chatbot_response(
#         user_message=user_query,
#         selected_country=selected_country,
        
#     )

#     # Save this turn in session history (keep last 10 messages to save tokens)
#     history.append({"role": "user", "content": user_query})
#     history.append({"role": "assistant", "content": ai_response})
#     session['chat_history'] = history[-10:]
#     session.modified = True

#     return jsonify({'response': ai_response})


@chatbot_bp.route('/ask', methods=['POST'])
def ask_chatbot():
    # 1. Get the data from the user's interface (frontend)
    data = request.get_json()
    user_text = data.get('message')
    session_id = data.get('session_id')
    user_country = data.get('country', 'Germany')
    user_material = data.get('material_type', 'General')


    if not user_text or not session_id:
        return jsonify({"error": "Message and session_id are required"}), 400

   
    session = ChatSession.query.get(session_id)
    if not session:
        # If the session doesn't exist, create it and save it to the DB
        new_session = ChatSession(session_id=session_id)
        db.session.add(new_session)
        db.session.commit()
    

    # 2. Save the User's message to the database
    user_message = ChatMessage(
        session_id=session_id,
        sender="user",
        message=user_text
    )
    db.session.add(user_message)
    db.session.commit()

    # 3. Instantiate new Service Class
    # We pass the session_id and the user's message into the constructor
    ai_service = ChatbotService(session_id=session_id, message=user_text)

    # 4. Trigger the business logic to get the AI response
    # (This automatically queries the WasteRule table and saves the AI's reply to the DB)
    ai_reply_text = ai_service.send_reply(user_country, user_material)

    # 5. Send the AI's text back to the frontend interface
    return jsonify({
        "status": "success",
        "reply": ai_reply_text
    })


@chatbot_bp.route('/sessions', methods=['GET'])
def get_sessions():
    """Fetches all past chat sessions to display in the sidebar."""
    # Query the database for all sessions, ordered from newest to oldest
    sessions = ChatSession.query.order_by(ChatSession.session_id.desc()).all()
    
    # Format into a JSON list
    session_list = [{"session_id": s.session_id} for s in sessions]
    
    return jsonify({"status": "success", "sessions": session_list})