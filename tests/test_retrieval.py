def test_correct_retrieval(client):
    response = client.post("/api/reports/retrieve", json={
        "query": "Open Priya Sharma latest OPG report",
        "session_id": "test-retrieval"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["patient"]["patient_id"] == "PAT001"
    assert data["report"]["report_id"] == "REP001"
