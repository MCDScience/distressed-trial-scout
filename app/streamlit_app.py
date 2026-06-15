from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from app.config import DEFAULT_TRIAL_COUNT, MAX_TRIAL_COUNT
from src.agents.scout import summarize_trials
from src.agents.schemas import TrialResult
from src.pipeline.scan import run_scan

load_dotenv(ROOT / ".env")

st.set_page_config(page_title="Distressed Trial Scout", layout="wide")
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

with st.sidebar:
    st.header("Scan inputs")
    condition = st.text_input(
        "Therapeutic area / condition",
        value=st.session_state.last_condition,
        placeholder="e.g. idiopathic pulmonary fibrosis",
    )
    trial_count = st.number_input(
        "Number of trials to fetch",
        min_value=1,
        max_value=MAX_TRIAL_COUNT,
        value=int(st.session_state.last_count),
        step=1,
    )
    run_scan_btn = st.button("Run Scan", type="primary", use_container_width=True)

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
            st.info(f"In progress: {label}")
        else:
            st.write(f"Pending: {label}")


def results_to_dataframe(results: list[TrialResult]) -> pd.DataFrame:
    rows = []
    for r in results:
        rows.append(
            {
                "NCT ID": r.ctgov_url,
                "Title": r.title,
                "Sponsor": r.sponsor,
                "Phase": r.phase,
                "Status": r.status,
                "Distress score": r.distress_score,
                "Biology summary": r.biology_summary,
                "CT.gov URL": r.ctgov_url,
            }
        )
    return pd.DataFrame(rows)


if run_scan_btn:
    if not condition or not condition.strip():
        st.error("Enter a therapeutic area or condition.")
    elif not __import__("os").getenv("ANTHROPIC_API_KEY"):
        st.error("Set ANTHROPIC_API_KEY in .env (see .env.example).")
    else:
        st.session_state.last_condition = condition.strip()
        st.session_state.last_count = int(trial_count)
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
        with progress_box.container():
            for label in step_labels:
                st.success(f"Done: {label}")
        status_box.caption("Scan complete.")

if st.session_state.scan_results:
    meta = st.session_state.scan_results["meta"]
    results: list[TrialResult] = st.session_state.scan_results["results"]

    st.divider()
    st.subheader("Results")
    st.write(
        f"Fetched **{meta['fetched_count']}** trials; excluded **{meta['excluded_safety_count']}** "
        f"safety-related stops; showing **{len(results)}** scored trials."
    )

    if not results:
        st.warning("No trials matched after filtering. Try another condition or increase the count.")
    else:
        df = results_to_dataframe(results)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "NCT ID": st.column_config.LinkColumn(
                    "NCT ID",
                    display_text=r"https://clinicaltrials\.gov/study/(.*)",
                    help="Open study on ClinicalTrials.gov",
                ),
                "CT.gov URL": st.column_config.LinkColumn("CT.gov URL"),
                "Distress score": st.column_config.NumberColumn(
                    "Distress score", format="%.1f"
                ),
            },
        )

