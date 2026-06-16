from __future__ import annotations

import json
import os
import re
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task
from dotenv import load_dotenv

from app.config import LLM_MODEL
from src.agents.schemas import TrialResult
from src.agents.tools import fetch_halted_trials
from src.models.trial_record import TrialRecord

load_dotenv()


def _haiku_llm() -> LLM:
    return LLM(
        model=LLM_MODEL,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=4096,
        temperature=0.2,
    )


def _records_to_payload(records: list[TrialRecord]) -> list[dict[str, Any]]:
    return [
        {
            "nct_id": r.nct_id,
            "title": r.title,
            "sponsor": r.sponsor,
            "phase": r.phase,
            "status": r.status,
            "distress_score": r.distress_score,
            "ctgov_url": r.ctgov_url,
            "registry_text": r.registry_text,
        }
        for r in records
    ]


def _parse_trial_results(raw: str, records: list[TrialRecord]) -> list[TrialResult]:
    by_id = {r.nct_id: r for r in records}
    text = raw.strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = []

    results: list[TrialResult] = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            nct = item.get("nct_id") or item.get("nctId")
            if not nct:
                continue
            base = by_id.get(nct)
            results.append(
                TrialResult(
                    nct_id=nct,
                    title=item.get("title") or (base.title if base else ""),
                    sponsor=item.get("sponsor") or (base.sponsor if base else ""),
                    phase=item.get("phase") or (base.phase if base else ""),
                    status=item.get("status") or (base.status if base else ""),
                    distress_score=float(
                        item.get("distress_score") or (base.distress_score if base else 0.0)
                    ),
                    distress_breakdown=dict(
                        item.get("distress_breakdown")
                        or (base.distress_breakdown if base else {})
                    ),
                    biology_summary=item.get("biology_summary")
                    or item.get("biologySummary")
                    or "Per registry: insufficient detail to summarize.",
                    ctgov_url=item.get("ctgov_url")
                    or (base.ctgov_url if base else TrialRecord.ctgov_link(nct)),
                )
            )

    seen = {r.nct_id for r in results}
    for record in records:
        if record.nct_id not in seen:
            results.append(
                TrialResult(
                    nct_id=record.nct_id,
                    title=record.title,
                    sponsor=record.sponsor,
                    phase=record.phase,
                    status=record.status,
                    distress_score=record.distress_score,
                    distress_breakdown=dict(record.distress_breakdown),
                    biology_summary="Per registry: summary unavailable.",
                    ctgov_url=record.ctgov_url,
                )
            )
    results.sort(key=lambda r: r.distress_score, reverse=True)
    return results


def summarize_trials(records: list[TrialRecord], condition: str) -> list[TrialResult]:
    """Generate biology/biomarker summaries for pre-scored trials (Streamlit step 4)."""
    if not records:
        return []

    payload = _records_to_payload(records)
    scout = Agent(
        role="Trial Scout",
        goal="Identify halted trials with interesting biology in a therapeutic area",
        backstory=(
            "Expert in clinical trial registry data and drug mechanism analysis. "
            "Only cite facts present in registry text; prefix summaries with 'Per registry:'."
        ),
        llm=_haiku_llm(),
        tools=[],
        verbose=False,
    )

    task = Task(
        description=(
            f"Therapeutic area: {condition}\n\n"
            "For each trial in the JSON below, write a concise 2-3 sentence biology/biomarker summary "
            "covering target/MOA, intervention type, biomarkers mentioned in the registry text, and any "
            "posted efficacy signals. Do not invent biomarkers. Prefix each summary with 'Per registry:'.\n\n"
            f"Trials JSON:\n{json.dumps(payload, indent=2)}\n\n"
            "Return ONLY a JSON array of objects with keys: "
            "nct_id, title, sponsor, phase, status, distress_score, biology_summary, ctgov_url."
        ),
        expected_output="JSON array of TrialResult objects, one per trial.",
        agent=scout,
    )

    crew = Crew(agents=[scout], tasks=[task], process=Process.sequential, verbose=False)
    output = crew.kickoff()
    raw = str(output)
    return _parse_trial_results(raw, records)


def run_scout_crew(condition: str, max_count: int) -> list[TrialResult]:
    """Full agent flow: fetch via tool, then summarize (CLI / alternative entry)."""
    scout = Agent(
        role="Trial Scout",
        goal="Identify halted trials with interesting biology in a therapeutic area",
        backstory="Expert in clinical trial registry data and drug mechanism analysis.",
        llm=_haiku_llm(),
        tools=[fetch_halted_trials],
        verbose=False,
    )

    task = Task(
        description=(
            f"Given condition '{condition}' and max_count {max_count}, call fetch_halted_trials, "
            "then for each returned trial write a 2-3 sentence biology/biomarker summary grounded in "
            "registry_text. Return ONLY a JSON array with nct_id, title, sponsor, phase, status, "
            "distress_score, biology_summary, ctgov_url."
        ),
        expected_output="JSON array of trial summaries.",
        agent=scout,
    )

    crew = Crew(agents=[scout], tasks=[task], process=Process.sequential, verbose=False)
    output = str(crew.kickoff())
    # Best-effort parse without base records
    try:
        match = re.search(r"\[.*\]", output, re.DOTALL)
        data = json.loads(match.group(0) if match else output)
        if isinstance(data, list):
            return [TrialResult.model_validate(item) for item in data]
    except Exception:
        pass
    return []
