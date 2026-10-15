# 3–5 minute Viscan demo script

## 0:00–0:25 — Introduction
Introduce Viscan as a synthetic-data proof of concept. Show the unified chat UI and the API status indicator. Explain that Groq enables flexible intent interpretation and natural-language responses; fallback mode remains conservative.

## 0:25–1:10 — Natural-language report retrieval
Ask: `Could you bring up Priya Sharma's most recent panoramic report?`
Show the patient, report ID, report date, report text, and evidence source. Explain that “panoramic” is interpreted as OPG and the backend still performs deterministic matching.

## 1:10–1:45 — Ambiguous identity
Ask: `Open Priya latest OPG report`.
Show that the assistant asks the user to choose between Priya Sharma and Priya Shankar instead of guessing. Select the correct candidate if the UI presents the choice buttons.

## 1:45–2:30 — Clinical dictation
Ask: `Generate a draft from this observation: Lower right third molar is horizontally impacted.`
Show the editable report draft, structured JSON, source transcript, source evidence, and clinician-review warning. Explain that unsupported findings/sites are rejected or omitted and the transcript is preserved conservatively.

## 2:30–3:15 — Contextual follow-up
Retrieve Priya Sharma's report, then ask: `Summarize it in simple language` or `Can you explain the main finding?`
Show that the answer references the previously selected report and displays the report ID as evidence. If Groq is disabled, the app deliberately shows the selected report text rather than claiming to have generated a model summary.

## 3:15–3:45 — Optional speech input
If the browser supports the Web Speech API, click Dictate, speak a short request, and show that the recognized text appears in the composer for review before sending. Typed input remains available in every browser.

## 3:45–4:30 — Safety and tests
Try a missing patient/report and show the safe not-found response. Run `python -m pytest -q` and show the passing tests. Mention the synthetic dataset, in-memory session state, lack of real PACS/authentication, provider-dependent latency/cost, and that source-span validation is a basic safeguard rather than a clinical fact checker.
