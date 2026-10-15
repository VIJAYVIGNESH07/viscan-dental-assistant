from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.models import RetrieveRequest, DictationRequest, ChatRequest
from app.data_store import get_patients
from app.services.report_service import get_report_by_id, retrieve_report
from app.services.dictation_service import create_draft
from app.services.conversation_service import handle_chat, SESSIONS

app = FastAPI(
    title="Viscan Dental Assistant",
    description="Synthetic-data proof of concept for dental report retrieval and clinical dictation drafts.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health():
    from app.config import GROQ_API_KEY, GROQ_ENABLED, GROQ_MODEL
    return {
        "status": "ok",
        "service": "Viscan Dental Assistant",
        "groq_enabled": GROQ_ENABLED,
        "groq_key_configured": bool(GROQ_API_KEY),
        "groq_model": GROQ_MODEL,
        "mode": "groq" if GROQ_ENABLED and GROQ_API_KEY else "fallback",
    }


@app.get("/api/patients")
def patients():
    # Synthetic demo endpoint. Do not expose patient listings like this in production.
    return {"patients": get_patients()}


@app.post("/api/reports/retrieve")
def reports_retrieve(request: RetrieveRequest):
    # This endpoint is explicitly a retrieval tool, so it does not depend on chat intent classification.
    result = retrieve_report(request.query)
    result["intent"] = "retrieve_report"
    if result.get("status") == "success" and result.get("patient") and result.get("report"):
        patient = result["patient"]
        report = result["report"]
        SESSIONS[request.session_id] = {
            "patient_id": patient["patient_id"],
            "patient_name": patient["name"],
            "report_id": report["report_id"],
            "history": [{"role": "user", "content": request.query}],
        }
    return result


@app.get("/api/reports/{report_id}")
def report_by_id(report_id: str):
    report = get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.post("/api/dictation/draft")
def dictation_draft(request: DictationRequest):
    try:
        return create_draft(request.transcript)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/chat")
def chat(request: ChatRequest):
    return handle_chat(request.query, request.session_id)
