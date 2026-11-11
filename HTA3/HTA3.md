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

## 3. Route & Database Action Mapping
*The table below documents how each Flask route interacts with the MySQL database (e.g., creating sessions, fetching history, querying rules, and sending a reply back from OpenAI API).*

| HTTP Method | Route Endpoint | Database Actions Description |
| :--- | :--- | :--- |
| POST|localhost:8000/ask |**Direct Route Actions:**<br>• Retrieves a `ChatSession` record matching the provided `session_id`.<br>• Creates and commits a new `ChatSession` record if the session does not already exist.<br>• Instantiates and commits a new `ChatMessage` record to save the user's text.<br>• Executes `db.session.rollback()` to revert pending database changes if an exception occurs.<br><br>**Service Actions: <br> 1. `send_reply()`:**<br>• Queries the `WasteRule` table to find rules matching the user's country and material type.<br>• Instantiates a new `ChatMessage` entity setting the sender as "assistant" to store the AI's generated response.<br>  2. `get_user_stats()`:<br>• Queries the database table `Scans` to count the number of scans of a specific material a user has saved. <br>• Send results back to api request `/ask`. <br>•Executes `db.session.add()` and `db.session.commit()` to save the AI's reply to the database |
|GET |localhost:8000/sessions|• Queries the `ChatSession` table to retrieve all existing chat session records.<br>• Orders the retrieved session records in descending order (from newest to oldest) based on their `session_id`. <br> • Returns all existing chat sessions to the frontend to be displayed in the chatbot as chat history. |
|GET |localhost:8000/history |• Queries the `ChatMessage` table for all records matching the provided `session_id`.<br>• Orders the retrieved messages chronologically (ascending) based on the `time_sent` attribute. <br> • Sends pavload back to frontend to be displayed in chatbot interface. |
