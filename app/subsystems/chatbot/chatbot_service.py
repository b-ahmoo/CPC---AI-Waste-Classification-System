import os
from openai import OpenAI
from app.models import WasteRule, ChatMessage
from app.extensions import db

class ChatbotService:
    #  Constructor and State Initialization
    def __init__(self, session_id: int, message: str):
        self.session_id = session_id
        self.message = message
        
        # Azure OpenAI client inside the constructor
        self.client = OpenAI(
            base_url=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_key=os.environ.get("AZURE_OPENAI_API_KEY")
        )
        self.deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")

    # 2. Encapsulation (Getter)
    def get_message(self):
        return self.message

    # 3. find rule from database
    def find_rule(self, user_country: str, user_material: str) -> str:
        """Replaces the old fetch_local_waste_rules() dictionary with a DB query."""
        rule = WasteRule.query.filter_by(
            country=user_country, 
            material_type=user_material
        ).first()
        
        if rule:
            return rule.get_instruction()
        return "Follow standard municipal sorting guidelines."

    def send_reply(self, user_country: str, user_material: str, conversation_history: list = None) -> str:
        """Replaces get_chatbot_response(), integrating DB rules and OpenAI."""
        if conversation_history is None:
            conversation_history = []

        # 1. Fetch the rule dynamically from the database
        local_rules = self.find_rule(user_country, user_material)

        # 2. Build the system prompt
        system_prompt = {
            "role": "system",
            "content": (
                f"You are an AI Waste Sorting Assistant. "
                f"Answer the user strictly using these recycling rules for {user_country}: {local_rules} "
                f"If a question is outside the scope of waste management, politely redirect the user back to recycling topics."
            )
        }

        # 3. Assemble payload
        messages_payload = [system_prompt] + conversation_history + [{"role": "user", "content": self.message}]

        try:
            # 4. Call Azure OpenAI
            response = self.client.responses.create(
                model=self.deployment_name,
                input=messages_payload,
            )
            ai_reply_text = response.output_text
            
            # 5. Save the AI's reply to the database
            ai_message = ChatMessage(
                session_id=self.session_id, 
                sender="assistant", 
                message=ai_reply_text
            )
            db.session.add(ai_message)
            db.session.commit()
            
            return ai_reply_text
            
        except Exception as e:
            return f"Error connecting to Azure OpenAI: {str(e)}"