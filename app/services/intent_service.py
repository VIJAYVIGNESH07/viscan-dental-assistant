"""LLM-assisted intent routing with a deterministic offline fallback."""
import re
from typing import Optional

from app.services.llm_service import groq_json

_ALLOWED = {"retrieve_report", "dictation_draft", "follow_up", "general", "unknown"}


def _fallback_intent(query: str, has_report_context: bool) -> dict:
    text = query.strip()
    lower = text.lower()

    dictation_cues = (
        "draft a report", "generate a draft", "create a draft", "make a draft from", "write a draft from",
        "turn this into a draft", "from this dictation", "from this observation", "clinical dictation",
        "dictated observation", "transcript:", "draft this:",
    )
    if any(cue in lower for cue in dictation_cues):
        # Keep only text after a clear separator/prefix when present; otherwise preserve the full request.
        transcript = text
        match = re.search(r"(?is)(?:dictation|observation|transcript|draft)\s*(?:is)?\s*[:\-]\s*(.+)$", text)
        if match:
            transcript = match.group(1).strip().strip('"“”')
        else:
            match = re.search(r"(?is)(?:draft a report|generate a draft|create a draft)\s+(?:from|using)\s+(.+)$", text)
            if match:
                transcript = match.group(1).strip().strip('"“”')
        return {"intent": "dictation_draft", "transcript": transcript}

    retrieval_cues = (
        "open ", "show ", "find ", "retrieve ", "get me ", "pull up ", "bring up ",
        "look up ", "fetch ", "display ", "access ", "can i see ", "could i see ", "may i see ",
        "view ", "see the report", "latest report", "most recent report", "newest report",
        "report for ", "report of ", "opg for ", "latest opg", "panoramic report", "report belonging to ",
    )
    explicit_report_request = bool(re.search(r"\b(show|see|view|open|find|retrieve|fetch|access|review|check|need|want)\b", lower)) and bool(re.search(r"\b(opg|panoramic|orthopantomogram|intra[- ]?oral|bite\s?wing|report|scan)\b", lower))
    if any(cue in lower for cue in retrieval_cues) or explicit_report_request:
        return {"intent": "retrieve_report"}

    # The assignment also permits a raw speech-to-text clinical observation with no wrapper command.
    anatomy_present = bool(re.search(r"\b(upper|lower|left|right|third|first|second|central|lateral|molar|incisor|canine|premolar|tooth|teeth)\b", lower))
    observation_present = bool(re.search(r"\b(impacted|unerupted|erupted|crowding|caries|decay|fracture|fractured|restored|missing|lesion|radiolucent|radiopaque|swelling|tender|is|are|shows|showing|noted|identified)\b", lower))
    question_like = "?" in text or bool(re.match(r"(?i)\s*(what|why|how|does|do|is|are|can|could|would|should|explain|summarize)\b", text))
    report_question = bool(re.search(r"\b(report|summarize|summary|according to|in the record)\b", lower))
    if anatomy_present and observation_present and not question_like and not report_question:
        return {"intent": "dictation_draft", "transcript": text}

    followup_cues = (
        "summarize", "summary", "explain this report", "explain it", "what does it say",
        "main findings", "main finding", "the findings", "the finding", "finding in the report",
        "what are the findings", "what is in the report", "what does the report show", "what does the report say",
        "in simple language", "tell me more about this report", "explain the finding", "explain the main finding",
        "what about this report", "show it again", "repeat the report",
    )
    followup_reference = bool(re.search(r"\b(it|this|that|her|his|their|the report|this report|these findings)\b", lower))
    if any(cue in lower for cue in followup_cues) and (has_report_context or followup_reference):
        return {"intent": "follow_up"}

    if lower in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"} or "what can you do" in lower or "help me" in lower:
        return {"intent": "general"}

    if has_report_context and (" it" in lower or " her " in f" {lower} " or " his " in f" {lower} "):
        return {"intent": "follow_up"}

    # For an offline demo, unsupported queries get a scope response rather than guessed clinical data.
    return {"intent": "general"}


def interpret_intent(query: str, has_report_context: bool) -> dict:
    data = groq_json(
        "You are an intent router for a synthetic-data dental report assistant. Return JSON only "
        "with keys intent, patient_name, report_type, transcript. Allowed intent values: "
        "retrieve_report, dictation_draft, follow_up, general, unknown. "
        "For retrieve_report, extract only a patient name stated by the user and a report type "
        "from OPG, INTRAORAL, BITEWING, UNKNOWN. Panoramic/orthopantomogram means OPG. "
        "For dictation_draft, transcript must be a verbatim span of the user's message containing "
        "the clinical observation; never add words. For follow_up, use it only when asking about "
        "a report already selected in context. General covers greetings, capability questions, "
        "and non-patient-specific conversation. Do not interpret a clinical statement as a request "
        "to retrieve a report unless the user asks to retrieve one. Do not invent patient names.",
        f"HAS_SELECTED_REPORT={str(has_report_context).lower()}\nUSER_MESSAGE={query}",
    )
    if data:
        intent = str(data.get("intent", "unknown")).strip().lower()
        if intent in _ALLOWED:
            result = {"intent": intent}
            if intent == "retrieve_report":
                result["patient_name"] = str(data.get("patient_name") or "").strip()
                result["report_type"] = str(data.get("report_type") or "UNKNOWN").upper()
            if intent == "dictation_draft":
                transcript = str(data.get("transcript") or "").strip().strip('"“”')
                fallback = _fallback_intent(query, has_report_context)
                # Prefer an explicitly delimited transcript over a model response that repeats the command.
                if fallback["intent"] == "dictation_draft" and fallback.get("transcript") != query.strip():
                    result["transcript"] = fallback["transcript"]
                elif transcript and transcript.casefold() in query.casefold():
                    result["transcript"] = transcript
                elif fallback["intent"] == "dictation_draft":
                    result["transcript"] = fallback["transcript"]
                else:
                    return {"intent": "unknown"}
            fallback = _fallback_intent(query, has_report_context)
            has_negation = bool(re.search(r"\b(not|don't|do not|never|without)\b", query.lower()))
            # Do not let a weak general/unknown classification swallow an explicit workflow request.
            if intent in {"general", "unknown"} and fallback.get("intent") in {"retrieve_report", "dictation_draft", "follow_up"} and not has_negation:
                return fallback
            if intent != "unknown":
                return result
    return _fallback_intent(query, has_report_context)
