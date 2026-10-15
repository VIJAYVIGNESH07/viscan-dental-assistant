"""Deterministic patient/report lookup with LLM-assisted request interpretation."""
import re
from typing import Optional

from app.data_store import get_reports
from app.services.patient_service import find_patient_matches, public_patient
from app.services.llm_service import groq_json

REPORT_TYPES = {"OPG", "INTRAORAL", "BITEWING", "UNKNOWN"}


def _normalize_report_type(value: str) -> str:
    normalized = re.sub(r"[^A-Z]", "", str(value or "UNKNOWN").upper())
    aliases = {
        "PANORAMIC": "OPG", "ORTHOPANTOMOGRAM": "OPG", "ORTHOPANTOMOGRAPH": "OPG",
        "INTRAORAL": "INTRAORAL", "BITEWING": "BITEWING", "UNKNOWN": "UNKNOWN", "": "UNKNOWN",
    }
    return aliases.get(normalized, normalized if normalized in REPORT_TYPES else "UNKNOWN")


def _clean_patient_name(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"(?i)([a-z])['’]s\b", r"\1", value)
    value = re.sub(r"[^A-Za-z0-9 ]", " ", value)
    return " ".join(value.split()).strip()


def parse_retrieval_intent(query: str) -> dict:
    data = groq_json(
        "Interpret a user request to retrieve a synthetic dental report. Return JSON only "
        "with intent, patient_name, report_type. intent is retrieve_report or unknown. "
        "report_type is OPG, INTRAORAL, BITEWING, or UNKNOWN. Understand synonyms such as "
        "panoramic/orthopantomogram for OPG and intra-oral for INTRAORAL. Extract only the "
        "patient name actually mentioned; do not guess. If no name is present, use an empty string.",
        query,
    )
    if data:
        intent = str(data.get("intent", "unknown")).lower()
        patient_name = _clean_patient_name(str(data.get("patient_name") or ""))
        report_type = _normalize_report_type(str(data.get("report_type") or "UNKNOWN"))
        if intent == "retrieve_report" and patient_name and report_type in REPORT_TYPES:
            return {"intent": intent, "patient_name": patient_name, "report_type": report_type}

    # Conservative fallback for offline mode. Remove request wording, not patient-name tokens.
    q = query.strip()
    lower = q.lower()
    report_type = "UNKNOWN"
    if re.search(r"\b(opg|panoramic|orthopantomogram)\b", lower):
        report_type = "OPG"
    elif re.search(r"\b(intra[- ]?oral)\b", lower):
        report_type = "INTRAORAL"
    elif re.search(r"\bbite\s?wing\b", lower):
        report_type = "BITEWING"

    cleaned = re.sub(r"(?i)([a-z])['’]s\b", r"\1", q)
    remove_phrases = [
        r"\b(?:could you|can you|could i|can i|may i|would you|please|i need to|i want to|i would like to|i need|i want)\b",
        r"\b(?:open|show|see|view|review|check|find|search for|look up|pull up|bring up|retrieve|get|display|access|fetch)\b",
        r"\b(?:the|latest|newest|most recent|recent|report|reports|patient|for|of|from|her|his|their|findings|details|information|results|record|records|scan|opg|panoramic|orthopantomogram|intra[- ]?oral|bite\s?wing)\b",
        r"\b(?:summarize|summary|review|view)\b",
    ]
    for pattern in remove_phrases:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^A-Za-z0-9 ]", " ", cleaned)
    name = " ".join(cleaned.split()).strip()
    return {"intent": "retrieve_report" if name else "unknown", "patient_name": name, "report_type": report_type}


def retrieve_report(query: str, parsed_intent: Optional[dict] = None) -> dict:
    intent = parsed_intent or parse_retrieval_intent(query)
    patient_name = _clean_patient_name(str(intent.get("patient_name") or ""))
    report_type = _normalize_report_type(str(intent.get("report_type") or "UNKNOWN"))
    if intent.get("intent") != "retrieve_report" or not patient_name or report_type not in REPORT_TYPES:
        return {
            "status": "clarification_required",
            "message": "Please tell me the patient's name and, if known, the report type (for example, OPG).",
            "evidence": [],
        }

    matches = find_patient_matches(patient_name)
    if not matches:
        return {"status": "not_found", "message": f"No patient matched '{patient_name}'.", "evidence": []}
    if len(matches) > 1:
        return {
            "status": "clarification_required",
            "message": f"More than one patient matches '{patient_name}'. Please choose the correct patient.",
            "candidates": [public_patient(patient) for patient in matches],
            "evidence": [],
        }

    patient = matches[0]
    patient_reports = [r for r in get_reports() if r.get("patient_id") == patient.get("patient_id")]
    if report_type != "UNKNOWN":
        patient_reports = [r for r in patient_reports if str(r.get("report_type", "")).upper() == report_type]
    if not patient_reports:
        requested = f"{report_type} " if report_type != "UNKNOWN" else ""
        return {
            "status": "not_found",
            "message": f"No {requested}report was found for {patient['name']}.",
            "patient": public_patient(patient),
            "evidence": [],
        }

    patient_reports.sort(key=lambda r: r.get("report_date") or "0000-00-00", reverse=True)
    report = patient_reports[0]
    return {
        "status": "success",
        "intent": "retrieve_report",
        "message": f"Retrieved {report.get('report_type', 'dental')} report {report['report_id']} for {patient['name']}.",
        "patient": public_patient(patient),
        "report": report,
        "evidence": [{"report_id": report["report_id"], "source": "synthetic_report_store"}],
    }


def get_report_by_id(report_id: str) -> Optional[dict]:
    return next((report for report in get_reports() if report.get("report_id") == report_id), None)
