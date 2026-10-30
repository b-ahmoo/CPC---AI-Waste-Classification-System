# CPC - AI Waste Classification System

An AI-driven application designed to assist users with waste classification and regional recycling guidelines using computer vision and conversational AI.

---

## Prerequisites

Before running the application, ensure you have the following installed on your machine:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (ensure it is running with WSL 2 backend on Windows)
- [Git](https://git-scm.com/)

---

## Getting Started: Quickstart Guide

Follow these steps to get the project running locally without configuring a local Python environment.

### 1. Clone the Repository
```bash
git clone <YOUR_GITLAB_REPO_URL>
cd cpc-ai-waste-classification-system
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
OPENAI_API_KEY=your_actual_key_here
FLASK_DEBUG=1
```

### 3. Build and Start the Application
Run Docker Compose to build the image and launch the web server:
```bash
docker compose up --build
```

### 4. Access the Application
Open your web browser and navigate to: [http://localhost:8000](http://localhost:8000)

To stop the application, press `Ctrl + C` in your terminal, or run:
```bash
docker compose down
```

### 5. Access the Database
Open your web browser and navigate to: [http://localhost:8080](http://localhost:8080)
---

## Development Workflow & Subsystems

This project is divided into four modular subsystems:

* **User Creation & Management** (`app/subsystems/auth/`)
* **Waste Identification & Classification** (`app/subsystems/classification/`)
* **Educational Chatbot** (`app/subsystems/chatbot/`)
* **Statistical Dashboard** (`app/subsystems/dashboard/`)

---

## Branching Guidelines

* **Do not** commit directly to `main`.
* **Branch naming convention:** `feature/<subsystem>/<feature>` (e.g., `feature/educational/chatbot`).
* Once your task is complete and tested, push your branch and create a Merge Request (MR) on GitLab for review.

## Statistical Dashboard (Hiranmayai Nemani)

The Statistical Dashboard subsystem receives classification results, calculates statistics, and shows them on a web dashboard: summary cards, a waste-by-category chart, and an activity-over-time chart.

Code: `app/subsystems/dashboard/` · Page: `templates/dashboard/dashboard.html` · URL: http://localhost:8000/dashboard/

| Class | Responsibility |
|---|---|
| `ClassificationRecord` | One classification result: predicted category, actual category, confidence, timestamp. Validates its data in the setters. |
| `MockDataGenerator` | Creates realistic mock records while the classifier is still in development. Configurable count, time range, accuracy, and random seed. |
| `StatisticsAnalyzer` | Calculates total classifications, category distribution, accuracy, average confidence, and daily activity. |
| `DashboardService` | Chooses the data source (mock or live), uses the analyzer, and returns the data in the format the dashboard needs. |

Every class has a constructor (`__init__`), initialization methods (`from_dict`, `initialize_random`, `configure`, `load_records`, `initialize`), and getters/setters for its private attributes.

`routes.py` connects the subsystem to the web app: `/dashboard/` shows the page and `/dashboard/api/stats` returns the statistics as JSON.

```mermaid
classDiagram
    direction LR
    class ClassificationRecord {
        -int _record_id
        -str _predicted_category
        -str _actual_category
        -float _confidence
        -datetime _timestamp
        +#95;#95;init#95;#95;(record_id, predicted_category, confidence, timestamp, actual_category)
        +from_dict(data)$ ClassificationRecord
        +to_dict() dict
        +has_ground_truth() bool
        +is_correct() bool
        +get_predicted_category() / set_predicted_category()
        +get_actual_category() / set_actual_category()
        +get_confidence() / set_confidence()
        +get_timestamp() / set_timestamp()
        +get_record_id() / set_record_id()
    }
    class MockDataGenerator {
        -list _categories
        -list _weights
        -int _record_count
        -int _days
        -float _accuracy
        -Random _rng
        +#95;#95;init#95;#95;(categories, weights, record_count, days, accuracy, seed)
        +initialize_random(seed)
        +configure(record_count, days, accuracy)
        +generate() list~ClassificationRecord~
        +get_categories() / set_categories()
        +get_record_count() / set_record_count()
        +get_days() / set_days()
        +get_accuracy() / set_accuracy()
    }
    class StatisticsAnalyzer {
        -list _records
        -list _categories
        +#95;#95;init#95;#95;(records, categories)
        +load_records(records)
        +add_record(record)
        +total_classifications() int
        +category_distribution() dict
        +category_count() int
        +accuracy() float
        +average_confidence() float
        +daily_activity() dict
        +summary() dict
        +get_records() / set_records()
        +get_categories() / set_categories()
    }
    class DashboardService {
        -bool _use_mock_data
        -list _categories
        -callable _record_provider
        -MockDataGenerator _generator
        -StatisticsAnalyzer _analyzer
        +#95;#95;init#95;#95;(use_mock_data, categories, record_provider)
        +initialize(seed)
        +refresh()
        +get_dashboard_data() dict
        +get_use_mock_data() / set_use_mock_data()
        +get_categories() / set_categories()
        +get_record_provider() / set_record_provider()
    }
    DashboardService *-- MockDataGenerator : uses in mock mode
    DashboardService *-- StatisticsAnalyzer : uses
    MockDataGenerator ..> ClassificationRecord : creates
    StatisticsAnalyzer o-- ClassificationRecord : analyses
```

![Statistical Dashboard class diagram](docs/uml/dashboard.png)

Run the tests: `python -m unittest tests.test_dashboard`
