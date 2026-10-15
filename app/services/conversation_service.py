"""Conversational orchestration: interpret, validate, call tools, then ground the answer."""
import re
from typing import Any, Optional

from app.services.intent_service import interpret_intent
from app.services.report_service import retrieve_report, get_report_by_id
from app.data_store import get_patients, get_reports
from app.services.dictation_service import create_draft
from app.services.llm_service import groq_json

# In-memory demo state only; use a secure store and authentication for production.
SESSIONS: dict[str, dict[str, Any]] = {}


def _public_report(report: dict) -> dict:
    return {
        "report_id": report.get("report_id"),
        "patient_id": report.get("patient_id"),
        "report_type": report.get("report_type"),
        "report_date": report.get("report_date"),
        "findings": report.get("findings", []),
        "report_text": report.get("report_text", ""),
    }



def _normalized_text(value: str) -> str:
    value = re.sub(r"(?i)([a-z])['’]s\b", r"\1", value or "")
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", value.lower()).split())


def _mentioned_patient(query: str) -> Optional[dict]:
    """Resolve only a full synthetic patient name literally present in the request."""
    normalized_query = f" {_normalized_text(query)} "
    patients = sorted(get_patients(), key=lambda patient: len(patient.get("name", "")), reverse=True)
    for patient in patients:
        normalized_name = _normalized_text(patient.get("name", ""))
        if normalized_name and f" {normalized_name} " in normalized_query:
            return patient
    return None


def _set_selected_report(session_id: str, patient: dict, report: dict, query: str, intent_name: str = "retrieve_report") -> dict:
    context = SESSIONS.get(session_id, {})
    history = context.get("history", [])
    history.extend([{"role": "user", "content": query}])
    SESSIONS[session_id] = {
        "patient_id": patient["patient_id"],
        "patient_name": patient["name"],
        "report_id": report["report_id"],
        "history": history[-12:],
    }
    return {
        "status": "success",
        "intent": intent_name,
        "message": f"Retrieved {report.get('report_type', 'dental')} report {report['report_id']} for {patient['name']} dated {report.get('report_date', 'date not recorded')}.",
        "patient": {"patient_id": patient["patient_id"], "name": patient["name"]},
        "report": _public_report(report),
        "evidence": [{"report_id": report["report_id"], "source": "synthetic_report_store"}],
    }


def _list_all_synthetic_reports() -> dict:
    """List only the bundled synthetic demo records; this is not a production access pattern."""
    patients = {p["patient_id"]: p for p in get_patients()}
    reports = sorted(get_reports(), key=lambda r: (r.get("report_date") or ""), reverse=True)
    lines = ["Here are all reports in the synthetic demo dataset (not real patient records):"]
    for report in reports:
        patient = patients.get(report.get("patient_id"), {})
        findings = report.get("findings") or []
        finding_text = "; ".join(
            str(item.get("text", "")) if isinstance(item, dict) else str(item)
            for item in findings
        ).strip()
        lines.append(
            f"• {patient.get('name', 'Unknown patient')} — {report.get('report_type', 'Dental')} — "
            f"{report.get('report_date', 'date not recorded')} — {report.get('report_id', 'no ID')}: "
            f"{finding_text or 'No findings recorded'}"
        )
    return {
        "status": "success",
        "intent": "list_reports",
        "message": "\n".join(lines),
        "reports": [_public_report(report) for report in reports],
        "evidence": [{"report_id": report["report_id"], "source": "synthetic_report_store"} for report in reports],
        "note": "Synthetic demonstration data only. Production systems must enforce user authentication and patient-level authorization.",
    }


def _previous_visit(query: str, session_id: str, context: dict) -> dict:
    patient_id = context.get("patient_id")
    current_report_id = context.get("report_id")
    if not patient_id or not current_report_id:
        return {
            "status": "clarification_required",
            "intent": "previous_visit",
            "message": "Which patient do you mean? Open that patient's latest report first, then ask for the previous visit.",
            "evidence": [],
        }
    patient = next((p for p in get_patients() if p.get("patient_id") == patient_id), None)
    current_report = get_report_by_id(current_report_id)
    patient_reports = sorted(
        [r for r in get_reports() if r.get("patient_id") == patient_id],
        key=lambda r: r.get("report_date") or "0000-00-00",
        reverse=True,
    )
    if not patient or not current_report:
        return {
            "status": "clarification_required",
            "intent": "previous_visit",
            "message": "I could not confirm the selected patient/report. Please open the patient's report again.",
            "evidence": [],
        }
    older_reports = [r for r in patient_reports if (r.get("report_date") or "") < (current_report.get("report_date") or "")]
    if not older_reports:
        return {
            "status": "not_found",
            "intent": "previous_visit",
            "message": f"No report from a visit before {current_report.get('report_date')} is available for {patient.get('name')} in the synthetic dataset.",
            "patient": {"patient_id": patient_id, "name": patient.get("name")},
            "evidence": [],
        }
    return _set_selected_report(session_id, patient, older_reports[0], query, intent_name="previous_visit")


