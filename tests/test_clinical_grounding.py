from app.services.dictation_service import create_draft


def test_transcript_is_preserved_without_inventing_findings(monkeypatch):
    # With Groq disabled, fallback preserves only the provided transcript.
    monkeypatch.setattr("app.services.dictation_service.groq_json", lambda *_: None)
    transcript = "Lower right third molar is horizontally impacted."
    result = create_draft(transcript)
    assert result["requires_clinician_review"] is True
    assert len(result["findings"]) == 1
    assert "infection" not in result["draft_report"].lower()
    assert result["findings"][0]["source_text"] == transcript


def test_model_cannot_add_finding_or_site_not_in_transcript(monkeypatch):
    monkeypatch.setattr("app.services.dictation_service.groq_json", lambda *_: {
        "findings": [{
            "finding": "infection",
            "anatomical_site": "upper left canine",
            "certainty": "stated_in_transcript",
            "source_text": "Lower right third molar is horizontally impacted.",
        }],
        "uncertainties": [],
    })
    result = create_draft("Lower right third molar is horizontally impacted.")
    finding = result["findings"][0]
    assert "infection" not in result["draft_report"].lower()
    assert finding["anatomical_site"] is None
    assert finding["source_text"] == "Lower right third molar is horizontally impacted."
