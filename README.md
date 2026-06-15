# Distressed Trial Scout

Local deal-sourcing helper that screens [ClinicalTrials.gov](https://clinicaltrials.gov) for **distressed or stalled** trials in a therapeutic area, excludes **safety-related** stops, scores remaining studies with distress heuristics, and generates short **biology / biomarker** summaries with **Claude Haiku** (CrewAI).

## Requirements

- Python 3.11+
- `ANTHROPIC_API_KEY` for LLM summaries (CT.gov fetch is free)

## Project layout

- `app/streamlit_app.py` — Streamlit UI
- `app/config.py` — statuses, safety patterns, distress weights
- `src/api/clinicaltrials_client.py` — CT.gov API v2 client
- `src/pipeline/` — normalize, filter, score, `scan.py` orchestration
- `src/agents/` — CrewAI tool, Scout agent, `TrialResult` schema

## Distress statuses

`TERMINATED`, `SUSPENDED`, `WITHDRAWN`, `ACTIVE_NOT_RECRUITING`, `NOT_YET_RECRUITING`

Trials stopped for efficacy/futility are **kept**; safety-related `whyStopped` text is **excluded**.
