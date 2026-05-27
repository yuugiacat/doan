"""
Session Analyzer — post-session statistics and summary.
3 states: focused / distracted / sleepy.
"""
from __future__ import annotations

from typing import Any

from app.services.analytics.vocabulary import (
    AttentionState,
    COMPOSITE_DISTRACTION,
    COMPOSITE_SLEEPY,
)


class SessionAnalyzer:
    def analyze(self, session_data: dict[str, Any]) -> dict[str, Any]:
        scores = session_data.get("attention_scores", [])
        events = session_data.get("events", [])
        if not scores:
            return {}

        score_values = [s["score"] for s in scores]
        states = [s["state"] for s in scores]

        total = len(states)
        focused_pct = round(states.count(AttentionState.FOCUSED.value) / total * 100, 1)
        distracted_pct = round(states.count(AttentionState.DISTRACTED.value) / total * 100, 1)
        on_phone_pct = round(states.count(AttentionState.ON_PHONE.value) / total * 100, 1)
        sleepy_pct = round(states.count(AttentionState.SLEEPY.value) / total * 100, 1)

        peak_score = max(score_values)
        avg_score = round(sum(score_values) / len(score_values), 1)

        # Nguyên nhân mất tập trung (distracted + sleepy composites)
        bad_names = {c.value for c in COMPOSITE_DISTRACTION | COMPOSITE_SLEEPY}
        distraction_events = [
            e for e in events
            if e.get("category") == "composite" and e.get("event_type") in bad_names
        ]
        cause_counts: dict[str, int] = {}
        for ev in distraction_events:
            cause_counts[ev["event_type"]] = cause_counts.get(ev["event_type"], 0) + 1
        main_distraction_cause = max(cause_counts, key=cause_counts.get) if cause_counts else None

        # Số lần chuyển sang trạng thái tiêu cực
        bad_states = {
            AttentionState.DISTRACTED.value,
            AttentionState.ON_PHONE.value,
            AttentionState.SLEEPY.value,
        }
        distraction_episodes = 0
        prev = None
        for state in states:
            if prev not in bad_states and state in bad_states:
                distraction_episodes += 1
            prev = state

        # Phân phối biểu cảm
        expr_events = [e for e in events if e.get("event_group") == "facial_expression"]
        expr_counts: dict[str, int] = {}
        for ev in expr_events:
            etype = ev["event_type"].replace("expr_", "")
            expr_counts[etype] = expr_counts.get(etype, 0) + 1

        return {
            "overall_score": avg_score,
            "peak_score": peak_score,
            "focused_pct": focused_pct,
            "distracted_pct": distracted_pct,
            "on_phone_pct": on_phone_pct,
            "sleepy_pct": sleepy_pct,
            "distraction_episodes": distraction_episodes,
            "main_distraction_cause": main_distraction_cause,
            "distraction_cause_counts": cause_counts,
            "expression_counts": expr_counts,
        }
