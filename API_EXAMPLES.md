# Viscan API examples and sample outputs

These examples document the synthetic-data proof of concept and can be used as submission demo evidence if a screen-recorded video is not supplied. Run the server from the project root first:


uvicorn app.main:app --reload


Base URL: `http://127.0.0.1:8000`

The exact natural-language `message` may differ when Groq is enabled. Patient/report IDs, status behavior, validation rules, and evidence should remain grounded in the mock dataset.

## 1. Health check


curl http://127.0.0.1:8000/api/health


Example shape:


{
  "status": "ok",
  "service": "Viscan Dental Assistant",
  "groq_enabled": true,
  "groq_key_configured": false,
  "groq_model": "openai/gpt-oss-20b",
  "mode": "fallback"
}


`groq_key_configured` and `mode` reflect the local `.env` configuration.

## 2. Retrieve a report using natural language


curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"Could you bring up Priya Sharma\u0027s most recent panoramic report?","session_id":"demo-1"}'


Expected key fields in the response:


{
  "status": "success",
  "intent": "retrieve_report",
  "patient": {"patient_id": "PAT001", "name": "Priya Sharma", "date_of_birth": "1998-04-12"},
  "report": {
    "report_id": "REP001",
    "patient_id": "PAT001",
    "report_type": "OPG",
    "report_date": "2026-08-10",
    "report_text": "Synthetic OPG report: lower right third molar is described as horizontally impacted."
  },
  "evidence": [{"report_id": "REP001", "source": "synthetic_report_store"}]
}


## 3. Ambiguous patient name

curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"Open Priya latest OPG report","session_id":"demo-2"}'


Expected behavior: `status` is `clarification_required`, with candidates for `Priya Sharma` and `Priya Shankar`. The backend does not choose a patient until the identity is unambiguous.

## 4. Clinical dictation to structured draft


curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"Generate a draft from this observation: Lower right third molar is horizontally impacted.","session_id":"demo-3"}'


Expected key fields:


{
  "status": "draft",
  "intent": "dictation_draft",
  "findings": [
    {
      "finding": "Lower right third molar is horizontally impacted.",
      "anatomical_site": "lower right third molar",
      "certainty": "stated_in_transcript",
      "source_text": "Lower right third molar is horizontally impacted."
    }
  ],
  "draft_report": "Lower right third molar is horizontally impacted.",
  "requires_clinician_review": true,
  "source_transcript": "Lower right third molar is horizontally impacted.",
  "evidence": [
    {"source": "user_provided_transcript", "source_text": "Lower right third molar is horizontally impacted."}
  ]
}
```

The exact extracted finding fields may be conservative in fallback mode. The source transcript is preserved and clinician review is always required.

## 5. Contextual follow-up

Use the same `session_id` as a successful retrieval:


curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"Summarize it in simple language","session_id":"demo-1"}'


Expected behavior: the response references report `REP001`, includes its evidence ID, and answers from that report only. In fallback mode, it exposes the report text instead of inventing a summary.

## 6. Missing patient/report

curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"Open the latest OPG report for Unlisted Exampleperson","session_id":"demo-4"}'


Expected behavior: `status` is `not_found`; no report is fabricated and no report evidence is returned.

## 7. Automated tests

python -m pytest -q


The tests use mocked/disabled LLM calls for repeatable validation and do not require a real Groq API key. A live Groq call should be separately verified using the user's own configured key and currently supported model.
