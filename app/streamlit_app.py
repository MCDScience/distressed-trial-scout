from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from dotenv import load_dotenv

from app.config import DEFAULT_TRIAL_COUNT, DISTRESS_WEIGHTS, MAX_TRIAL_COUNT
from src.agents.scout import summarize_trials
from src.agents.schemas import TrialResult
from src.pipeline.scan import run_scan

load_dotenv(ROOT / ".env")

st.set_page_config(page_title="Distressed Trial Scout", layout="wide")

# Hide "Press Enter to apply" on sidebar inputs (backup for older Streamlit versions).
st.markdown(
    """
<style>
[data-testid="stSidebar"] [data-testid="InputInstructions"] {
    display: none;
}

.pipeline-spinner {
    width: 1.25rem;
    height: 1.25rem;
    margin-top: 0.35rem;
    border: 2px solid rgba(49, 51, 63, 0.15);
    border-top-color: rgb(28, 131, 225);
    border-radius: 50%;
    animation: pipeline-spin 0.75s linear infinite;
    flex-shrink: 0;
}

@keyframes pipeline-spin {
    to {
        transform: rotate(360deg);
    }
}

.trial-card-shell {
    background-color: #171C26;
    border: 1px solid #2a3140;
    border-radius: 0.65rem;
    padding: 1rem 1.1rem;
    margin-bottom: 0.85rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
    overflow: visible;
}

.trial-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    overflow: visible;
}

.trial-card-title {
    font-size: 1.2rem;
    font-weight: 700;
    line-height: 1.4;
    margin: 0 0 0.35rem 0;
    color: #ffffff;
}

.trial-card-subtitle {
    font-size: 0.92rem;
    font-weight: 500;
    line-height: 1.35;
    color: #a8b0bc;
    margin: 0;
}

.distress-score-wrap {
    position: relative;
    flex-shrink: 0;
    display: inline-block;
}

.distress-score-box {
    display: inline-block;
    min-width: 3.25rem;
    padding: 0.45rem 0.65rem;
    border-radius: 0.5rem;
    background: rgba(28, 131, 225, 0.12);
    border: 1px solid rgba(28, 131, 225, 0.35);
    color: rgb(28, 131, 225);
    font-size: 1.1rem;
    font-weight: 700;
    text-align: center;
    line-height: 1;
    white-space: nowrap;
    cursor: help;
}

.distress-score-tooltip {
    display: block;
    visibility: hidden;
    opacity: 0;
    pointer-events: none;
    position: absolute;
    top: calc(100% + 0.55rem);
    right: 0;
    width: min(19rem, 78vw);
    padding: 0.75rem 0.85rem;
    border-radius: 0.55rem;
    background: #0f1419;
    border: 1px solid #2a3140;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
    z-index: 20;
    text-align: left;
    transition: opacity 0.15s ease, visibility 0.15s ease;
}

.distress-score-wrap:hover .distress-score-tooltip,
.distress-score-wrap:focus-within .distress-score-tooltip {
    visibility: visible;
    opacity: 1;
}

.distress-score-tooltip-title {
    color: #ffffff;
    font-size: 0.88rem;
    font-weight: 700;
    margin: 0 0 0.4rem 0;
}

.distress-score-tooltip-summary {
    color: #a8b0bc;
    font-size: 0.76rem;
    line-height: 1.45;
    margin: 0 0 0.65rem 0;
}

.distress-score-tooltip-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.74rem;
}

.distress-score-tooltip-table th {
    color: #94a3b8;
    font-weight: 600;
    text-align: left;
    padding: 0 0 0.35rem 0;
    border-bottom: 1px solid #2a3140;
}

.distress-score-tooltip-table th:last-child {
    text-align: right;
}

.distress-score-tooltip-table td {
    color: #cbd5e1;
    padding: 0.32rem 0 0;
    vertical-align: top;
}

.distress-score-tooltip-table td:last-child {
    text-align: right;
    white-space: nowrap;
    padding-left: 0.75rem;
}

.distress-score-tooltip-table tr.distress-signal-active td {
    color: #ffffff;
    font-weight: 600;
}

.distress-score-tooltip-table tr.distress-signal-active td:last-child {
    color: #60a5fa;
}

.trial-tag-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 0.75rem 0 0.5rem 0;
}

.status-tag {
    display: inline-block;
    padding: 0.28rem 0.75rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.01em;
}

.tag-phase-early1 {
    background: rgba(186, 230, 253, 0.18);
    color: #bae6fd;
}

.tag-phase-1 {
    background: rgba(147, 197, 253, 0.18);
    color: #93c5fd;
}

.tag-phase-1-2 {
    background: rgba(125, 186, 252, 0.18);
    color: #7dbafc;
}

.tag-phase-2 {
    background: rgba(96, 165, 250, 0.18);
    color: #60a5fa;
}

.tag-phase-2-3 {
    background: rgba(59, 130, 246, 0.2);
    color: #3b82f6;
}

.tag-phase-3 {
    background: rgba(37, 99, 235, 0.22);
    color: #93c5fd;
}

.tag-phase-3-4 {
    background: rgba(29, 78, 216, 0.24);
    color: #7dbafc;
}

.tag-phase-4 {
    background: rgba(30, 64, 175, 0.28);
    color: #bfdbfe;
}

.tag-phase-na {
    background: rgba(107, 114, 128, 0.15);
    color: rgb(148, 163, 184);
}

.tag-status-halted {
    background: rgba(239, 68, 68, 0.15);
    color: #fca5a5;
}

.tag-status-stale {
    background: rgba(245, 158, 11, 0.18);
    color: #fcd34d;
}

.tag-status-default {
    background: rgba(107, 114, 128, 0.15);
    color: #94a3b8;
}

.trial-card-actions {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    column-gap: 1rem;
    align-items: center;
    margin-top: 0.85rem;
    border-top: 1px solid #2a3140;
    padding-top: 0.65rem;
}

.trial-card-details {
    grid-column: 1;
    grid-row: 1 / -1;
    margin: 0;
    border-top: none;
    padding-top: 0;
}

.trial-card-details summary {
    cursor: pointer;
    color: #ffffff;
    font-size: 0.95rem;
    font-weight: 600;
    list-style: none;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
}

.trial-card-details summary::after {
    content: "▼";
    font-size: 0.62rem;
    color: #a8b0bc;
    line-height: 1;
    transition: transform 0.2s ease;
}

.trial-card-details[open] summary::after {
    transform: rotate(180deg);
}

.trial-card-details summary::-webkit-details-marker {
    display: none;
}

.trial-card-details[open] summary {
    margin-bottom: 0.65rem;
}

.trial-card-summary {
    color: #e2e8f0;
    font-size: 0.92rem;
    line-height: 1.55;
    white-space: pre-wrap;
    margin: 0;
    padding: 0.65rem 0.75rem;
    border-radius: 0.45rem;
    background: rgba(0, 0, 0, 0.2);
    border: 1px solid #2a3140;
    max-width: min(100%, 72%);
}

.trial-link {
    grid-column: 2;
    grid-row: 1;
    align-self: center;
    font-size: 0.9rem;
    font-weight: 600;
    color: rgb(28, 131, 225);
    text-decoration: none;
    white-space: nowrap;
}

.trial-link:hover {
    text-decoration: underline;
}
</style>
""",
    unsafe_allow_html=True,
)

