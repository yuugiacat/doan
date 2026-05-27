from fastapi import APIRouter, HTTPException
from app.storage.event_buffer import store

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/{session_id}/scores")
def get_scores(session_id: str):
    rec = store.get(session_id)
    if not rec:
        raise HTTPException(404, "Session not found")
    return rec.attention_scores


@router.get("/{session_id}/events")
def get_events(session_id: str, category: str | None = None):
    rec = store.get(session_id)
    if not rec:
        raise HTTPException(404, "Session not found")
    events = rec.events
    if category:
        events = [e for e in events if e.get("category") == category]
    return events


@router.get("/{session_id}/alerts")
def get_alerts(session_id: str):
    rec = store.get(session_id)
    if not rec:
        raise HTTPException(404, "Session not found")
    return rec.alerts
