"""
Composite Inferrer — derives composite behavior events from atomic state.

Each rule maps directly to a row in the README's Composite Events table.
Atomic encoder provides `get_current_state()`; this layer adds meaning.
"""
from __future__ import annotations

import time
from typing import Any, Optional

from app.config import settings  # noqa: F401 — dùng trong _eval_reading_materials
from app.services.analytics.vocabulary import (
    BehaviorEvent,
    CompositeEventType,
    EventCategory,
    EventGroup,
    COMPOSITE_SLEEPY,
)


def _make_composite(
    event_type: CompositeEventType,
    session_id: str,
    timestamp: float,
    confidence: float,
    attributes: Optional[dict] = None,
) -> BehaviorEvent:
    return BehaviorEvent(
        event_type=event_type.value,
        category=EventCategory.COMPOSITE,
        event_group=EventGroup.COMPOSITE,
        timestamp_start=timestamp,
        confidence=confidence,
        session_id=session_id,
        attributes=attributes or {},
    )


class CompositeInferrer:
    """
    Stateful inferrer. Tracks which composites are currently active to
    emit start/end events rather than per-frame events.
    """

    # Ngưỡng phát hiện hành vi lặp lại
    # Cao hơn để không nhầm với hành vi học bình thường (nhìn vở, ngẩng đầu)
    _NODDING_COUNT = 6        # ≥6 lần cúi đầu trong 60s → gật gù buồn ngủ
    _TURNING_COUNT = 5        # ≥5 lần quay đầu trong 60s → mất tập trung
    _REPEAT_WINDOW_S = 60.0

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._active: dict[str, float] = {}  # composite_type → start_ts
        self._last_inferred: set[str] = set()

        # Theo dõi chuyển trạng thái để phát hiện hành vi lặp
        self._head_down_times: list[float] = []    # timestamps mỗi lần đầu cúi
        self._head_turned_times: list[float] = []  # timestamps mỗi lần quay đầu
        self._prev_head_state: str = "facing"

        # Theo dõi sao nhãng liên tục để phát hiện dùng điện thoại
        self._distraction_since: Optional[float] = None

    def infer(self, atomic_state: dict[str, Any], ts: float) -> list[BehaviorEvent]:
        """
        Given current atomic state snapshot, return newly activated or
        completed composite events.
        """
        current: set[str] = set()
        emitted: list[BehaviorEvent] = []

        # Ghi nhận chuyển trạng thái đầu để phát hiện lặp
        head_state = atomic_state.get("head_state", "facing")
        if head_state != self._prev_head_state:
            if head_state == "down":
                self._head_down_times.append(ts)
            elif head_state in ("turned_left", "turned_right"):
                self._head_turned_times.append(ts)
            self._prev_head_state = head_state

        # ── Focused ──────────────────────────────────────────────
        self._eval_taking_notes(atomic_state, current)
        self._eval_reading_screen(atomic_state, current)
        self._eval_reading_materials(atomic_state, current)
        self._eval_writing(atomic_state, current)
        self._eval_thinking_pose(atomic_state, current)
        self._eval_actively_engaged(atomic_state, current)

        # ── Neutral ──────────────────────────────────────────────
        self._eval_passive_watching(atomic_state, current)

        # ── Sleepy ───────────────────────────────────────────────
        self._eval_drowsy(atomic_state, ts, current)
        self._eval_head_nodding(ts, current)

        # ── Distracted ───────────────────────────────────────────
        self._eval_looking_away(atomic_state, current)
        self._eval_frequent_head_turning(ts, current)
        self._eval_head_tilt_phone(atomic_state, current)
        self._eval_phone_distraction(atomic_state, current)
        self._eval_talking_to_someone(atomic_state, current)
        self._eval_away_from_desk(atomic_state, current)

        # Sao nhãng liên tục ≥60s → phone distraction (dù loại sao nhãng nào)
        _base_distractions = {
            CompositeEventType.LOOKING_AWAY.value,
            CompositeEventType.FREQUENT_HEAD_TURNING.value,
        }
        if current & _base_distractions:
            if self._distraction_since is None:
                self._distraction_since = ts
            elif ts - self._distraction_since >= settings.PHONE_USE_DURATION_MS / 1000:
                current.add(CompositeEventType.PHONE_DISTRACTION.value)
        elif atomic_state.get("face_present"):
            self._distraction_since = None

        # Newly started composites
        for ctype in current - self._last_inferred:
            self._active[ctype] = ts
            ev = _make_composite(CompositeEventType(ctype), self.session_id, ts, 0.8)
            emitted.append(ev)

        # Ended composites
        for ctype in self._last_inferred - current:
            start = self._active.pop(ctype, ts)
            ev = _make_composite(CompositeEventType(ctype), self.session_id, start, 0.8)
            ev.finalize(ts)
            emitted.append(ev)

        self._last_inferred = current
        return [e for e in emitted if e.confidence >= 0.5]

    def get_active_composites(self) -> list[str]:
        return list(self._last_inferred)

    # ── Rules ────────────────────────────────────────────────────────────────

    def _eval_taking_notes(self, s: dict, current: set) -> None:
        # head_down ∧ hand_writing ∧ ¬eyes_closed
        if (
            s.get("head_state") == "down"
            and s.get("hand_writing")
            and s.get("eye_state") != "closed"
        ):
            current.add(CompositeEventType.TAKING_NOTES.value)

    def _eval_reading_screen(self, s: dict, current: set) -> None:
        # head_facing_screen ∧ face_present ∧ mắt mở ∧ duration ≥ 1s → đọc màn hình.
        # Bỏ điều kiện gaze_on_screen vì nó được tính từ cùng góc đầu (redundant).
        head_facing = s.get("head_state") == "facing"
        face_present = s.get("face_present", False)
        eyes_open = s.get("eye_state") != "closed"
        duration_ok = s.get("head_state_duration_ms", 0) >= settings.READING_MIN_MS
        if head_facing and face_present and eyes_open and duration_ok:
            current.add(CompositeEventType.READING_SCREEN.value)

    def _eval_thinking_pose(self, s: dict, current: set) -> None:
        # hand_near_face ∧ (gaze_on_screen ∨ gaze_up) ∧ expr_neutral ∧ ¬eyes_closed
        gaze_ok = s.get("gaze_on_screen") or s.get("gaze_direction") == "up"
        hand_dur_ok = s.get("hand_near_face_duration_ms", 0) >= settings.THINKING_HAND_MIN_MS
        if (
            s.get("hand_near_face")
            and hand_dur_ok
            and gaze_ok
            and s.get("expr") == "neutral"
            and s.get("eye_state") != "closed"
        ):
            current.add(CompositeEventType.THINKING_POSE.value)

    def _eval_actively_engaged(self, s: dict, current: set) -> None:
        # lean_forward ∧ gaze_on_screen ∧ duration ≥ ACTIVELY_ENGAGED_MIN_MS
        if (
            s.get("lean_state") == "forward"
            and s.get("gaze_on_screen")
            and s.get("head_state_duration_ms", 0) >= settings.ACTIVELY_ENGAGED_MIN_MS
        ):
            current.add(CompositeEventType.ACTIVELY_ENGAGED.value)

    def _eval_passive_watching(self, s: dict, current: set) -> None:
        # gaze_on_screen ∧ head_facing ∧ expr_neutral ∧ lean_back ≥ PASSIVE_WATCHING_MIN_MS
        if (
            s.get("gaze_on_screen")
            and s.get("head_state") == "facing"
            and s.get("expr") == "neutral"
            and s.get("lean_state") == "back"
            and s.get("head_state_duration_ms", 0) >= settings.PASSIVE_WATCHING_MIN_MS
        ):
            current.add(CompositeEventType.PASSIVE_WATCHING.value)

    def _eval_drowsy(self, s: dict, ts: float, current: set) -> None:
        # eyes_closed ≥ 2s OR yawn ≥ 2 in 60s OR (head_down ∧ eyes_closed)
        eyes_closed_long = (
            s.get("eye_state") == "closed"
            and s.get("eye_state_duration_ms", 0) >= settings.EYES_CLOSED_DROWSY_MS
        )
        yawn_times = s.get("yawn_times", [])
        recent_yawns = sum(1 for t in yawn_times if ts - t <= settings.YAWN_COUNT_WINDOW_S)
        many_yawns = recent_yawns >= settings.YAWN_COUNT_DROWSY
        head_down_closed = s.get("head_state") == "down" and s.get("eye_state") == "closed"

        if eyes_closed_long or many_yawns or head_down_closed:
            current.add(CompositeEventType.DROWSY.value)

    def _eval_looking_away(self, s: dict, current: set) -> None:
        # Chỉ dùng head_turned có thời gian — đáng tin hơn gaze direction đơn lẻ.
        # head_down KHÔNG tính là looking_away (có thể đang đọc sách / viết bài).
        head_turned_long = (
            s.get("head_state") in ("turned_left", "turned_right")
            and s.get("head_state_duration_ms", 0) >= settings.GAZE_OFF_LOOKING_AWAY_MS
        )
        if head_turned_long:
            current.add(CompositeEventType.LOOKING_AWAY.value)

    def _eval_phone_distraction(self, s: dict, current: set) -> None:
        # Ưu tiên 1: Object detector thấy điện thoại ≥ 2s → ngay lập tức
        if (s.get("phone_detected")
                and s.get("phone_detected_duration_ms", 0) >= settings.PHONE_DETECTED_MIN_MS):
            current.add(CompositeEventType.PHONE_DISTRACTION.value)
            return

        # Fallback: đầu cúi ≥ 30s không viết bài (không có camera phone detection)
        head_down = s.get("head_state") == "down"
        not_writing = not s.get("hand_writing")
        long_enough = s.get("head_state_duration_ms", 0) >= settings.PHONE_DISTRACTION_MIN_MS
        if head_down and not_writing and long_enough:
            current.add(CompositeEventType.PHONE_DISTRACTION.value)

    def _eval_talking_to_someone(self, s: dict, current: set) -> None:
        # multiple_faces OR (talking_likely ∧ head_turned)
        multi = s.get("multiple_faces", False)
        talking_turned = (
            s.get("talking")
            and s.get("head_state") in ("turned_left", "turned_right")
        )
        if multi or talking_turned:
            current.add(CompositeEventType.TALKING_TO_SOMEONE.value)

    def _eval_away_from_desk(self, s: dict, current: set) -> None:
        # face_absent_long (tracked by face_present = False for >10s via atomic encoder)
        if not s.get("face_present"):
            current.add(CompositeEventType.AWAY_FROM_DESK.value)

    def _eval_head_tilt_phone(self, s: dict, current: set) -> None:
        # Đầu nghiêng ≥20° (roll lớn) trong khi mặt hiện diện → có thể đọc điện thoại ngang
        if s.get("face_present") and abs(s.get("head_roll", 0.0)) >= settings.HEAD_TILT_THRESHOLD:
            current.add(CompositeEventType.LOOKING_AWAY.value)

    def _eval_reading_materials(self, s: dict, current: set) -> None:
        # Đọc sách / tài liệu / viết bài: đầu cúi + mặt hiện diện + mắt mở.
        # Tính là focused cho đến khi đủ điều kiện phone_distraction (30s).
        # phone_distraction sẽ ghi đè nếu cần — hai rule là loại trừ nhau qua duration.
        head_down = s.get("head_state") == "down"
        face_present = s.get("face_present", False)
        eyes_open = s.get("eye_state") != "closed"
        duration = s.get("head_state_duration_ms", 0)
        # Chỉ nhường cho phone_distraction sau 30s — trước đó coi là đọc/viết
        not_phone_yet = duration < settings.PHONE_DISTRACTION_MIN_MS
        if head_down and face_present and eyes_open and not_phone_yet:
            current.add(CompositeEventType.READING_MATERIALS.value)

    def _eval_writing(self, s: dict, current: set) -> None:
        # Viết bài: tay viết + mặt hiện diện (không nhất thiết head_down)
        if s.get("hand_writing") and s.get("face_present") and s.get("eye_state") != "closed":
            current.add(CompositeEventType.WRITING.value)

    def _eval_head_nodding(self, ts: float, current: set) -> None:
        # Gật gù: đầu cúi ≥ N lần trong cửa sổ REPEAT_WINDOW_S giây
        self._head_down_times = [t for t in self._head_down_times if ts - t <= self._REPEAT_WINDOW_S]
        if len(self._head_down_times) >= self._NODDING_COUNT:
            current.add(CompositeEventType.HEAD_NODDING.value)

    def _eval_frequent_head_turning(self, ts: float, current: set) -> None:
        # Quay đầu liên tục: quay đầu ≥ N lần trong cửa sổ REPEAT_WINDOW_S giây
        self._head_turned_times = [t for t in self._head_turned_times if ts - t <= self._REPEAT_WINDOW_S]
        if len(self._head_turned_times) >= self._TURNING_COUNT:
            current.add(CompositeEventType.FREQUENT_HEAD_TURNING.value)