st.title("Distressed Trial Scout")
st.caption(
    "Screen ClinicalTrials.gov for distressed or stalled programs (safety stops excluded)."
)

if "scan_results" not in st.session_state:
    st.session_state.scan_results = None
if "pipeline_step" not in st.session_state:
    st.session_state.pipeline_step = 0
if "last_condition" not in st.session_state:
    st.session_state.last_condition = ""
if "last_count" not in st.session_state:
    st.session_state.last_count = DEFAULT_TRIAL_COUNT


def parse_trial_count(raw: str) -> int | None:
    """Parse trial count from text input; return None if invalid."""
    text = raw.strip()
    if not text:
        return None
    try:
        value = int(text)
    except ValueError:
        return None
    if value < 1 or value > MAX_TRIAL_COUNT:
        return None
    return value


with st.sidebar:
    st.header("Scan inputs")
    with st.form("scan_form", enter_to_submit=False, border=False):
        condition = st.text_input(
            "Therapeutic area / condition",
            value=st.session_state.last_condition,
            placeholder="e.g. idiopathic pulmonary fibrosis",
        )
        trial_count_raw = st.text_input(
            "Number of trials to fetch",
            value=str(int(st.session_state.last_count)),
            placeholder=f"1–{MAX_TRIAL_COUNT}",
        )
        run_scan_btn = st.form_submit_button("Run Scan", type="primary", use_container_width=True)

STEPS = [
    ("fetching", "Fetching trials from ClinicalTrials.gov"),
    ("filtering", "Filtering safety-related terminations"),
    ("scoring", "Scoring distress signals"),
    ("analyzing", "Generating biology summaries"),
]

step_labels = [label for _, label in STEPS]


