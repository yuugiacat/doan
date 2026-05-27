from fastapi import APIRouter
from app.storage.event_buffer import store
from app.services.analytics.session_analyzer import SessionAnalyzer
from app.services.recommendation.advice_generator import generate_advice

router = APIRouter(prefix="/sessions", tags=["sessions"])
_analyzer = SessionAnalyzer()


@router.post("/")
def create_session():
    rec = store.create_session()
    return {"session_id": rec.id, "started_at": rec.started_at}


@router.get("/")
def list_sessions():
    return store.list_sessions()


@router.get("/{session_id}")
def get_session(session_id: str):
    rec = store.get(session_id)
    if not rec:
        from fastapi import HTTPException
        raise HTTPException(404, "Session not found")
    return rec.to_dict()


@router.post("/{session_id}/end")
def end_session(session_id: str):
    full = store.get_full(session_id)
    if not full:
        from fastapi import HTTPException
        raise HTTPException(404, "Session not found")
    analysis = _analyzer.analyze(full)
    overall = analysis.get("overall_score")
    store.end_session(session_id, overall)
    advice = generate_advice(analysis)
    return {"session_id": session_id, "analysis": analysis, "advice": advice}


@router.get("/{session_id}/report")
def get_report(session_id: str):
    full = store.get_full(session_id)
    if not full:
        from fastapi import HTTPException
        raise HTTPException(404, "Session not found")
    analysis = _analyzer.analyze(full)
    advice = generate_advice(analysis)
    return {
        **full,
        "analysis": analysis,
        "advice": advice,
    }
