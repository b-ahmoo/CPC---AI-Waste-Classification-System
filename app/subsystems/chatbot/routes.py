from flask import Blueprint, render_template, request, jsonify, session
from app.subsystems.chatbot.rag_service import get_chatbot_response
from app.extensions import db
from app.models.dummy import DummyItem

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

@chatbot_bp.route('/send', methods=['POST'])
def send_message():
    data = request.get_json()
    user_query = data.get('message', '').strip()

    selected_country = data.get('country', 'Germany')

    if not user_query:
        return jsonify({'response': 'Please enter a valid question.'}), 400

    # Retrieve past conversation turns from the Flask session
    history = session.get('chat_history', [])

    # Call Azure OpenAI via our service
    ai_response = get_chatbot_response(
        user_message=user_query,
        selected_country=selected_country,
        
    )

    # Save this turn in session history (keep last 10 messages to save tokens)
    history.append({"role": "user", "content": user_query})
    history.append({"role": "assistant", "content": ai_response})
    session['chat_history'] = history[-10:]
    session.modified = True

    return jsonify({'response': ai_response})