def render_progress(active_index: int) -> None:
    st.subheader("Pipeline progress")
    for idx, label in enumerate(step_labels):
        if idx < active_index:
            st.success(f"Done: {label}")
        elif idx == active_index:
            step_cols = st.columns([12, 1], vertical_alignment="center")
            with step_cols[0]:
                st.info(f"In progress: {label}")
            with step_cols[1]:
                st.markdown(
                    '<div class="pipeline-spinner" role="status" aria-label="Loading"></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.write(f"Pending: {label}")


def render_progress_collapsed() -> None:
    """Compact completed pipeline summary — collapsed by default."""
    with st.expander("Scan Complete", expanded=False):
        st.caption("Fetch → Filter → Score → Analyze")
        for label in step_labels:
            st.markdown(f"✓ {label}")


def _format_phase_label(phase: str) -> str:
    if not phase or phase.upper() in {"NA", "N/A"}:
        return "Phase N/A"
    parts = [p.strip().replace("PHASE", "Phase ") for p in phase.split(",") if p.strip()]
    return ", ".join(parts) if parts else phase


def _normalize_phase_key(phase: str) -> str:
    upper = (phase or "").upper()
    parts = [p.strip().replace(" ", "") for p in upper.split(",") if p.strip()]
    return ",".join(parts) if parts else "NA"


def _phase_tag_class(phase: str) -> str:
    key = _normalize_phase_key(phase)
    if key in {"NA", "N/A", ""}:
        return "tag-phase-na"

    phase_class_by_key = {
        "EARLY_PHASE1": "tag-phase-early1",
        "PHASE1": "tag-phase-1",
        "PHASE1,PHASE2": "tag-phase-1-2",
        "PHASE2": "tag-phase-2",
        "PHASE2,PHASE3": "tag-phase-2-3",
        "PHASE3": "tag-phase-3",
        "PHASE3,PHASE4": "tag-phase-3-4",
        "PHASE4": "tag-phase-4",
    }
    if key in phase_class_by_key:
        return phase_class_by_key[key]

    if "PHASE4" in key:
        return "tag-phase-4"
    if "PHASE3" in key:
        return "tag-phase-3"
    if "PHASE2" in key:
        return "tag-phase-2"
    if "EARLY_PHASE1" in key:
        return "tag-phase-early1"
    if "PHASE1" in key:
        return "tag-phase-1"
    return "tag-phase-na"


def _format_status_label(status: str) -> str:
    return (status or "Unknown").replace("_", " ").title()


def _status_tag_class(status: str) -> str:
    upper = (status or "").upper()
    if upper in {"TERMINATED", "SUSPENDED", "WITHDRAWN"}:
        return "tag-status-halted"
    if upper in {"ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING"}:
        return "tag-status-stale"
    return "tag-status-default"


def _coerce_trial_result(item: TrialResult | dict) -> TrialResult:
    if isinstance(item, TrialResult):
        return item
    return TrialResult.model_validate(item)


DISTRESS_SIGNAL_ROWS: list[tuple[str, str, str]] = [
    (
        "halted_status",
        "Halted status (terminated, suspended, withdrawn)",
        str(DISTRESS_WEIGHTS["halted_status"]),
    ),
    (
        "stale_active",
        "Stale listing (no registry update in 18+ months)",
        str(DISTRESS_WEIGHTS["stale_active"]),
    ),
    (
        "late_stage_stall",
        "Late-stage non-recruiting stall",
        str(DISTRESS_WEIGHTS["late_stage_stall"]),
    ),
    (
        "non_safety_why_stopped",
        "Documented non-safety stop reason",
        str(DISTRESS_WEIGHTS["non_safety_why_stopped"]),
    ),
    (
        "low_enrollment",
        "Low enrollment vs phase norm",
        f"{DISTRESS_WEIGHTS['low_enrollment_min']}–{DISTRESS_WEIGHTS['low_enrollment_max']}",
    ),
    (
        "posted_results",
        "Results posted on registry",
        str(DISTRESS_WEIGHTS["posted_results"]),
    ),
]


def _build_distress_score_tooltip(nct_id: str, breakdown: dict[str, float] | None) -> str:
    signal_rows: list[str] = []
    active_breakdown = breakdown or {}

    for key, label, weight_label in DISTRESS_SIGNAL_ROWS:
        points = active_breakdown.get(key)
        row_class = "distress-signal-active" if points else ""
        weight_cell = f"+{points:.0f}" if points else html.escape(weight_label)
        signal_rows.append(
            f'<tr class="{row_class}">'
            f"<td>{html.escape(label)}</td>"
            f"<td>{weight_cell}</td>"
            f"</tr>"
        )

    safe_nct = html.escape(nct_id)
    return (
        f'<span class="distress-score-tooltip" id="distress-tip-{safe_nct}" role="tooltip">'
        f'<p class="distress-score-tooltip-title">Distress Score</p>'
        f'<p class="distress-score-tooltip-summary">'
        f"A heuristic score (0–100) estimating how distressed or stalled a trial appears "
        f"based on registry status, activity, and enrollment signals. Safety-related stops "
        f"are excluded before scoring."
        f"</p>"
        f'<table class="distress-score-tooltip-table">'
        f"<thead><tr><th>Signal</th><th>Weight</th></tr></thead>"
        f'<tbody>{"".join(signal_rows)}</tbody>'
        f"</table>"
        f"</span>"
    )


def render_trial_card(result: TrialResult) -> None:
    phase_label = _format_phase_label(result.phase)
    status_label = _format_status_label(result.status)
    phase_class = _phase_tag_class(result.phase)
    status_class = _status_tag_class(result.status)

    title = html.escape(result.title)
    sponsor = html.escape(result.sponsor)
    summary = html.escape(result.biology_summary)
    distress_tooltip = _build_distress_score_tooltip(result.nct_id, result.distress_breakdown)
    safe_nct = html.escape(result.nct_id)

    card_html = (
        f'<div class="trial-card-shell">'
        f'<div class="trial-card-header">'
        f"<div>"
        f'<p class="trial-card-title">{title}</p>'
        f'<p class="trial-card-subtitle">{sponsor}</p>'
        f"</div>"
        f'<span class="distress-score-wrap" tabindex="0" aria-describedby="distress-tip-{safe_nct}">'
        f'<span class="distress-score-box">{result.distress_score:.0f}</span>'
        f"{distress_tooltip}"
        f"</span>"
        f"</div>"
        f'<div class="trial-tag-row">'
        f'<span class="status-tag {phase_class}">{html.escape(phase_label)}</span>'
        f'<span class="status-tag {status_class}">{html.escape(status_label)}</span>'
        f"</div>"
        f'<div class="trial-card-actions">'
        f'<details class="trial-card-details">'
        f"<summary>Read Summary</summary>"
        f'<p class="trial-card-summary">{summary}</p>'
        f"</details>"
        f'<a class="trial-link" href="{result.ctgov_url}" target="_blank" rel="noopener noreferrer">'
        f"go to trial &gt;"
        f"</a>"
        f"</div>"
        f"</div>"
    )

    st.markdown(card_html, unsafe_allow_html=True)


def render_results_cards(results: list[TrialResult | dict]) -> None:
    for item in results:
        render_trial_card(_coerce_trial_result(item))


if run_scan_btn:
    if not condition or not condition.strip():
        st.error("Enter a therapeutic area or condition.")
    elif (trial_count := parse_trial_count(trial_count_raw)) is None:
        st.error(f"Enter a whole number between 1 and {MAX_TRIAL_COUNT}.")
    elif not __import__("os").getenv("ANTHROPIC_API_KEY"):
        st.error("Set ANTHROPIC_API_KEY in .env (see .env.example).")
    else:
        st.session_state.last_condition = condition.strip()
        st.session_state.last_count = trial_count
        st.session_state.scan_results = None
        st.session_state.pipeline_step = 0

        progress_box = st.empty()
        status_box = st.empty()

        def on_progress(step: str, message: str) -> None:
            index = next((i for i, (s, _) in enumerate(STEPS) if s == step), 0)
            st.session_state.pipeline_step = index
            with progress_box.container():
                render_progress(index)
            status_box.caption(message)

        with progress_box.container():
            render_progress(0)
        scan_payload = run_scan(
            condition=st.session_state.last_condition,
            max_count=st.session_state.last_count,
            on_progress=on_progress,
        )

        st.session_state.pipeline_step = 3
        with progress_box.container():
            render_progress(3)
        status_box.caption("Generating biology summaries")

        summaries = summarize_trials(scan_payload["trials"], st.session_state.last_condition)
        st.session_state.scan_results = {
            "results": summaries,
            "meta": {
                "fetched_count": scan_payload["fetched_count"],
                "excluded_safety_count": scan_payload["excluded_safety_count"],
                "result_count": scan_payload["result_count"],
            },
        }
        st.session_state.pipeline_step = len(STEPS)
        progress_box.empty()
        status_box.empty()

if st.session_state.scan_results:
    render_progress_collapsed()

    meta = st.session_state.scan_results["meta"]
    results: list[TrialResult] = st.session_state.scan_results["results"]

    st.subheader(f"Results — {st.session_state.last_condition}")
    st.write(
        f"Fetched **{meta['fetched_count']}** trials; excluded **{meta['excluded_safety_count']}** "
        f"safety-related stops; showing **{len(results)}** scored trials."
    )

    if not results:
        st.warning("No trials matched after filtering. Try another condition or increase the count.")
    else:
        render_results_cards(results)

