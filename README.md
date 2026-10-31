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

The Statistical Dashboard reads the classification results stored by the classification subsystem (the `scans` table), calculates statistics, and shows them on a web dashboard: summary cards (items classified, Pfand items, materials detected), an items-by-bin chart, and an activity-over-time chart. Each refresh is stored in the database as a snapshot.

Models: `app/models/dashboard.py` · Logic: `app/subsystems/dashboard/services.py` · Routes: `app/subsystems/dashboard/routes.py` · Page: `templates/dashboard/dashboard.html` · URL: http://localhost:8000/dashboard/

| Class (table) | Responsibility |
|---|---|
| `DashboardSetting` (`dashboard_settings`) | Where the dashboard gets its data: mock data or live scans, and how many days back. |
| `DashboardSnapshot` (`dashboard_snapshots`) | The statistics at one point in time: total items, Pfand items, number of materials. Built from scans with `from_scans()`. |
| `BinStatistic` (`bin_statistics`) | Items per bin type (e.g. Gelbe Tonne) in a snapshot, for the doughnut chart. |
| `DailyActivity` (`daily_activity`) | Items per day in a snapshot, for the line chart. |

All four are SQLAlchemy models (`db.Model` with `db.Column`), so `db.create_all()` creates their tables. Each has a constructor (`__init__`), initialization methods (`get_or_create`, `from_scans`, `add_bin_statistic`, `add_daily_activity`), and getters/setters that validate values before they are saved. A snapshot owns its `BinStatistic` and `DailyActivity` rows (one-to-many, deleted together).

Until the classifier has produced real scans, the dashboard uses mock scans generated with the classification subsystem's own bin rules (`rules.json`). Switch to live data with `POST /dashboard/api/settings` and `{"use_mock_data": false}`.

```mermaid
classDiagram
    direction LR
    class Scan {
        <<classification subsystem>>
        +id: int
        +timestamp: str
        +item_name: str
        +material: str
        +bin_type: str
        +is_pfand: bool
    }
    class DashboardSetting {
        <<db.Model: dashboard_settings>>
        +id: int
        -_use_mock_data: bool
        -_time_range_days: int
        -_updated_at: datetime
        +#95;#95;init#95;#95;(use_mock_data, time_range_days)
        +get_or_create()$ DashboardSetting
        +to_dict() dict
        +get_use_mock_data() / set_use_mock_data()
        +get_time_range_days() / set_time_range_days()
        +get_updated_at() datetime
    }
    class DashboardSnapshot {
        <<db.Model: dashboard_snapshots>>
        +id: int
        -_created_at: datetime
        -_source: str
        -_total_items: int
        -_pfand_items: int
        -_material_count: int
        +#95;#95;init#95;#95;(source, total_items, pfand_items, material_count)
        +from_scans(scans, source)$ DashboardSnapshot
        +add_bin_statistic(statistic)
        +add_daily_activity(activity)
        +pfand_share() float
        +to_dict() dict
        +get_source() / set_source()
        +get_total_items() / set_total_items()
        +get_pfand_items() / set_pfand_items()
        +get_material_count() / set_material_count()
        +get_created_at() datetime
    }
    class BinStatistic {
        <<db.Model: bin_statistics>>
        +id: int
        +snapshot_id: int FK
        -_bin_type: str
        -_item_count: int
        +#95;#95;init#95;#95;(bin_type, item_count)
        +share_of(total_items) float
        +get_bin_type() / set_bin_type()
        +get_item_count() / set_item_count()
        +get_snapshot() DashboardSnapshot
    }
    class DailyActivity {
        <<db.Model: daily_activity>>
        +id: int
        +snapshot_id: int FK
        -_activity_date: date
        -_item_count: int
        +#95;#95;init#95;#95;(activity_date, item_count)
        +get_activity_date() / set_activity_date()
        +get_item_count() / set_item_count()
        +get_snapshot() DashboardSnapshot
    }
    DashboardSnapshot "1" *-- "*" BinStatistic : has
    DashboardSnapshot "1" *-- "*" DailyActivity : has
    DashboardSnapshot ..> Scan : calculated from
    DashboardSnapshot ..> DashboardSetting : built using
```

![Statistical Dashboard class diagram](docs/uml/dashboard.png)

Run the tests: `docker compose exec web pytest app/subsystems/dashboard/tests`
