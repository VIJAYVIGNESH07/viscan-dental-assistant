"""Conservative transcript-to-draft conversion for synthetic demonstration data."""
import re
from app.models import DraftReport, Finding
from app.services.llm_service import groq_json


def _fallback_extract(transcript: str) -> list[Finding]:
    cleaned = " ".join(transcript.strip().split())
    site = None
    match = re.search(
        r"(?i)\b(upper|lower)\s+(left|right)\s+([a-z ]{0,35}?(?:molar|incisor|canine|premolar|tooth|teeth))\b",
        cleaned,
    )
    if match:
        site = match.group(0).strip()
    return [Finding(
        finding=cleaned,
        anatomical_site=site,
        certainty="stated_in_transcript",
        source_text=cleaned,
    )]


def create_draft(transcript: str) -> dict:
    transcript = " ".join((transcript or "").strip().split())
    if not transcript:
        raise ValueError("Transcript must not be empty.")

    data = groq_json(
        "Extract structured information from clinical dictation. Do not diagnose, infer, or add "
        "observations. Return JSON with findings (array of finding, anatomical_site, certainty, "
        "source_text) and uncertainties (array). Every source_text must be an exact substring of "
        "the transcript. The finding and anatomical_site must each be directly stated in the "
        "transcript; if you cannot quote them exactly, use the exact source phrase or null for the "
        "site. certainty is stated_in_transcript or uncertain. Do not add negative findings unless "
        "explicitly spoken.",
        transcript,
    )

    findings = []
    uncertainties = []
    if data and isinstance(data.get("findings"), list):
        for item in data["findings"]:
            if not isinstance(item, dict):
                continue
            source_text = " ".join(str(item.get("source_text") or "").split())
            finding_text = " ".join(str(item.get("finding") or "").split())
            if not source_text or source_text.casefold() not in transcript.casefold():
                uncertainties.append("A model-produced finding was rejected because its source text was not found verbatim in the transcript.")
                continue
            # Do not accept paraphrased/invented clinical claims from the model.
            if not finding_text or finding_text.casefold() not in transcript.casefold():
                finding_text = source_text
                uncertainties.append("A finding was kept as its exact source phrase to avoid unsupported paraphrasing.")
            anatomical_site = str(item.get("anatomical_site") or "").strip() or None
            if anatomical_site and anatomical_site.casefold() not in transcript.casefold():
                anatomical_site = None
                uncertainties.append("An anatomical site was omitted because it was not stated verbatim in the transcript.")
            certainty = item.get("certainty")
            if certainty not in {"stated_in_transcript", "uncertain"}:
                certainty = "uncertain"
            findings.append(Finding(
                finding=finding_text,
                anatomical_site=anatomical_site,
                certainty=certainty,
                source_text=source_text,
            ))
        if isinstance(data.get("uncertainties"), list):
            uncertainties.extend(str(value) for value in data["uncertainties"] if isinstance(value, str) and value.strip())

    if not findings:
        findings = _fallback_extract(transcript)
        if data:
            uncertainties.append("The model output did not pass source-span validation; the transcript was preserved conservatively.")
        else:
            uncertainties.append("LLM unavailable; transcript preserved without additional clinical interpretation.")

    # The readable draft uses only verbatim source spans, so it cannot add claims absent from dictation.
    source_spans = []
    for finding in findings:
        if finding.source_text not in source_spans:
            source_spans.append(finding.source_text)
    draft_text = " ".join(span.rstrip(" .") + "." for span in source_spans)

    result = DraftReport(
        findings=findings,
        draft_report=draft_text,
        uncertainties=list(dict.fromkeys(uncertainties)),
        requires_clinician_review=True,
        source_transcript=transcript,
    )
    output = result.model_dump()
    output["evidence"] = [{"source": "user_provided_transcript", "source_text": transcript}]
    return output
