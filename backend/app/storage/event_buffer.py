"""
In-memory session store (replaces PostgreSQL for MVP).
Stores sessions, events, attention scores, and alerts.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SessionRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    calibration_baseline: dict = field(default_factory=dict)
    overall_score: Optional[float] = None
    events: list[dict] = field(default_factory=list)
    attention_scores: list[dict] = field(default_factory=list)
    alerts: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "overall_score": self.overall_score,
            "calibration_baseline": self.calibration_baseline,
            "event_count": len(self.events),
            "score_count": len(self.attention_scores),
            "alert_count": len(self.alerts),
        }


class SessionStore:
    """Thread-safe-ish in-memory store for MVP."""

    def __init__(self):
        self._sessions: dict[str, SessionRecord] = {}

    def create_session(self) -> SessionRecord:
        rec = SessionRecord()
        self._sessions[rec.id] = rec
        return rec

    def get(self, session_id: str) -> Optional[SessionRecord]:
        return self._sessions.get(session_id)

    def end_session(self, session_id: str, overall_score: Optional[float] = None) -> None:
        rec = self._sessions.get(session_id)
        if rec:
            rec.ended_at = time.time()
            rec.overall_score = overall_score

    def add_event(self, session_id: str, event_dict: dict) -> None:
        rec = self._sessions.get(session_id)
        if rec:
            rec.events.append(event_dict)

    def add_attention_score(self, session_id: str, score_dict: dict) -> None:
        rec = self._sessions.get(session_id)
        if rec:
            rec.attention_scores.append(score_dict)

    def add_alert(self, session_id: str, alert_dict: dict) -> None:
        rec = self._sessions.get(session_id)
        if rec:
            rec.alerts.append(alert_dict)

    def set_calibration(self, session_id: str, baseline: dict) -> None:
        rec = self._sessions.get(session_id)
        if rec:
            rec.calibration_baseline = baseline

    def list_sessions(self) -> list[dict]:
        return [s.to_dict() for s in self._sessions.values()]

    def get_full(self, session_id: str) -> Optional[dict[str, Any]]:
        rec = self._sessions.get(session_id)
        if not rec:
            return None
        return {
            **rec.to_dict(),
            "events": rec.events,
            "attention_scores": rec.attention_scores,
            "alerts": rec.alerts,
        }


# Singleton store shared across the application
store = SessionStore()
