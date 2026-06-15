from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from src.api.clinicaltrials_client import ClinicalTrialsClient
from src.models.trial_record import TrialRecord
from src.pipeline.distress_scorer import score_trials
from src.pipeline.filters import is_safety_stop
from src.pipeline.normalize_study import normalize_study

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, str], None]


def _noop_progress(step: str, message: str) -> None:
    return None


def run_scan(
    condition: str,
    max_count: int,
    on_progress: ProgressCallback | None = None,
    client: ClinicalTrialsClient | None = None,
) -> dict[str, Any]:
    """
    Orchestrate fetch, safety filter, and distress scoring.

    Progress steps: fetching, filtering, scoring.
    """
    progress = on_progress or _noop_progress
    api = client or ClinicalTrialsClient()

    progress("fetching", "Fetching trials from ClinicalTrials.gov")
    raw_studies = api.fetch_studies(condition=condition, max_count=max_count)
    normalized: list[TrialRecord] = []
    for raw in raw_studies:
        record = normalize_study(raw)
        if record:
            normalized.append(record)

    progress("filtering", "Filtering safety-related terminations")
    kept: list[TrialRecord] = []
    excluded_safety = 0
    for record in normalized:
        if is_safety_stop(record.why_stopped):
            excluded_safety += 1
            continue
        kept.append(record)

    progress("scoring", "Scoring distress signals")
    scored = score_trials(kept)

    return {
        "trials": scored,
        "fetched_count": len(normalized),
        "excluded_safety_count": excluded_safety,
        "result_count": len(scored),
    }
