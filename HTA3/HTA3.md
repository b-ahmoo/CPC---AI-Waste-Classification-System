# Home Task Assignment 3

### Video
Branch: [HomeworkAssignment3](https://github.com/b-ahmoo/CPC---AI-Waste-Classification-System/tree/HomeworkAssignment3)  
Video: [Video HTA3](https://fhdoprod-my.sharepoint.com/:v:/r/personal/bhavisha_ah-moo001_stud_fh-dortmund_de/Documents/MDTSem1/CPC/Capstone/HomeTaskAssignment%20Videos/Group3_HomeTaskAssignment3.mp4?d=wb52b4e0d50f942f9992fae9a38dc76f2&csf=1&web=1&nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=SuuB52) 

## Home Assignment 3: Flask + MySQL Data Output – Statistical Dashboard

**Student:** Srivaishnavi Jakku · **Student ID:** 7225998 · **Subsystem:** Statistical Dashboard
**GitHub project:** https://github.com/b-ahmoo/CPC---AI-Waste-Classification-System

The Statistical Dashboard is a Flask blueprint (`app/subsystems/dashboard`) that uses the project's shared MySQL database through Flask-SQLAlchemy. It reads the classification results stored in the `scans` table, calculates statistics, stores them in its own tables, and outputs the data on two pages.

| Page | URL | What it shows |
|---|---|---|
| Overview | http://localhost:8000/dashboard/ | Summary cards (items classified, Pfand items, materials detected), items-by-bin chart, activity-over-time chart |
| Data | http://localhost:8000/dashboard/data | The rows of the `scans` table, filterable by material, bin and time period, plus the latest saved snapshots from `dashboard_snapshots` |

**MySQL tables used**

| Table | Model | Role |
|---|---|---|
| `scans` | `Scan` (classification subsystem) | Source data: one row per classified item |
| `dashboard_settings` | `DashboardSetting` | Mock or live data, time range |
| `dashboard_snapshots` | `DashboardSnapshot` | Statistics saved on every Overview visit |
| `bin_statistics` | `BinStatistic` | Items per bin in a snapshot |
| `daily_activity` | `DailyActivity` | Items per day in a snapshot |

**How it works:** `routes.py` handles the requests, `services.py` queries MySQL with SQLAlchemy (e.g. `Scan.query.filter(Scan.material == material).order_by(Scan.timestamp.desc())`), and the Jinja templates in `templates/dashboard/` render the results as HTML tables and charts.

**Run it**

1. Copy `.env.example` to `.env` and set the MySQL settings (`MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `DATABASE_URL=mysql+pymysql://<user>:<password>@db:3306/<database>`).
2. `docker compose up --build`
3. Open http://localhost:8000/dashboard/data and click **Add sample scans** to fill the `scans` table with example rows (they can be removed again with **Remove sample scans**).
4. Check the tables in phpMyAdmin: http://localhost:8080
5. Tests: `docker compose exec web python -m pytest app/subsystems/dashboard/tests`


# Chatbot Subsystem: Database Setup & Route Documentation

## 1. Database Architecture & Setup
*   **Database Engine:** MySQL 8.0 (Containerized via Docker)
*   **ORM (Object-Relational Mapper):** Flask-SQLAlchemy
*   **Database Driver:** PyMySQL
*   **Initialization:** Tables are generated automatically on application startup using the `db.create_all()` command within the Flask application context (`app/__init__.py`).

## 2. MySQL tables used
The chatbot subsystem relies on the following strictly encapsulated Object-Oriented models mapped to MySQL:

| Table | Model | Role |
|---|---|---|
| `chat_session` | `ChatSession`| Tracks unique conversation threads (Primary Key: `session_id`). |
| `chat_message` | `ChatMessage` |  Stores individual user and AI messages, linked to a specific session via a Foreign Key (`session_id`). |
| `waste_rule` | `WasteRule` |  Acts as the independent knowledge base, storing regional recycling instructions queried by the `ChatbotService`. |
| `scans` | `Scans` | Stores individual user scans classfied by material type. Is used by `ChatbotService` and the chatbot system to allow users to query the chatbot regarding number of scans of a specific material type recorded.|

**How it works:** `routes.py` defines the API routes and requests, `chatbot_service.py` queries MySQL with SQLAlchemy (e.g. `rules = WasteRule.query.filter_by(country=user_country).all()`), to fetch data from the database.

## 3. Route & Database Action Mapping (Internal API)
*The table below documents how each Flask route interacts with the MySQL database (e.g., creating sessions, fetching history, querying rules, and sending a reply back from OpenAI API).*

| HTTP Method | Route Endpoint | Database Actions Description |
| :--- | :--- | :--- |
| POST|localhost:8000/ask |**Direct Route Actions:**<br>• Retrieves a `ChatSession` record matching the provided `session_id`.<br>• Creates and commits a new `ChatSession` record if the session does not already exist.<br>• Instantiates and commits a new `ChatMessage` record to save the user's text.<br>• Executes `db.session.rollback()` to revert pending database changes if an exception occurs.<br><br>**Service Actions: <br> 1. `send_reply()`:**<br>• Queries the `WasteRule` table to find rules matching the user's country and material type.<br>• Instantiates a new `ChatMessage` entity setting the sender as "assistant" to store the AI's generated response.<br>  2. `get_user_stats()`:<br>• Queries the database table `Scans` to count the number of scans of a specific material a user has saved. <br>• Send results back to api request `/ask`. <br>•Executes `db.session.add()` and `db.session.commit()` to save the AI's reply to the database |
|GET |localhost:8000/sessions|• Queries the `ChatSession` table to retrieve all existing chat session records.<br>• Orders the retrieved session records in descending order (from newest to oldest) based on their `session_id`. <br> • Returns all existing chat sessions to the frontend to be displayed in the chatbot as chat history. |
|GET |localhost:8000/history |• Queries the `ChatMessage` table for all records matching the provided `session_id`.<br>• Orders the retrieved messages chronologically (ascending) based on the `time_sent` attribute. <br> • Sends pavload back to frontend to be displayed in chatbot interface. |


# Azure AI Foundry & Database Integration Guide (External API)

This document explains the architecture and implementation steps used to create a GPT API model via Azure AI Foundry and seamlessly connect it to a local relational database using a Retrieval-Augmented Generation (RAG) approach.

## 1. Model Creation in Azure AI Foundry
The first step involves deploying a model within the **Azure AI Foundry** (formerly Azure OpenAI Studio). 
1. A foundational model (e.g., `gpt-5-mini` or `gpt-4o-mini`) is selected and deployed.
2. Azure generates a custom **Deployment Name**, alongside an **Endpoint URL** and **API Key**. 
3. Unlike the standard OpenAI playground, these deployed models are completely *stateless*. They do not remember past conversations inherently, requiring our backend to pass the conversation history and database context during every API call.

## 2. Environment Configuration
To securely connect the application to the Azure Foundry model without hardcoding sensitive credentials, the connection parameters are stored in a `.env` file:

```env
AZURE_OPENAI_ENDPOINT=https://<your-resource-name>.services.ai.azure.com/openai/v1
AZURE_OPENAI_API_KEY=<your_secure_api_key>
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-mini
```

## 3. Database Access Layer (DAL) Setup
Before calling the Azure AI model, the system must retrieve local knowledge to ground the AI's response. This is handled by a **Database Access Layer (DAL)** built with Flask-SQLAlchemy. 

Instead of writing raw SQL, the backend queries Python objects. For example, the system retrieves municipal recycling rules for a specific country:
```python
rules = WasteRule.query.filter_by(country=user_country).all()
```
It can also fetch user-specific statistics (like past scanned items) to provide personalized context.

## 4. The `ChatbotService` Wrapper
To orchestrate the connection between the MySQL database and Azure AI Foundry, a dedicated service class (`ChatbotService`) is used. 

Inside the class constructor, the standard `OpenAI` Python client is initialized using the Azure endpoint provided by Foundry:
```python
from openai import OpenAI
import os

class ChatbotService:
    def __init__(self, session_id: int, message: str):
        self._session_id = session_id
        self.message = message
        
        # Initialize the client pointing to Azure AI Foundry
        self.client = OpenAI(
            base_url=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_key=os.environ.get("AZURE_OPENAI_API_KEY")
        )
        self.deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")
```

## 5. API Execution and Database Saving
When a user asks a question, the `ChatbotService` retrieves the rules from the database, bundles them with the user's prompt into a `messages_payload`, and sends the request to Azure AI Foundry. 

Using the modern Responses SDK specified by Azure Foundry for newer models, the execution looks like this:

```python
def send_reply(self, user_country: str, user_id: int, conversation_history: list = None) -> str:
    # 1. Fetch DB Context
    local_rules = self.find_rule(user_country)
    
    # 2. Build Payload
    system_prompt = {
        "role": "system",
        "content": f"You are an AI Assistant. Answer using these rules: {local_rules}"
    }
    messages_payload = [system_prompt] + conversation_history + [{"role": "user", "content": self.message}]
    
    try:
        # 3. Call Azure Foundry API
        response = self.client.responses.create(
            model=self.deployment_name,
            input=messages_payload,
        )
        
        # 4. Extract the plain text from the Azure response object
        ai_reply_text = response.output_text
        
       
```

### Summary of the Data Flow
1. **Frontend Request:** The user submits a natural language question.
2. **Database Query:** SQLAlchemy retrieves regional rules and user stats from MySQL.
3. **Azure API Call:** The `client.responses.create()` method sends the bundled context to the model deployed in Azure Foundry.
4. **Database Persistence:** The `ai_reply_text` is extracted and committed to the `ChatMessage` table as persistent history.
