from __future__ import annotations

from pydantic import BaseModel, Field


class TrialResult(BaseModel):
    nct_id: str
    title: str
    sponsor: str
    phase: str
    status: str
    distress_score: float
    biology_summary: str = Field(
        description="2-3 sentence biology/biomarker summary grounded in registry text"
    )
    ctgov_url: str
