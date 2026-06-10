"""
Attention Scorer — monotonic deduction model.

Bắt đầu ở 100. Mỗi khi mất tập trung hoặc buồn ngủ → trừ điểm.
Đã trừ rồi thì KHÔNG hồi lại — điểm cuối phiên phản ánh đúng tổng "chi phí"
sao nhãng trong toàn bộ phiên học.
"""
from __future__ import annotations

from typing import Any, Optional

from app.config import settings
from app.services.analytics.vocabulary import (
    AttentionScore,
    AttentionState,
    CompositeEventType,
    COMPOSITE_DISTRACTION,
    COMPOSITE_SLEEPY,
)


class AttentionScorer:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._score: float = 100.0
        self._last_ts: Optional[float] = None
        self._history: list[AttentionScore] = []

    def update(self, ts: float, active_composites: list[str]) -> AttentionScore:
        # dt capped at 5s to avoid huge jumps after pauses
        dt = min((ts - self._last_ts) if self._last_ts is not None else 1.0, 5.0)
        self._last_ts = ts

        distraction_names = {e.value for e in COMPOSITE_DISTRACTION}
        sleepy_names = {e.value for e in COMPOSITE_SLEEPY}
        composites = set(active_composites)

        # Chỉ trừ, không bao giờ cộng — điểm đi xuống là không quay lại.
        if composites & distraction_names:
            self._score = max(0.0, self._score - settings.SCORE_DISTRACTION_RATE_PER_S * dt)
        elif composites & sleepy_names:
            self._score = max(0.0, self._score - settings.SCORE_SLEEPY_RATE_PER_S * dt)
        # Focused / neutral: điểm giữ nguyên (không cộng).

        score = round(self._score, 1)
        state = self._classify(active_composites)
        result = AttentionScore(
            session_id=self.session_id,
            timestamp=ts,
            score=score,
            state=state,
            active_composites=active_composites,
        )
        self._history.append(result)
        return result

    @staticmethod
    def _classify(active_composites: list[str]) -> AttentionState:
        # State chỉ phụ thuộc hành vi hiện tại (composites đang hoạt động),
        # KHÔNG dựa vào điểm số — điểm là chi phí lũy kế, không phản ánh hiện tại.
        sleepy_names = {e.value for e in COMPOSITE_SLEEPY}
        distraction_names = {e.value for e in COMPOSITE_DISTRACTION}
        if any(c in sleepy_names for c in active_composites):
            return AttentionState.SLEEPY
        if CompositeEventType.PHONE_DISTRACTION.value in active_composites:
            return AttentionState.ON_PHONE
        if any(c in distraction_names for c in active_composites):
            return AttentionState.DISTRACTED
        return AttentionState.FOCUSED

    def get_history(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._history]

    def get_last_score(self) -> float:
        return self._score
