def test_ambiguous_first_name_requires_clarification(client):
    response = client.post("/api/reports/retrieve", json={
        "query": "Open Priya latest OPG report",
        "session_id": "test-ambiguous"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "clarification_required"
    assert data["report"] is None if "report" in data else True
    assert len(data["candidates"]) == 2
