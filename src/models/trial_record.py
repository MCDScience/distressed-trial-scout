from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TrialRecord:
    nct_id: str
    title: str
    sponsor: str
    phase: str
    status: str
    why_stopped: str | None = None
    last_update_post_date: str | None = None
    enrollment_count: int | None = None
    has_results: bool = False
    conditions: list[str] = field(default_factory=list)
    interventions: list[str] = field(default_factory=list)
    intervention_types: list[str] = field(default_factory=list)
    brief_summary: str | None = None
    detailed_description: str | None = None
    primary_outcomes: list[str] = field(default_factory=list)
    secondary_outcomes: list[str] = field(default_factory=list)
    distress_score: float = 0.0
    distress_breakdown: dict[str, float] = field(default_factory=dict)
    ctgov_url: str = ""
    registry_text: str = ""

    @classmethod
    def ctgov_link(cls, nct_id: str) -> str:
        return f"https://clinicaltrials.gov/study/{nct_id}"

    def to_agent_context(self) -> str:
        parts = [
            f"NCT ID: {self.nct_id}",
            f"Title: {self.title}",
            f"Sponsor: {self.sponsor}",
            f"Phase: {self.phase}",
            f"Status: {self.status}",
        ]
        if self.why_stopped:
            parts.append(f"Why stopped: {self.why_stopped}")
        if self.conditions:
            parts.append(f"Conditions: {', '.join(self.conditions)}")
        if self.interventions:
            parts.append(f"Interventions: {', '.join(self.interventions)}")
        if self.intervention_types:
            parts.append(f"Intervention types: {', '.join(self.intervention_types)}")
        if self.brief_summary:
            parts.append(f"Brief summary: {self.brief_summary}")
        if self.detailed_description:
            parts.append(f"Description: {self.detailed_description}")
        if self.primary_outcomes:
            parts.append(f"Primary outcomes: {'; '.join(self.primary_outcomes)}")
        if self.secondary_outcomes:
            parts.append(f"Secondary outcomes: {'; '.join(self.secondary_outcomes)}")
        return chr(10).join(parts)
