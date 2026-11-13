# CPC - AI Waste Classification System

An AI-driven application designed to assist users with waste classification and regional recycling guidelines using computer vision and conversational AI.

# MVP Features Documentation: AI Waste Classification System

This document outlines the Minimum Viable Product (MVP) features and database requirements for the four core subsystems of the AI Waste Classification project.
Video presentation[Video](https://fhdoprod-my.sharepoint.com/:v:/g/personal/bhavisha_ah-moo001_stud_fh-dortmund_de/IQCw4QMQDkkTRJKp8Hde1psBAecwh9GS1B2Y8PEygrLbsyo)

---
# Team members and assigned subsystems

* Ah-Moo Bhavisha (7226049) - Educational Chatbot
* Srivaishnavi Jakku (7225998) - Statistical Dashboard
* Swarbhanu Bandyopadhaya (7226982) - Classification System
* Sejal Dolas ( 7226366 ) - User Management
---
# Home Task Assignments
Link to video presentations for the home task assignments  can be found below. Access only with an FH-Dortmund account.

### Home Task Assignment 1
Branch: [hometaskassignment001](https://github.com/b-ahmoo/CPC---AI-Waste-Classification-System/tree/hometaskassignment001)  
Video:[Video HTA1](https://fhdoprod-my.sharepoint.com/:v:/r/personal/bhavisha_ah-moo001_stud_fh-dortmund_de/Documents/MDTSem1/CPC/Capstone/HomeTaskAssignment%20Videos/Group3_HomeTaskAssignment1.mp4?d=wd3aec5dd936c4e9a9eceb3ea7e8f70a9&csf=1&web=1&nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=zaWQr1)

### Home Task Assignment 2
Branch: [HomeworkAssignment2](https://github.com/b-ahmoo/CPC---AI-Waste-Classification-System/tree/HomeworkAssignment2)  
Video: [Video HTA2](https://fhdoprod-my.sharepoint.com/:v:/r/personal/bhavisha_ah-moo001_stud_fh-dortmund_de/Documents/MDTSem1/CPC/Capstone/HomeTaskAssignment%20Videos/Group3_HomeTaskAssignment2.mp4?d=w5af3f756afcc456185820c3f00a66ad2&csf=1&web=1&nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=xhRyno)  

### Home Task Assignment 3
Branch: [HomeworkAssignment3](https://github.com/b-ahmoo/CPC---AI-Waste-Classification-System/tree/HomeworkAssignment3)  
Video: [Video HTA3](https://fhdoprod-my.sharepoint.com/:v:/r/personal/bhavisha_ah-moo001_stud_fh-dortmund_de/Documents/MDTSem1/CPC/Capstone/HomeTaskAssignment%20Videos/Group3_HomeTaskAssignment3.mp4?d=wb52b4e0d50f942f9992fae9a38dc76f2&csf=1&web=1&nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=SuuB52)  

### Home Task Assignment 4  
Branch: [HomeworkAssignment4](https://github.com/b-ahmoo/CPC---AI-Waste-Classification-System/tree/HomeworkAssignment4)  
Video: [Video HTA4](https://fhdoprod-my.sharepoint.com/:v:/g/personal/bhavisha_ah-moo001_stud_fh-dortmund_de/IQDA8MnjKNeJSrsNb25xY20kAXG93LjWu2JPMqxCra-rMcU?nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&email=galyna.tabunshchyk%40fh-dortmund.de&e=ObBhz9)





# Class Diagrams
## 1. User Management Subsystem (Sejal Dolas)  
This module handles user creation and profile settings.

* **User creation:** Basic user creation and account setup.
* **Country selection upon set up** Must implement a minimum of 3 unique database entities.
* **Login:** User login and authentication after account creation.
* **View country specific rules:** Access a repository of local recycling rules based on selected country.

<img width="1672" height="464" alt="image" src="https://github.com/user-attachments/assets/b03420fc-87d6-463b-9c12-a7d41f94b61d" />

## 2. Waste Classification Subsystem (Swarbhanu Bandyopadhaya)  

This module handles the core computer vision and identification features.

* **Geographic Scope:** Provides basic waste classification supporting a maximum of 2 countries.
* **Data Persistence:** Every single item scanned must be saved to the database. 
  * *Example:* If a user scans 2 plastic bottles, it must create 2 separate entries in the database.
<img width="941" height="337" alt="image" src="https://github.com/user-attachments/assets/c1f2aa36-003b-4b96-b1aa-3e533e53f981" />

## 3. Educational Chatbot (Bhavisha Ah-Moo)  
This module provides conversational AI assistance for local recycling rules.

* **Core Functionality:** Basic Q&A capabilities focusing on waste disposal rules for 2 countries.
* **Session Handling:** Must include active chat session management.
* **Database Integration:** Must connect to the database to:
  * Fetch local recycling rules to feed as context to the chatbot.
  * Fetch the active user's selected country.
  * Fetch count of number of items scanned of a specific type of material.


<img width="944" height="426" alt="image" src="https://github.com/user-attachments/assets/5da769cd-4df4-4b89-9b83-3723df1bb3fc" />


## 4. Analytics Dashboard (Srivaishnavi Jakku)  
This module provides statistical insights based on classification data.

* **User Statistics:** Basic stats displaying the volume of items scanned per category for individual users. 
  * *Example:* "40% plastic scanned during the last week."
* **Government Statistics:** Basic statistical views tailored specifically for government officials and municipalities.
* **Database Integration:** Must connect to the database to fetch and filter information dynamically by selected fields.
<img width="1617" height="959" alt="image" src="https://github.com/user-attachments/assets/15cb5aa8-6590-4f17-9ea2-0f87a3dbb42c" />

---

# Setting up the project and Testing

## Prerequisites

Before running the application, ensure you have the following installed on your machine:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (ensure it is running with WSL 2 backend on Windows)
- [Git](https://git-scm.com/)

---

## Getting Started: Quickstart Guide

Follow these steps to get the project running locally without configuring a local Python environment.

### 1. Clone the Repository
```bash
git clone <GITLAB_REPO_URL>
cd CPC---AI-Waste-Classification-System
```

### 2. Configure Environment Variables
Copy the template configuration file to create your local `.env` file.

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Mac / Linux / Git Bash:**
```bash
cp .env.example .env
```

Open the `.env` file in your text editor and add your OpenAI API key and project secrets:
```env
FLASK_ENV=development
SECRET_KEY=replace-with-a-random-secret-key
AZURE_OPENAI_API_KEY=replace-with-your-open-ai-secret-key
AZURE_OPENAI_ENDPOINT=replace-with-your-open-ai-endpoint
AZURE_OPENAI_API_VERSION=replace-with-your-open-ai-version
AZURE_OPENAI_DEPLOYMENT_NAME=replace-with-your-deployment-name
MYSQL_USER=waste_user
MYSQL_PASSWORD=waste_password
MYSQL_DATABASE=waste_assistant_db
DATABASE_URL=mysql+pymysql://waste_user:waste_password@db:3306/waste_assistant_db
```

### 3. Build and Start the Application
Run Docker Compose to build the image and launch the web server:
```bash
docker compose up --build
```

### Note:

Make sure you are on the `main` branch when running the docker and testing the application. The `main` branch contains the completed system.

### 4. Access the Application
Open your web browser and navigate to: [http://localhost:8000](http://localhost:8000)

To stop the application, press `Ctrl + C` in your terminal, or run:
```bash
docker compose down
```

### 5. Access the Database  

Open your web browser and navigate to: [http://localhost:8080](http://localhost:8080)

**Upgrading an existing database.** If your database was created before the classification
routing code feature was added, the `scans` table has no `routing_code` column and the
classification page will report that the database is unavailable. The `user_id` column
in `scans`, and the same column in `chat_sessions`, also need widening to hold the string ids
issued by the user management subsystem. Run all three changes once:

```bash
docker compose exec db sh -c 'mysql -u root -prootpassword "$MYSQL_DATABASE" -e "ALTER TABLE scans ADD COLUMN routing_code VARCHAR(10) NOT NULL DEFAULT \"\"; ALTER TABLE scans MODIFY COLUMN user_id VARCHAR(50) NULL; ALTER TABLE chat_sessions MODIFY COLUMN user_id VARCHAR(50) NULL;"'
```

This reads the database name from your `.env`, so it works whatever you called it. A fresh
setup does not need this — the column is created with the table.


### 6. Routes

The subsystems can be accessed and tested at the following routes:

* User management:
* Chatbot: [http://localhost:8000/chat](http://localhost:8000/chat)
* Classification: [http://localhost:8000/classify](http://localhost:8000/classify)
* Dashboard: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)


---

# The following sections are intended for documentation purposes only.

The following sections document the project architecture, programming guidelines to follow and CI/CD pipelines to abide by. These sections are intended for members of the group working on the project but can be considered for understanding the architecture of the system.

## Branching Guidelines

* **Do not** commit directly to `main`.
* **Branch naming convention:** `feature/<subsystem>/<feature>` (e.g., `feature/chatbot/chatbot-setup`).
* Once your task is complete and tested, create a pull request and resolve any conflicts that may arise.
* Home task assignments have their own dedicated branches. Therefore in addition to merging your home task assignments on main, also merge in the respective branches.


## Database & Object-Oriented Architecture Guide

This section documents our team's database infrastructure, Object-Relational Mapping (ORM) setup, and the strict guidelines required for implementing Object-Oriented Programming (OOP) classes in each subsystem. Following these guidelines ensures your classes successfully generate MySQL tables and meet the assignment's explicit database integration rubric.

### 1. Technology Stack & Rationale
* **MySQL 8.0:** Acts as our core relational database. It provides a robust, persistent storage layer required to prove explicit database integration for the final submission.
* **phpMyAdmin:** A web-based graphical interface running alongside our containers. It allows team members to visually verify that their subsystem tables and data records are generating correctly without needing to write raw SQL queries in the terminal.
* **Flask-SQLAlchemy (ORM):** The Object-Relational Mapper bridges our Python OOP code with the MySQL database. It automatically translates Python class blueprints into MySQL tables. We use this to keep our codebase entirely in Python while satisfying the database integration requirement.

### 2. Class Implementation Guidelines for Team Members
To prevent critical bugs where subsystem tables fail to generate in MySQL, all team members must strictly distinguish between **Data Entities** and **Service Classes**. Our subsystem architectures rely heavily on Composition and Service Delegation, meaning these two types of classes are written differently.

#### A. Data Entities (Must use `db.Model`)
If your class represents data that needs to be permanently saved to the database (e.g., `ChatSession`, `WasteRule`, `ClassificationRecord`), **it must inherit from `db.Model`**.
* **State Initialization:** Do not write a traditional `__init__` constructor. SQLAlchemy generates this automatically. Instead, define your state variables as `db.Column` attributes.
* **Encapsulation:** To satisfy the assignment rubric, you must manually write explicit Getters and Setters (e.g., `get_confidence(self)`, `set_confidence(self, value)`) for every column attribute.

**Example Data Entity Structure:**
```python
from app.extensions import db

class ClassificationRecord(db.Model):
    __tablename__ = 'classification_records'

    # 1. State Initialization (Database Columns)
    record_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    confidence = db.Column(db.Float, nullable=False, default=0.0)

    # 2. Encapsulation
    def get_record_id(self):
        return self.record_id

    def set_record_id(self, record_id):
        self.record_id = record_id
        
    def get_confidence(self):
        return self.confidence

    def set_confidence(self, confidence):
        self.confidence = float(confidence)
```

#### B. Service Classes (Standard Python Classes)
If your class handles business logic, processing, or acts as a middleman (e.g., `ChatbotService`), it does not belong in the database.
* **Do not** inherit from `db.Model`.
* **Do** write a traditional `def __init__(self):` constructor to initialize state.
* **Do** write explicit Getters and Setters for its internal variables.

### 3. Registering Your Classes to Generate Tables
SQLAlchemy's `db.create_all()` command executes exactly once during the Flask app initialization. It does not automatically scan the project folder for new files. **If your class is not explicitly imported before this command runs, your MySQL table will not be created.**

**How to register your subsystem models:**
1. Open the centralized application factory file: `app/__init__.py`.
2. Locate the `with app.app_context():` block.
3. Import your specific model directly into this block *before* the `db.create_all()` execution.

```python
    with app.app_context():
        # Import your subsystem models here so SQLAlchemy detects them
        from app.models.chatbot import ChatSession, ChatMessage, WasteRule
        from app.models.dashboard import ClassificationRecord
        
        # Generates all detected models into MySQL tables
        db.create_all()
```

### 4. Troubleshooting Table Generation
If you navigate to phpMyAdmin and do not see your new tables, verify the following steps:
1. **Check your class definition:** Ensure your class inherits from `(db.Model)` and uses `db.Column`. Regular Python classes exist only in temporary memory and will never generate a MySQL table.
2. **Check your imports:** Ensure your file is explicitly imported inside the `app.app_context()` block in `app/__init__.py`.
3. **Rebuild the Container:** The database generation command only runs on startup. If you add a new model, you must completely restart the Docker environment for it to take effect. Run the following commands in your terminal:

```bash
docker compose down
docker compose up --build
```
