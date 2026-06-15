"""Application configuration for Distressed Trial Scout MVP."""

LLM_MODEL = "anthropic/claude-haiku-4-5"

DEFAULT_TRIAL_COUNT = 10
MAX_TRIAL_COUNT = 50

DISTRESSED_STATUSES = [
    "TERMINATED",
    "SUSPENDED",
    "WITHDRAWN",
    "ACTIVE_NOT_RECRUITING",
    "NOT_YET_RECRUITING",
]

STALE_MONTHS = 18

SAFETY_EXCLUDE_PATTERNS = [
    r"safety",
    r"adverse",
    r"toxicity",
    r"tolerability",
    r"dose-limiting",
    r"\bsae\b",
    r"side effect",
    r"harm",
]

DISTRESS_WEIGHTS = {
    "halted_status": 40,
    "stale_active": 25,
    "late_stage_stall": 15,
    "non_safety_why_stopped": 10,
    "low_enrollment_min": 5,
    "low_enrollment_max": 10,
    "posted_results": 5,
}

HALTED_STATUSES = {"TERMINATED", "SUSPENDED", "WITHDRAWN"}
STALE_ACTIVE_STATUSES = {"ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING"}
NON_RECRUITING_STATUSES = HALTED_STATUSES | STALE_ACTIVE_STATUSES
LATE_PHASES = {"PHASE2", "PHASE3"}

CTGOV_API_BASE = "https://clinicaltrials.gov/api/v2/studies"
CTGOV_STUDY_URL_TEMPLATE = "https://clinicaltrials.gov/study/{nct_id}"
API_THROTTLE_SECONDS = 1.0
API_PAGE_SIZE_MAX = 100

CTGOV_FIELDS = [
    "NCTId",
    "BriefTitle",
    "OverallStatus",
    "Phase",
    "LeadSponsorName",
    "WhyStopped",
    "LastUpdatePostDate",
    "EnrollmentCount",
    "HasResults",
    "Condition",
    "InterventionName",
    "InterventionType",
    "BriefSummary",
    "DetailedDescription",
    "PrimaryOutcomeMeasure",
    "SecondaryOutcomeMeasure",
]

PHASE_ENROLLMENT_NORMS = {
    "PHASE1": 30,
    "PHASE2": 100,
    "PHASE3": 300,
    "PHASE4": 500,
}
