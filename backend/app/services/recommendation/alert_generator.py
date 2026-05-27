"""
Alert Generator — fires real-time alerts based on sustained attention state.
3 states: FOCUSED (bình thường), DISTRACTED (mất tập trung), SLEEPY (mệt mỏi).
"""
from __future__ import annotations

from typing import Optional

from app.config import settings
from app.services.analytics.vocabulary import Alert, AlertType, AttentionState


_MESSAGES = {
    AttentionState.DISTRACTED: (
        AlertType.ALERT,
        "Bạn đang mất tập trung. Hãy quay lại bài học nhé!",
    ),
    AttentionState.SLEEPY: (
        AlertType.STRONG_ALERT,
        "Bạn có vẻ đang buồn ngủ hoặc mệt mỏi. Hãy nghỉ ngắn 5 phút rồi tiếp tục!",
    ),
}

_THRESHOLDS = {
    AttentionState.DISTRACTED: 30,   # cảnh báo sau 30s mất tập trung
    AttentionState.SLEEPY: 15,       # cảnh báo sau 15s biểu hiện mệt
}


class AlertGenerator:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._state_since: Optional[float] = None
        self._current_state: Optional[AttentionState] = None
        self._last_alert_ts: float = 0.0
        self._alert_cooldown_s: float = 30.0

    def check(self, score_record: dict) -> Optional[Alert]:
        ts = score_record["timestamp"]
        state = AttentionState(score_record["state"])
        composites = score_record.get("active_composites", [])

        if state != self._current_state:
            self._current_state = state
            self._state_since = ts

        if state == AttentionState.FOCUSED:
            return None

        since = self._state_since or ts
        duration_s = ts - since
        threshold = _THRESHOLDS.get(state, 9999)

        if duration_s < threshold:
            return None
        if ts - self._last_alert_ts < self._alert_cooldown_s:
            return None

        self._last_alert_ts = ts
        alert_type, message = _MESSAGES[state]
        reason = composites[0] if composites else state.value

        return Alert(
            session_id=self.session_id,
            timestamp=ts,
            alert_type=alert_type,
            reason=reason,
            message=message,
        )
