from __future__ import annotations

import json
from typing import Any

from crewai.tools import tool

from src.pipeline.scan import run_scan


@tool("fetch_halted_trials")
def fetch_halted_trials(condition: str, max_count: int = 10) -> str:
    """Fetch halted and stale-active trials for a therapeutic area from ClinicalTrials.gov.

    Applies safety-only filtering and distress scoring. Returns JSON list of trials.
    """
    result = run_scan(condition=condition, max_count=int(max_count))
    trials = result["trials"]
    payload: list[dict[str, Any]] = []
    for t in trials:
        payload.append(
            {
                "nct_id": t.nct_id,
                "title": t.title,
                "sponsor": t.sponsor,
                "phase": t.phase,
                "status": t.status,
                "why_stopped": t.why_stopped,
                "distress_score": t.distress_score,
                "distress_breakdown": t.distress_breakdown,
                "ctgov_url": t.ctgov_url,
                "registry_text": t.registry_text,
            }
        )
    meta = {
        "fetched_count": result["fetched_count"],
        "excluded_safety_count": result["excluded_safety_count"],
        "result_count": result["result_count"],
        "trials": payload,
    }
    return json.dumps(meta, indent=2)
