from __future__ import annotations

from typing import Any

from src.models.trial_record import TrialRecord


def _get_study_payload(study: dict[str, Any]) -> dict[str, Any]:
    if "protocolSection" in study:
        return study
    return {"protocolSection": study.get("protocolSection", study)}


def _module(section: dict[str, Any], key: str) -> dict[str, Any]:
    return section.get(key) or {}


def _first_or_join(values: list[str] | None, sep: str = ", ") -> str:
    if not values:
        return ""
    return sep.join(v for v in values if v)


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _date_string(date_struct: dict[str, Any] | None) -> str | None:
    if not date_struct:
        return None
    if isinstance(date_struct, str):
        return date_struct
    for key in ("date", "value"):
        if date_struct.get(key):
            return str(date_struct[key])
    parts = []
    for key in ("year", "month", "day"):
        if date_struct.get(key) is not None:
            parts.append(str(date_struct[key]).zfill(2) if key != "year" else str(date_struct[key]))
    if parts:
        return "-".join(parts) if len(parts) == 3 else parts[0]
    return None


def normalize_study(raw: dict[str, Any]) -> TrialRecord | None:
    """Parse a ClinicalTrials.gov API v2 study JSON object into a TrialRecord."""
    study = _get_study_payload(raw)
    section = study.get("protocolSection") or study
    ident = _module(section, "identificationModule")
    status = _module(section, "statusModule")
    sponsor_mod = _module(section, "sponsorCollaboratorsModule")
    design = _module(section, "designModule")
    conditions_mod = _module(section, "conditionsModule")
    arms_mod = _module(section, "armsInterventionsModule")
    desc_mod = _module(section, "descriptionModule")
    outcomes_mod = _module(section, "outcomesModule")

    nct_id = ident.get("nctId") or raw.get("NCTId") or ""
    if not nct_id:
        return None

    lead = sponsor_mod.get("leadSponsor") or {}
    sponsor = lead.get("name") or raw.get("LeadSponsorName") or "Unknown"

    phases = design.get("phases") or []
    if not phases and raw.get("Phase"):
        phases = [raw["Phase"]] if isinstance(raw["Phase"], str) else list(raw["Phase"])
    phase = _first_or_join(phases) or "NA"

    overall_status = status.get("overallStatus") or raw.get("OverallStatus") or "UNKNOWN"
    why_stopped = status.get("whyStopped") or raw.get("WhyStopped")

    last_update = _date_string(status.get("lastUpdatePostDateStruct"))
    if not last_update:
        last_update = raw.get("LastUpdatePostDate")

    enrollment_info = design.get("enrollmentInfo") or {}
    enrollment = _parse_int(enrollment_info.get("count"))
    if enrollment is None:
        enrollment = _parse_int(raw.get("EnrollmentCount"))

    has_results = bool(study.get("hasResults") or raw.get("HasResults"))

    conditions = list(conditions_mod.get("conditions") or [])
    if not conditions and raw.get("Condition"):
        c = raw["Condition"]
        conditions = [c] if isinstance(c, str) else list(c)

    interventions: list[str] = []
    intervention_types: list[str] = []
    for item in arms_mod.get("interventions") or []:
        name = item.get("name")
        if name:
            interventions.append(name)
        itype = item.get("type")
        if itype:
            intervention_types.append(itype)
    if not interventions and raw.get("InterventionName"):
        interventions = [raw["InterventionName"]] if isinstance(raw["InterventionName"], str) else list(raw["InterventionName"])
    if not intervention_types and raw.get("InterventionType"):
        intervention_types = [raw["InterventionType"]] if isinstance(raw["InterventionType"], str) else list(raw["InterventionType"])

    brief_summary = desc_mod.get("briefSummary") or raw.get("BriefSummary")
    detailed_description = desc_mod.get("detailedDescription") or raw.get("DetailedDescription")

    primary_outcomes = [
        o.get("measure", "")
        for o in (outcomes_mod.get("primaryOutcomes") or [])
        if o.get("measure")
    ]
    if not primary_outcomes and raw.get("PrimaryOutcomeMeasure"):
        primary_outcomes = [raw["PrimaryOutcomeMeasure"]]

    secondary_outcomes = [
        o.get("measure", "")
        for o in (outcomes_mod.get("secondaryOutcomes") or [])
        if o.get("measure")
    ]
    if not secondary_outcomes and raw.get("SecondaryOutcomeMeasure"):
        secondary_outcomes = [raw["SecondaryOutcomeMeasure"]]

    record = TrialRecord(
        nct_id=nct_id,
        title=ident.get("briefTitle") or raw.get("BriefTitle") or "",
        sponsor=sponsor,
        phase=phase,
        status=overall_status,
        why_stopped=why_stopped,
        last_update_post_date=last_update,
        enrollment_count=enrollment,
        has_results=has_results,
        conditions=conditions,
        interventions=interventions,
        intervention_types=intervention_types,
        brief_summary=brief_summary,
        detailed_description=detailed_description,
        primary_outcomes=primary_outcomes,
        secondary_outcomes=secondary_outcomes,
        ctgov_url=TrialRecord.ctgov_link(nct_id),
    )
    record.registry_text = record.to_agent_context()
    return record
