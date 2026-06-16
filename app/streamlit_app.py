from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from dotenv import load_dotenv

from app.config import DEFAULT_TRIAL_COUNT, MAX_TRIAL_COUNT
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

.trial-card {
    margin-bottom: 1rem;
}

.trial-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
}

.trial-card-title {
    font-size: 1.15rem;
    font-weight: 600;
    line-height: 1.35;
    margin: 0 0 0.25rem 0;
    color: inherit;
}

.trial-card-subtitle {
    font-size: 0.9rem;
    color: rgba(49, 51, 63, 0.65);
    margin: 0;
}

.distress-score-box {
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

.tag-phase {
    background: rgba(59, 130, 246, 0.15);
    color: rgb(29, 78, 216);
}

.tag-phase-early {
    background: rgba(16, 185, 129, 0.15);
    color: rgb(4, 120, 87);
}

.tag-phase-late {
    background: rgba(99, 102, 241, 0.15);
    color: rgb(67, 56, 202);
}

.tag-phase-na {
    background: rgba(107, 114, 128, 0.15);
    color: rgb(75, 85, 99);
}

.tag-status-halted {
    background: rgba(239, 68, 68, 0.15);
    color: rgb(185, 28, 28);
}

.tag-status-stale {
    background: rgba(245, 158, 11, 0.18);
    color: rgb(180, 83, 9);
}

.tag-status-default {
    background: rgba(107, 114, 128, 0.15);
    color: rgb(55, 65, 81);
}

.trial-card-footer {
    display: flex;
    justify-content: flex-end;
    margin-top: 0.5rem;
}

.trial-link {
    font-size: 0.9rem;
    font-weight: 600;
    color: rgb(28, 131, 225);
    text-decoration: none;
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


def _phase_tag_class(phase: str) -> str:
    upper = (phase or "").upper()
    if not upper or upper in {"NA", "N/A"}:
        return "tag-phase-na"
    if any(p in upper for p in ("PHASE1", "EARLY_PHASE1")):
        return "tag-phase-early"
    if any(p in upper for p in ("PHASE3", "PHASE4")):
        return "tag-phase-late"
    return "tag-phase"


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


def render_trial_card(result: TrialResult) -> None:
    phase_label = _format_phase_label(result.phase)
    status_label = _format_status_label(result.status)
    phase_class = _phase_tag_class(result.phase)
    status_class = _status_tag_class(result.status)

    title = html.escape(result.title)
    sponsor = html.escape(result.sponsor)

    with st.container(border=True):
        st.markdown(
            f"""
<div class="trial-card">
  <div class="trial-card-header">
    <div>
      <p class="trial-card-title">{title}</p>
      <p class="trial-card-subtitle">{sponsor}</p>
    </div>
    <div class="distress-score-box">{result.distress_score:.0f}</div>
  </div>
  <div class="trial-tag-row">
    <span class="status-tag {phase_class}">{html.escape(phase_label)}</span>
    <span class="status-tag {status_class}">{html.escape(status_label)}</span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        with st.expander("Read Summary"):
            st.text_area(
                "Analysis summary",
                value=result.biology_summary,
                height=160,
                disabled=True,
                label_visibility="collapsed",
            )

        st.markdown(
            f"""
<div class="trial-card-footer">
  <a class="trial-link" href="{result.ctgov_url}" target="_blank" rel="noopener noreferrer">
    go to trial &gt;
  </a>
</div>
""",
            unsafe_allow_html=True,
        )


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

