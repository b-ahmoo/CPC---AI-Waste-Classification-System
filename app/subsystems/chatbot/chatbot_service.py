import os
from openai import OpenAI
from app.models import WasteRule, ChatMessage
from app.models.scan import Scan
from app.extensions import db
from sqlalchemy import func

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

    # (Getter)
    def get_message(self):
        return self.message

    #  find rules from database for specific country
    def find_rule(self, user_country: str) -> str:

        try:
            rules = WasteRule.query.filter_by(
                country=user_country
            ).all()

            if not rules:
                return f"Follow standard municipal sorting guidelines for {user_country}."

            combined_rules = ""
            for r in rules:
                combined_rules += f"Bin: {r.get_bin()}. Instructions: {r.get_instruction()} | "
            return combined_rules

        except Exception as e:
            print(f"Database error while fetching rule : {e}")
            return f"Follow standard municipal sorting guidelines."

        return f"Follow standard municipal sorting guidelines for {user_country}."


    # assemble payload and send rule + prompt to open ai api to receive a response to display back to user
    def send_reply(self, user_country: str, user_id: int, conversation_history: list = None) -> str:
        """Replaces get_chatbot_response(), integrating DB rules and OpenAI."""
        if conversation_history is None:
            conversation_history = []

        #  Fetch the rule dynamically from the database
        local_rules = self.find_rule(user_country)
        # also fetch user stats, if any
        user_stats = self.get_user_stats(user_id)

        # Build the system prompt
        system_prompt = {
            "role": "system",
            "content": (
                f"You are an AI Waste Sorting Assistant. "
                f"Answer the user strictly using these recycling rules for {user_country} and other knowledge you may find regarding the following rules: {local_rules} "
                f"If a question is outside the scope of waste management, politely redirect the user back to recycling topics."
                f"If a question is about stats, strictly use user's personal scans data : {user_stats}."
            )
        }

        # Assemble payload
        messages_payload = [system_prompt] + conversation_history + [{"role": "user", "content": self.message}]

        try:
            #  Call Azure OpenAI
            response = self.client.responses.create(
                model=self.deployment_name,
                input=messages_payload,
            )
            ai_reply_text = response.output_text
            
            # Save the AI's reply to the database
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


    # for a specific user, filter Scans table to find and count all material types scanned
    # connected with subsystem 2 - classification
    def get_user_stats(self, user_id: int)->str:

        try:
            scan_counts = Scan.query.with_entities(
                Scan.material,
                func.count(Scan.id)
                ).filter_by(user_id=user_id).group_by(Scan.material).all()
            
            if not scan_counts:
                return "You have not scanned any items yet."

            stats_dict = {bin_name: count for bin_name, count in scan_counts}

            formatted_stats = "Your scan history is: "
            for bin_name, count in stats_dict.items():
                formatted_stats += f"{count} items in the {bin_name}, "
                
            return formatted_stats.strip(", ")
        except Exception as e:
            return f"Error finding user scans : {e}"

        
        

        
            