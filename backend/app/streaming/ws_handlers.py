"""
WebSocket message handler — orchestrates the full pipeline per frame.

Pipeline:
  FeatureFrame → AtomicEncoder → CompositeInferrer → AttentionScorer
              → AlertGenerator → send back to client
"""
from __future__ import annotations

import time
from typing import Any, Optional

from app.services.analytics.atomic_encoder import AtomicEncoder
from app.services.analytics.composite_inferrer import CompositeInferrer
from app.services.analytics.attention_scorer import AttentionScorer
from app.services.recommendation.alert_generator import AlertGenerator
from app.storage.event_buffer import store
from app.streaming.ws_manager import manager


class SessionPipeline:
    """Per-session processing pipeline."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.atomic = AtomicEncoder(session_id)
        self.composite = CompositeInferrer(session_id)
        self.scorer = AttentionScorer(session_id)
        self.alerter = AlertGenerator(session_id)
        self._last_score_ts: float = 0.0
        self._score_interval: float = 1.0

    def process_frame(self, frame: dict[str, Any]) -> dict[str, Any]:
        ts = frame.get("timestamp", time.time())

        # 1. Atomic events
        atomic_events = self.atomic.process(frame)
        for ev in atomic_events:
            if ev.timestamp_end is None:
                ev.finalize(ts)
            store.add_event(self.session_id, ev.to_dict())

        # 2. Composite inference
        atomic_state = self.atomic.get_current_state()
        composite_events = self.composite.infer(atomic_state, ts)
        for ev in composite_events:
            store.add_event(self.session_id, ev.to_dict())

        active_composites = self.composite.get_active_composites()

        # 3. Attention score (once per interval)
        score_record = None
        if ts - self._last_score_ts >= self._score_interval:
            score_obj = self.scorer.update(ts, active_composites)
            score_record = score_obj.to_dict()
            store.add_attention_score(self.session_id, score_record)
            self._last_score_ts = ts

        # 4. Alert check
        alert_data: Optional[dict] = None
        if score_record:
            alert = self.alerter.check(score_record)
            if alert:
                alert_data = alert.to_dict()
                store.add_alert(self.session_id, alert_data)

        return {
            "type": "frame_processed",
            "timestamp": ts,
            "active_composites": active_composites,
            "atomic_count": len(atomic_events),
            "score": score_record,
            "alert": alert_data,
        }

    def set_calibration(self, baseline: dict) -> None:
        store.set_calibration(self.session_id, baseline)
        self.atomic.baseline = baseline


# In-memory registry of active pipelines
_pipelines: dict[str, SessionPipeline] = {}


def get_or_create_pipeline(session_id: str) -> SessionPipeline:
    if session_id not in _pipelines:
        _pipelines[session_id] = SessionPipeline(session_id)
    return _pipelines[session_id]


def remove_pipeline(session_id: str) -> None:
    _pipelines.pop(session_id, None)
