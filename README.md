
# AI Workflow Engine — FastAPI Implementation
*A Minimal Graph-Based Workflow Executor With Branching, Looping, and Rule-Based Summarization*

This project is my implementation of the AI Engineering Internship Assignment for Tredence Inc..
It includes:

* A minimal **workflow engine** supporting node-based execution
* **Graph definition** with edges and conditional edges
* **Branching** and **looping** logic driven by shared state
* A complete **rule-based summarization workflow (Option B)**
* A clean **FastAPI backend** exposing endpoints to create and execute graphs

No machine learning or external APIs are used.
All summarization logic is deterministic and rule-based.

---

## Features

### ✔ Workflow Engine

* Define graphs dynamically using `/graph/create`
* Execute workflows via `/graph/run`
* Retrieve run state via `/graph/state/{run_id}`
* Supports:

  * Linear execution
  * Conditional branching
  * Looping until conditions are satisfied
  * Shared state passed through nodes

### ✔ Rule-Based Summarization Workflow (Option B)

Implements a complete summarization pipeline using deterministic rules:

* `decide_pipeline` — choose short or long workflow
* `single_pass_summary` — quick summary for short text
* `split_text` — chunk long text
* `generate_summaries` — per-chunk extractive summaries
* `merge_summaries` — join partial summaries
* `refine_summary` — iterative trimming
* `check_length` — loop until summary length ≤ target

---

## Project Structure

```
ai-workflow-engine/
├── app/
│   ├── main.py
│   ├── engine.py
│   ├── models.py
│   ├── registry.py
│   └── workflows/
│        └── summarization.py
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Installation & Setup

### 1. Clone the repository

```
git clone https://github.com/Theo64-dev/ai-workflow-engine.git
cd ai-workflow-engine
```

### 2. Create virtual environment

```
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Launch server

```
uvicorn app.main:app --reload
```

Open Swagger UI:

```
http://127.0.0.1:8000/docs
```

---

## Graph Concept

A graph is defined by:

* `nodes`: names of registered node functions
* `entry_node`: where execution begins
* `edges`: normal transitions
* `conditional_edges`: branching loops based on state values
* `state`: a shared dictionary modified by each node

Nodes do not decide which node comes next—
they only write signals into `state`.
The engine reads `conditional_edges` to choose next nodes.

---

## Example: Create Summarization Workflow Graph

POST `/graph/create`:

```
{
  "name": "summarization_workflow",
  "entry_node": "decide_pipeline",
  "nodes": [
    "decide_pipeline",
    "single_pass_summary",
    "split_text",
    "generate_summaries",
    "merge_summaries",
    "refine_summary",
    "check_length"
  ],
  "edges": {
    "single_pass_summary": "refine_summary",
    "split_text": "generate_summaries",
    "generate_summaries": "merge_summaries",
    "merge_summaries": "refine_summary",
    "refine_summary": "check_length"
  },
  "conditional_edges": {
    "decide_pipeline": {
      "short": "single_pass_summary",
      "long": "split_text"
    },
    "check_length": {
      "true": "refine_summary",
      "false": null
    }
  }
}
```

---

## Example: Run the Workflow

POST `/graph/run`:

```
{
  "graph_id": "graph_xxx",
  "initial_state": {
    "original_text": "Climate change is one of the biggest challenges of the 21st century...",
    "chunk_size": 80,
    "chunk_summary_words": 40,
    "max_length": 50,
    "refine_factor": 0.6,
    "short_threshold": 100
  }
}
```

The response includes:

* `run_id`
* `final_state`
* `execution_log`
* `status`

---

## Looping Behavior

The loop is driven by:

* `refine_summary` — trims summary length
* `check_length` — sets `state["check_length"] = True/False`

As long as `check_length == true`, the engine follows:

```
refine_summary → check_length → refine_summary → ...
```

Loop ends when:

```
len(final_summary_words) <= max_length
```

---

## Branching Behavior

At the start:

```
decide_pipeline:
    if word_count <= short_threshold → "short"
    else → "long"
```

Engine uses:

```
conditional_edges["decide_pipeline"][state["decide_pipeline"]]
```

to choose the next node.

---

## Test Cases

* Short text → single-pass path
* Medium text → long pipeline once
* Long text → multi-chunk + multiple loops
* Empty input → valid baseline
* Stress test with tiny chunks → performance check
* Invalid graph definitions → engine validation errors

---

## Design Choices

* Deterministic rule-based summarization
* Lightweight registry system
* In-memory graph & run store
* Clear separation of:

  * Node execution
  * Graph control flow
  * API interface
* Convergence guaranteed via `refine_factor`
* Loop protection using `max_iterations`

---

## Future Improvements

* Persist graphs/runs in a database
* Add async/queued execution
* Visualize graphs in UI
* Add WebSockets for live logs
* Support parallel branches
* Expand test coverage

---
 