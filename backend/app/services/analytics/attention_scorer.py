"""
Attention Scorer — health-bar model.

Starts at 100. Deducts while distracted/sleepy, recovers while focused or neutral.
Never drops below 0, never exceeds 100.
"""
from __future__ import annotations

from typing import Any, Optional

from app.config import settings
from app.services.analytics.vocabulary import (
    AttentionScore,
    AttentionState,
    COMPOSITE_ENGAGEMENT,
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

        engagement_names = {e.value for e in COMPOSITE_ENGAGEMENT}
        distraction_names = {e.value for e in COMPOSITE_DISTRACTION}
        sleepy_names = {e.value for e in COMPOSITE_SLEEPY}
        composites = set(active_composites)

        if composites & distraction_names:
            self._score = max(0.0, self._score - settings.SCORE_DISTRACTION_RATE_PER_S * dt)
        elif composites & sleepy_names:
            self._score = max(0.0, self._score - settings.SCORE_SLEEPY_RATE_PER_S * dt)
        elif composites & engagement_names:
            self._score = min(100.0, self._score + settings.SCORE_ENGAGED_RATE_PER_S * dt)
        else:
            # Neutral — ngồi yên không sao nhãng → cộng điểm chậm
            self._score = min(100.0, self._score + settings.SCORE_NEUTRAL_RATE_PER_S * dt)

        score = round(self._score, 1)
        state = self._classify(score, active_composites)
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
    def _classify(score: float, active_composites: list[str]) -> AttentionState:
        sleepy_names = {e.value for e in COMPOSITE_SLEEPY}
        if any(c in sleepy_names for c in active_composites):
            return AttentionState.SLEEPY
        if score >= 60:
            return AttentionState.FOCUSED
        return AttentionState.DISTRACTED

    def get_history(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._history]

    def get_last_score(self) -> float:
        return self._score
