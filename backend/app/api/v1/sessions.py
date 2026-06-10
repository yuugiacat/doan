from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.analytics.session_analyzer import SessionAnalyzer
from app.services.recommendation.advice_generator import generate_advice
from app.storage import db
from app.storage.event_buffer import store

router = APIRouter(prefix="/sessions", tags=["sessions"])
_analyzer = SessionAnalyzer()

# Lưu metadata user (anonymous_id, email, consent) theo session_id —
# in-memory, dùng lại lúc end_session để biết có flush DB không.
_meta: dict[str, dict] = {}


class CreateSessionBody(BaseModel):
    anonymous_id: Optional[str] = None
    email: Optional[str] = None
    display_name: Optional[str] = None
    consent_research: bool = False


@router.post("/")
def create_session(body: Optional[CreateSessionBody] = None):
    rec = store.create_session()
    if body is not None:
        _meta[rec.id] = {
            "anonymous_id": body.anonymous_id or "anonymous",
            "email": body.email,
            "display_name": body.display_name,
            "consent_research": body.consent_research,
        }
    return {"session_id": rec.id, "started_at": rec.started_at}


@router.get("/")
def list_sessions():
    return store.list_sessions()


@router.get("/{session_id}")
def get_session(session_id: str):
    rec = store.get(session_id)
    if not rec:
        raise HTTPException(404, "Session not found")
    return rec.to_dict()


@router.post("/{session_id}/end")
async def end_session(session_id: str):
    full = store.get_full(session_id)
    if not full:
        raise HTTPException(404, "Session not found")
    analysis = _analyzer.analyze(full)
    overall = analysis.get("overall_score")
    store.end_session(session_id, overall)
    advice = generate_advice(analysis)

    # Flush DB nếu user đã đồng ý nghiên cứu
    meta = _meta.pop(session_id, {})
    if meta.get("consent_research") and db.is_enabled():
        rec = store.get(session_id)
        if rec and rec.ended_at:
            await db.flush_session(
                anonymous_id=meta.get("anonymous_id", "anonymous"),
                email=meta.get("email"),
                display_name=meta.get("display_name"),
                consent_given=True,
                started_at=rec.started_at,
                ended_at=rec.ended_at,
                analysis=analysis,
                full_payload={**full, "analysis": analysis, "advice": advice},
            )

    return {"session_id": session_id, "analysis": analysis, "advice": advice}


@router.get("/{session_id}/report")
def get_report(session_id: str):
    full = store.get_full(session_id)
    if not full:
        raise HTTPException(404, "Session not found")
    analysis = _analyzer.analyze(full)
    advice = generate_advice(analysis)
    return {
        **full,
        "analysis": analysis,
        "advice": advice,
    }
