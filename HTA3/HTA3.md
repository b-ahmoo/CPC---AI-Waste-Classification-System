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
