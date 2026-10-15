from typing import Literal, Optional
from pydantic import BaseModel, Field


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    session_id: str = Field(default="demo-session", min_length=1, max_length=120)


class DictationRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=10000)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(default="demo-session", min_length=1, max_length=120)


class Finding(BaseModel):
    finding: str
    anatomical_site: Optional[str] = None
    certainty: Literal["stated_in_transcript", "uncertain"] = "stated_in_transcript"
    source_text: str


class DraftReport(BaseModel):
    status: Literal["draft"] = "draft"
    findings: list[Finding]
    draft_report: str
    uncertainties: list[str] = Field(default_factory=list)
    requires_clinician_review: bool = True
    source_transcript: str


class EvidenceItem(BaseModel):
    report_id: str
    source: str = "synthetic_report_store"


class RetrieveResponse(BaseModel):
    status: Literal["success", "clarification_required", "not_found", "error"]
    message: str
    patient: Optional[dict] = None
    report: Optional[dict] = None
    candidates: list[dict] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
