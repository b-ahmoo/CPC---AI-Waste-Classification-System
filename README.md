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

## Home Assignment 2: Statistical Dashboard Stream Processing (Srivaishnavi Jakku)

Scenario: **AI-Powered Waste Sorting & Recycling Assistant.** Optical sorters on the conveyor belts send a continuous stream of image-recognition payloads. The dashboard's pipeline filters out low-confidence predictions and tiny noise detections, transforms visual tags and bounding boxes into material categories (PET, HDPE, Aluminium, ...) and conveyor routing codes (e.g. `L1-PET-M`), and aggregates the stream into live dashboard statistics.

Code: `app/subsystems/dashboard/stream.py` · Tests: `app/subsystems/dashboard/tests/test_stream.py`

| OOP concept | Where |
|---|---|
| Abstract Base Classes | `StreamProcessor` (`process`), `EventFilter` (`accepts`), `EventTransformer` (`transform`), all with `@abstractmethod` |
| Inheritance & polymorphism | `ConfidenceFilter`, `BoundingBoxFilter`, `MaterialCategoryTransformer`, `RoutingCodeTransformer`, `DashboardAggregator`: every stage is called through the same `process()` |
| Operator overloading | `__add__`: `ConfidenceFilter() + BoundingBoxFilter() + MaterialCategoryTransformer()` builds a `ProcessingPipeline` |
| Iterators & generators | `SorterEventStream` implements `__iter__`/`__next__`; `ProcessingPipeline.stream()` and `tumbling_windows()` are generators |

```python
pipeline = (ConfidenceFilter(0.75) + BoundingBoxFilter(400)
            + MaterialCategoryTransformer() + RoutingCodeTransformer() + DashboardAggregator())
for window in tumbling_windows(pipeline.stream(SorterEventStream(count=200)), 25):
    ...  # refresh the dashboard once per window
```

### Class diagram

```mermaid
classDiagram
    direction TB
    class StreamProcessor {
        <<abstract>>
        +process(event)* SortingEvent
        +name: str
        +#95;#95;add#95;#95;(other) ProcessingPipeline
    }
    class EventFilter {
        <<abstract>>
        +passed: int
        +dropped: int
        +accepts(event)* bool
        +process(event) SortingEvent
    }
    class EventTransformer {
        <<abstract>>
        +transform(event)* SortingEvent
        +process(event) SortingEvent
    }
    class ConfidenceFilter {
        +min_confidence: float
        +accepts(event) bool
    }
    class BoundingBoxFilter {
        +min_area: int
        +accepts(event) bool
    }
    class MaterialCategoryTransformer {
        +TAG_TO_CATEGORY: dict
        +transform(event) SortingEvent
    }
    class RoutingCodeTransformer {
        +LANES: dict
        +size_class(area) str
        +transform(event) SortingEvent
    }
    class DashboardAggregator {
        +total: int
        +by_category: Counter
        +by_lane: Counter
        +by_belt: Counter
        +process(event) SortingEvent
        +snapshot() dict
        +reset()
    }
    class ProcessingPipeline {
        +stages: list
        +add_stage(stage)
        +process(event) SortingEvent
        +stream(events) generator
        +#95;#95;add#95;#95;(other) ProcessingPipeline
        +#95;#95;len#95;#95;() int
        +#95;#95;iter#95;#95;() iterator
    }
    class SortingEvent {
        +event_id: int
        +belt_id: str
        +visual_tags: list
        +confidence: float
        +bounding_box: tuple
        +timestamp: datetime
        +material_category: str
        +routing_code: str
        +area: int
    }
    class SorterEventStream {
        +count: int
        +belts: list
        +#95;#95;iter#95;#95;() SorterEventStream
        +#95;#95;next#95;#95;() SortingEvent
    }
    StreamProcessor <|-- EventFilter
    StreamProcessor <|-- EventTransformer
    StreamProcessor <|-- DashboardAggregator
    StreamProcessor <|-- ProcessingPipeline
    EventFilter <|-- ConfidenceFilter
    EventFilter <|-- BoundingBoxFilter
    EventTransformer <|-- MaterialCategoryTransformer
    EventTransformer <|-- RoutingCodeTransformer
    ProcessingPipeline o-- "*" StreamProcessor : stages
    SorterEventStream ..> SortingEvent : produces
    StreamProcessor ..> SortingEvent : processes
```

![Dashboard stream processing class diagram](docs/uml/dashboard_stream.png)

Run the demo: `docker compose exec web python app/subsystems/dashboard/stream.py`
Run the tests: `docker compose exec web python -m pytest app/subsystems/dashboard/tests`

### Video

Video presentation: _link to be added_
