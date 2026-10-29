import os
from openai import OpenAI

# Initialize the standard OpenAI client configured with your Azure AI Foundry endpoint & key
client = OpenAI(
    base_url=os.environ.get("AZURE_OPENAI_ENDPOINT"),
    api_key=os.environ.get("AZURE_OPENAI_API_KEY")
)

DEPLOYMENT_NAME = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")

def fetch_local_waste_rules(country_name: str) -> str:
    knowledge_base = {
        "Germany": (
            "Paper and cardboard go in the Blue Bin (Blaue Tonne). "
            "Clean plastic, metal, and composite packaging go in the Yellow Bin/Bag (Gelbe Tonne/Gelber Sack). "
            "Food and garden waste go in the Brown Organic Bin (Biotonne). "
            "Greasy pizza boxes and non-recyclables go in the Black/Grey Residual Waste Bin (Restmüll). "
            "Glass bottles must be sorted by color into neighborhood glass containers."
        ),
        "France": (
            "All plastic, metal, and paper/cardboard packaging goes into the Yellow Bin (Bac Jaune). "
            "Glass bottles and jars go into the Green Bin/Container."
        )
    }
    return knowledge_base.get(country_name, "Follow standard municipal sorting guidelines.")

def get_chatbot_response(user_message: str, selected_country: str = "Germany", conversation_history: list = None) -> str:
    if conversation_history is None:
        conversation_history = []

    local_rules = fetch_local_waste_rules(selected_country)

    system_prompt = {
        "role": "system",
        "content": (
            f"You are an AI Waste Sorting Assistant. "
            f"Answer the user strictly using the recycling rules for {selected_country}: {local_rules} "
            f"If a question is outside the scope of waste management, politely redirect the user back to recycling topics."
        )
    }

    # Assemble payload: system prompt + history + current user message
    messages_payload = [system_prompt] + conversation_history + [{"role": "user", "content": user_message}]

    try:
        # Use standard chat completions endpoint
        response = client.responses.create(
            model=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME"),
            input=messages_payload,
            
        )
        return response.output_text
    except Exception as e:
        return f"Error connecting to Azure OpenAI: {str(e)}"