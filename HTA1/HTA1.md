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
* *Implemented:* Germany (`rules.json`). The rules file is per country, so adding a second country is a configuration change, not a code change.
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

## Statistical Dashboard (Srivaishnavi Jakku)

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

![Statistical Dashboard class diagram](../docs/uml/dashboard.png)

Run the tests: `docker compose exec web python -m pytest app/subsystems/dashboard/tests`

### Video

Video presentation: [Video HTA1](https://fhdoprod-my.sharepoint.com/:v:/r/personal/bhavisha_ah-moo001_stud_fh-dortmund_de/Documents/MDTSem1/CPC/Capstone/HomeTaskAssignment%20Videos/Group3_HomeTaskAssignment1.mp4?d=wd3aec5dd936c4e9a9eceb3ea7e8f70a9&csf=1&web=1&nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=zaWQr1) (access only with an FH-Dortmund account)