def _explicit_workflow(query: str, session_id: str, context: dict) -> Optional[dict]:
    """Handle high-confidence, common requests deterministically before probabilistic LLM routing."""
    lower = query.lower().strip()
    if re.search(r"\b(all|every)\b.*\b(patient\s+)?reports?\b|\ball\s+patient\s+records\b", lower):
        return _list_all_synthetic_reports()

    if re.search(r"\b(previous|prior|earlier|previously)\s+(visit|report|record)\b|\breport\s+from\s+the\s+previous\s+visit\b", lower):
        return _previous_visit(query, session_id, context)

    patient = _mentioned_patient(query)
    report_request = bool(re.search(r"\b(report|record|scan|opg|panoramic|orthopantomogram|intra[- ]?oral|bite\s?wing)\b", lower))
    if patient and report_request:
        parsed = {
            "intent": "retrieve_report",
            "patient_name": patient["name"],
            "report_type": "UNKNOWN",
        }
        if re.search(r"\b(opg|panoramic|orthopantomogram)\b", lower):
            parsed["report_type"] = "OPG"
        elif re.search(r"\bintra[- ]?oral\b", lower):
            parsed["report_type"] = "INTRAORAL"
        elif re.search(r"\bbite\s?wing\b", lower):
            parsed["report_type"] = "BITEWING"
        result = retrieve_report(query, parsed_intent=parsed)
        if result.get("status") == "success" and result.get("patient") and result.get("report"):
            patient_data = next((p for p in get_patients() if p["patient_id"] == result["patient"]["patient_id"]), patient)
            selected = _set_selected_report(session_id, patient_data, result["report"], query)
            summary_request = bool(re.search(r"\b(summarize|summarise|summary|findings?|explain)\b", lower))
            if summary_request:
                return _follow_up("Summarize the findings in this report", session_id, SESSIONS[session_id])
            return selected
        result["intent"] = "retrieve_report"
        return result
    return None

def _general_response(query: str) -> str:
    data = groq_json(
        "You are Viscan, a prototype assistant for synthetic dental report retrieval and clinical "
        "dictation drafting. Respond naturally and concisely to greetings, questions about your "
        "capabilities, and general workflow questions. You may give high-level educational context, "
        "but do not diagnose, recommend treatment for a person, claim to have examined an image, "
        "or invent patient/report data. If the request is outside this prototype's scope, politely "
        "explain what you can do. Return JSON with keys answer and out_of_scope (boolean).",
        query,
    )
    if data and isinstance(data.get("answer"), str) and data["answer"].strip():
        return data["answer"].strip()
    lower = query.lower().strip()
    if lower in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}:
        return "Hello! I can help retrieve synthetic dental reports, summarize a selected report, and turn a provided clinical transcript into an editable draft for clinician review."
    if "what can you do" in lower or "help me" in lower:
        return "I can find synthetic patient reports, answer follow-up questions using a selected report, and convert supplied clinical dictation into a structured draft. I cannot access real patient systems or replace clinician review."
    return "I can help with synthetic dental report retrieval, questions grounded in a selected report, and structured drafts from supplied clinical dictation. For patient-specific questions, please select the relevant report first."


