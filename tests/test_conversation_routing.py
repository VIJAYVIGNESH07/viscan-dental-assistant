def test_natural_language_retrieval_with_synonyms(client):
    response = client.post("/api/chat", json={
        "query": "Could you bring up Priya Sharma's most recent panoramic report?",
        "session_id": "synonym-retrieval",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["patient"]["name"] == "Priya Sharma"
    assert data["report"]["report_id"] == "REP001"
    assert data["evidence"][0]["report_id"] == "REP001"


def test_follow_up_uses_previously_selected_report(client):
    session = "context-follow-up"
    first = client.post("/api/chat", json={
        "query": "Open Priya Sharma latest OPG report", "session_id": session,
    }).json()
    assert first["status"] == "success"

    second = client.post("/api/chat", json={
        "query": "Summarize it in simple language", "session_id": session,
    }).json()
    assert second["status"] == "success"
    assert second["report"]["report_id"] == "REP001"
    assert second["evidence"][0]["report_id"] == "REP001"
    assert "horizontally impacted" in second["message"].lower()


def test_chat_dictation_routes_to_structured_draft(client):
    response = client.post("/api/chat", json={
        "query": "Generate a draft from this observation: Lower right third molar is horizontally impacted.",
        "session_id": "dictation-chat",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "draft"
    assert data["requires_clinician_review"] is True
    assert data["source_transcript"] == "Lower right third molar is horizontally impacted."
    assert "horizontally impacted" in data["draft_report"].lower()


def test_general_capability_question_does_not_require_selected_report(client):
    response = client.post("/api/chat", json={
        "query": "What can you help me with?", "session_id": "general-help",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["intent"] == "general"
    assert "synthetic" in data["message"].lower()


def test_alternate_retrieval_wording_is_understood(client):
    response = client.post("/api/chat", json={
        "query": "Can I see the latest OPG findings for Priya Sharma?",
        "session_id": "alternate-wording",
    })
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "success"
    assert data["patient"]["name"] == "Priya Sharma"
    assert data["report"]["report_id"] == "REP001"


def test_llm_structured_intent_drives_tool_call(client, monkeypatch):
    monkeypatch.setattr("app.services.intent_service.groq_json", lambda *_: {
        "intent": "retrieve_report",
        "patient_name": "Priya Sharma",
        "report_type": "PANORAMIC",
        "transcript": "",
    })
    response = client.post("/api/chat", json={
        "query": "Would you locate Priya Sharma's panoramic record for me?",
        "session_id": "llm-routed-retrieval",
    })
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "success"
    assert data["report"]["report_id"] == "REP001"


def test_follow_up_uses_dynamic_grounded_llm_answer(client, monkeypatch):
    session = "dynamic-follow-up"
    first = client.post("/api/chat", json={
        "query": "Open Priya Sharma latest OPG report", "session_id": session,
    }).json()
    assert first["status"] == "success"
    monkeypatch.setattr("app.services.conversation_service.groq_json", lambda *_: {
        "answer": "The selected report describes horizontal impaction of the lower right third molar.",
        "unsupported": False,
    })
    second = client.post("/api/chat", json={
        "query": "Can you explain the main finding?", "session_id": session,
    }).json()
    assert second["status"] == "success"
    assert second["message"].startswith("The selected report describes")
    assert second["evidence"][0]["report_id"] == "REP001"


def test_missing_patient_does_not_fabricate_report(client):
    response = client.post("/api/chat", json={
        "query": "Open the latest OPG report for Unlisted Exampleperson",
        "session_id": "missing-patient",
    })
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "not_found"
    assert "report" not in data or data["report"] is None
    assert data.get("evidence", []) == []


def test_plain_transcript_is_accepted_without_draft_command(client):
    response = client.post("/api/chat", json={
        "query": "Lower right third molar is horizontally impacted.",
        "session_id": "plain-transcript",
    })
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "draft"
    assert data["source_transcript"] == "Lower right third molar is horizontally impacted."
    assert data["requires_clinician_review"] is True


def test_contextual_follow_up_without_selected_report_asks_for_clarification(client):
    response = client.post("/api/chat", json={
        "query": "Summarize her report", "session_id": "no-selected-report",
    })
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "clarification_required"
    assert "which report" in data["message"].lower() or "open" in data["message"].lower()


def test_summarize_latest_named_report_retrieves_then_summarizes(client, monkeypatch):
    monkeypatch.setattr("app.services.conversation_service.groq_json", lambda *_: None)
    response = client.post("/api/chat", json={
        "query": "Summarize the findings in the latest report for Priya Sharma.",
        "session_id": "summary-latest-priya",
    })
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "success"
    assert data["patient"]["name"] == "Priya Sharma"
    assert data["report"]["report_id"] == "REP001"
    assert "horizontally impacted" in data["message"].lower()
    assert data["evidence"][0]["report_id"] == "REP001"


def test_previous_visit_uses_selected_patient_and_older_report(client):
    session = "previous-visit-priya"
    first = client.post("/api/chat", json={
        "query": "Show me Priya Sharma's latest report.",
        "session_id": session,
    }).json()
    assert first["status"] == "success"
    assert first["report"]["report_id"] == "REP001"

    previous = client.post("/api/chat", json={
        "query": "Show me the report from the previous visit for this patient.",
        "session_id": session,
    }).json()
    assert previous["status"] == "success"
    assert previous["report"]["report_id"] == "REP002"
    assert previous["patient"]["name"] == "Priya Sharma"


def test_all_patient_reports_lists_only_bundled_synthetic_reports(client):
    response = client.post("/api/chat", json={
        "query": "Give me all patient reports.",
        "session_id": "all-synthetic-reports",
    })
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "success"
    assert data["intent"] == "list_reports"
    assert len(data["reports"]) == 10
    assert "synthetic demo dataset" in data["message"].lower()
    assert "production systems must enforce" in data["note"].lower()


def test_report_summary_wording_variation_is_handled_without_llm(client, monkeypatch):
    monkeypatch.setattr("app.services.conversation_service.groq_json", lambda *_: None)
    response = client.post("/api/chat", json={
        "query": "Tell me the findings in the most recent report for Arun Kumar.",
        "session_id": "alternate-summary-arun",
    })
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "success"
    assert data["patient"]["name"] == "Arun Kumar"
    assert data["report"]["report_id"] == "REP005"
    assert "mild crowding" in data["message"].lower()
