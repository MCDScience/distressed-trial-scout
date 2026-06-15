from __future__ import annotations

from datetime import date, datetime

from app.config import (
    DISTRESS_WEIGHTS,
    HALTED_STATUSES,
    LATE_PHASES,
    NON_RECRUITING_STATUSES,
    PHASE_ENROLLMENT_NORMS,
    STALE_ACTIVE_STATUSES,
    STALE_MONTHS,
)
from src.models.trial_record import TrialRecord
from src.pipeline.filters import is_safety_stop


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    for fmt, length in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try:
            return datetime.strptime(text[:length], fmt).date()
        except ValueError:
            continue
    # ISO prefix fallback
    try:
        return datetime.fromisoformat(text[:10]).date()
    except ValueError:
        return None


def _months_between(older: date, newer: date) -> int:
    return (newer.year - older.year) * 12 + (newer.month - older.month)


def _is_stale(last_update: str | None, today: date | None = None) -> bool:
    parsed = _parse_date(last_update)
    if not parsed:
        return False
    ref = today or date.today()
    return _months_between(parsed, ref) > STALE_MONTHS


def _primary_phase(phase: str) -> str | None:
    if not phase:
        return None
    upper = phase.upper()
    for token in ("PHASE4", "PHASE3", "PHASE2", "PHASE1"):
        if token in upper.replace(" ", ""):
            return token
    return None


def _low_enrollment_points(phase: str, enrollment: int | None) -> float:
    if enrollment is None:
        return 0.0
    key = _primary_phase(phase)
    if not key:
        return 0.0
    norm = PHASE_ENROLLMENT_NORMS.get(key)
    if not norm:
        return 0.0
    ratio = enrollment / norm
    w_min = DISTRESS_WEIGHTS["low_enrollment_min"]
    w_max = DISTRESS_WEIGHTS["low_enrollment_max"]
    if ratio <= 0.25:
        return float(w_max)
    if ratio <= 0.5:
        return float(w_min + (w_max - w_min) / 2)
    if ratio < 1.0:
        return float(w_min)
    return 0.0


def score_trial(record: TrialRecord) -> TrialRecord:
    """Apply full distress heuristics and attach score + breakdown to the record."""
    breakdown: dict[str, float] = {}
    status = (record.status or "").upper()

    if status in HALTED_STATUSES:
        breakdown["halted_status"] = float(DISTRESS_WEIGHTS["halted_status"])

    if status in STALE_ACTIVE_STATUSES and _is_stale(record.last_update_post_date):
        breakdown["stale_active"] = float(DISTRESS_WEIGHTS["stale_active"])

    phase_tokens = (record.phase or "").upper().replace(" ", "")
    if any(p in phase_tokens for p in LATE_PHASES) and status in NON_RECRUITING_STATUSES:
        breakdown["late_stage_stall"] = float(DISTRESS_WEIGHTS["late_stage_stall"])

    if record.why_stopped and record.why_stopped.strip() and not is_safety_stop(record.why_stopped):
        breakdown["non_safety_why_stopped"] = float(DISTRESS_WEIGHTS["non_safety_why_stopped"])

    enroll_pts = _low_enrollment_points(record.phase, record.enrollment_count)
    if enroll_pts:
        breakdown["low_enrollment"] = enroll_pts

    if record.has_results:
        breakdown["posted_results"] = float(DISTRESS_WEIGHTS["posted_results"])

    record.distress_breakdown = breakdown
    record.distress_score = min(100.0, sum(breakdown.values()))
    return record


def score_trials(records: list[TrialRecord]) -> list[TrialRecord]:
    scored = [score_trial(r) for r in records]
    scored.sort(key=lambda r: r.distress_score, reverse=True)
    return scored
