# Distressed Trial Scout

Local deal-sourcing helper that screens [ClinicalTrials.gov](https://clinicaltrials.gov) for **distressed or stalled** trials in a therapeutic area, excludes **safety-related** stops, scores remaining studies with distress heuristics, and generates short **biology / biomarker** summaries with **Claude Haiku** (CrewAI).

Phase 0 MVP: single Scout agent, no RAG, no SQLite cache.

## Requirements

- Python 3.11+
- `ANTHROPIC_API_KEY` for LLM summaries (CT.gov fetch is free)

## Setup

```bash
cd distressed-trial-scout
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Add your Anthropic API key to `.env`.

## Run

```bash
streamlit run app/streamlit_app.py
```

1. Enter a **condition** (e.g. `idiopathic pulmonary fibrosis`)
2. Choose **trial count** (default 10, max 50)
3. Click **Run Scan**

The UI runs the deterministic pipeline (fetch → safety filter → distress score), then the Scout agent for summaries.

## Project layout

- `app/streamlit_app.py` — Streamlit UI
- `app/config.py` — statuses, safety patterns, distress weights
- `src/api/clinicaltrials_client.py` — CT.gov API v2 client
- `src/pipeline/` — normalize, filter, score, `scan.py` orchestration
- `src/agents/` — CrewAI tool, Scout agent, `TrialResult` schema

## Distress statuses

`TERMINATED`, `SUSPENDED`, `WITHDRAWN`, `ACTIVE_NOT_RECRUITING`, `NOT_YET_RECRUITING`

Trials stopped for efficacy/futility are **kept**; safety-related `whyStopped` text is **excluded**.

## License

Private / local use — adjust as needed.
