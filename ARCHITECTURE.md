# Viscan Dental Assistant — Architecture

## Purpose
A synthetic-data proof of concept for natural-language patient report retrieval, clinical dictation drafts, and report-grounded conversational follow-up. It is a demo, not a clinical product.

## Request flow
1. The single-page HTML/CSS/JavaScript chat submits a user message or reviewed speech transcript to `POST /api/chat`.
2. `app/services/intent_service.py` asks the configured Groq model to classify the request as report retrieval, dictation drafting, contextual follow-up, general conversation, or unknown. It extracts structured parameters where appropriate. If the model is unavailable, a conservative deterministic fallback handles common phrasing.
3. The router invokes existing services rather than letting the LLM access records directly. The patient service performs deterministic identity matching; multiple matches require clarification.
4. The report service filters synthetic records by patient and requested report type, then selects the newest matching report. The selected report ID and patient ID are retained in in-memory session context.
5. Follow-up answers are generated from the selected report only. Responses include report evidence where a report was used. When Groq is unavailable, the app exposes the source report text rather than pretending to create a model-generated summary.
6. Dictation requests go to `app/services/dictation_service.py`. Structured output is checked against verbatim transcript spans. Findings or anatomical sites not directly supported by the transcript are rejected or omitted; the source transcript is preserved and clinician review remains required.
7. The UI renders normal assistant messages, report previews, ambiguity choices, evidence, and editable draft reports. Optional browser speech recognition places recognized text into the composer for review; typed input always works.

## Components
- `frontend/index.html`, `frontend/style.css`, `frontend/app.js`: unified responsive chat interface, session history, optional speech-to-text, and safe text rendering.
- `app/main.py`: FastAPI endpoints and static UI serving.
- `app/services/llm_service.py`: Groq client, structured JSON parsing, provider-failure fallback.
- `app/services/intent_service.py`: LLM-assisted intent classification and deterministic fallback routing.
- `app/services/patient_service.py`: deterministic identity matching and public patient fields.
- `app/services/report_service.py`: retrieval parameter extraction, filtering, ambiguity and report selection.
- `app/services/dictation_service.py`: source-grounded draft extraction and conservative fallback.
- `app/services/conversation_service.py`: tool orchestration, report context, grounded follow-up, and evidence.
- `app/data/`: synthetic patients and reports only.
- `tests/`: automated checks for retrieval, ambiguity, dictation grounding, flexible phrasing, contextual follow-up, and chat routing.

## Privacy, authorization, latency, and cost
No real patient data or external clinical systems are used. The prototype has no authentication or production authorization, and the in-memory session map is not suitable for multi-worker production deployment. A production version would require authenticated identity resolution, role-based access controls, audit logs, encrypted transport/storage, retention policies, clinician approval, monitoring, and privacy review. LLM calls add network latency and incur provider-dependent token costs; disabling Groq uses fallback behavior but reduces flexible language understanding. Never log API keys or sensitive patient data.

## Limitations
- The mock dataset is small and synthetic.
- Fallback routing recognizes common phrasings but is less flexible than the LLM path.
- Source-span validation is a basic guardrail, not a clinical fact checker.
- Browser speech recognition support depends on the browser and its permissions; the app does not upload raw audio to a dedicated STT service.
- The project does not integrate with PACS, real patient records, or real appointment systems.