def _follow_up(query: str, session_id: str, context: dict) -> dict:
    report_id = context.get("report_id")
    report = get_report_by_id(report_id) if report_id else None
    if not report:
        SESSIONS.pop(session_id, None)
        return {
            "status": "clarification_required",
            "intent": "follow_up",
            "message": "I don't have an available report selected in this conversation. Please tell me which patient's report to open first.",
            "evidence": [],
        }

    # The LLM receives only the selected synthetic report and the current question.
    report_payload = _public_report(report)
    data = groq_json(
        "Answer the user's question using only the supplied synthetic report. Be natural and "
        "direct, and adapt the explanation to the question (summary, specific finding, simpler "
        "wording, or restatement). Do not infer missing details or provide a diagnosis/treatment "
        "recommendation. If the report does not specify something, say so. Return JSON with "
        "keys answer and unsupported (boolean).",
        f"SELECTED_REPORT={report_payload}\nQUESTION={query}",
    )
    if data and isinstance(data.get("answer"), str) and data["answer"].strip():
        answer = data["answer"].strip()
    else:
        # Safe offline fallback summarizes only explicit source findings; it never invents details.
        lower_query = query.lower()
        findings = report.get("findings") or []
        finding_text = [
            str(item.get("text", "")).strip() if isinstance(item, dict) else str(item).strip()
            for item in findings
        ]
        finding_text = [item for item in finding_text if item]
        if any(cue in lower_query for cue in ("summarize", "summarise", "summary", "main finding", "findings", "simple language")):
            if finding_text:
                answer = (
                    f"The report dated {report.get('report_date', 'unknown date')} "
                    f"({report.get('report_type', 'dental')}) records: " + "; ".join(finding_text) + "."
                )
            else:
                answer = f"The selected report ({report['report_id']}) does not contain recorded findings."
        else:
            answer = f"The selected synthetic report ({report['report_id']}) states: {report.get('report_text', 'No report text is available.')}"

    context["history"] = (context.get("history", []) + [{"role": "user", "content": query}, {"role": "assistant", "content": answer}])[-12:]
    SESSIONS[session_id] = context
    return {
        "status": "success",
        "intent": "follow_up",
        "message": answer,
        "patient": {"patient_id": context.get("patient_id"), "name": context.get("patient_name")},
        "report": report_payload,
        "evidence": [{"report_id": report["report_id"], "source": "synthetic_report_store"}],
    }


def handle_chat(query: str, session_id: str) -> dict:
    query = (query or "").strip()
    if not query:
        return {"status": "error", "intent": "unknown", "message": "Please enter a message.", "evidence": []}

    context = SESSIONS.get(session_id, {})
    explicit_result = _explicit_workflow(query, session_id, context)
    if explicit_result is not None:
        return explicit_result

    # Deterministic contextual follow-ups take precedence over model classification.
    lower_query = query.lower()
    contextual_follow_up = bool(context.get("report_id")) and bool(re.search(
        r"(summarize|summarise|summary|findings|finding|explain|her|his|their|it|this report|that report|previous visit|prior visit)",
        lower_query,
    ))
    intent = {"intent": "follow_up"} if contextual_follow_up else interpret_intent(query, bool(context.get("report_id")))
    intent_name = intent.get("intent", "unknown")

    if intent_name == "retrieve_report":
        parsed = None
        if intent.get("patient_name"):
            parsed = {
                "intent": "retrieve_report",
                "patient_name": intent.get("patient_name"),
                "report_type": intent.get("report_type", "UNKNOWN"),
            }
        result = retrieve_report(query, parsed_intent=parsed)
        result["intent"] = "retrieve_report"
        if result.get("status") == "success" and result.get("report") and result.get("patient"):
            report = result["report"]
            patient = result["patient"]
            SESSIONS[session_id] = {
                "patient_id": patient["patient_id"],
                "patient_name": patient["name"],
                "report_id": report["report_id"],
                "history": [{"role": "user", "content": query}],
            }
        return result

    if intent_name == "dictation_draft":
        transcript = str(intent.get("transcript") or "").strip()
        if not transcript:
            return {"status": "clarification_required", "intent": intent_name, "message": "Please provide the exact clinical observation to draft from.", "evidence": []}
        try:
            draft = create_draft(transcript)
        except ValueError as exc:
            return {"status": "error", "intent": intent_name, "message": str(exc), "evidence": []}
        draft["intent"] = "dictation_draft"
        draft["message"] = "Draft created from the supplied transcript. Clinician review is required."
        draft["evidence"] = [{"source": "user_provided_transcript", "source_text": transcript}]
        return draft

    if intent_name == "follow_up":
        if not context.get("report_id"):
            return {
                "status": "clarification_required",
                "intent": "follow_up",
                "message": "Which report would you like me to use? Please ask me to open a patient's report first.",
                "evidence": [],
            }
        return _follow_up(query, session_id, context)

    if intent_name == "general":
        answer = _general_response(query)
        history = context.get("history", [])
        history.extend([{"role": "user", "content": query}, {"role": "assistant", "content": answer}])
        context["history"] = history[-12:]
        if context:
            SESSIONS[session_id] = context
        return {"status": "success", "intent": "general", "message": answer, "evidence": []}

    return {
        "status": "clarification_required",
        "intent": "unknown",
        "message": "I couldn't confidently determine the requested action. You can ask me to open a synthetic dental report, ask a question about a selected report, or generate a draft from a clinical transcript.",
        "evidence": [],
    }
