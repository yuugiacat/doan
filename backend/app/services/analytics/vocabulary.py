"""
Behavior Vocabulary — single source of truth for all event types.
Every event name used elsewhere in the codebase must be declared here first.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class EventCategory(str, Enum):
    ATOMIC = "atomic"
    COMPOSITE = "composite"


class EventGroup(str, Enum):
    PRESENCE = "presence"
    GAZE = "gaze"
    HEAD_POSE = "head_pose"
    FACIAL_EXPRESSION = "facial_expression"
    BODY_HANDS = "body_hands"
    COMPOSITE = "composite"


class AtomicEventType(str, Enum):
    # A1. Presence
    FACE_PRESENT = "face_present"
    FACE_ABSENT_SHORT = "face_absent_short"
    FACE_ABSENT_LONG = "face_absent_long"
    MULTIPLE_FACES = "multiple_faces"

    # A2. Gaze
    GAZE_ON_SCREEN = "gaze_on_screen"
    GAZE_OFF_SCREEN = "gaze_off_screen"
    BLINK = "blink"
    EYES_CLOSED = "eyes_closed"

    # A3. Head Pose
    HEAD_FACING_SCREEN = "head_facing_screen"
    HEAD_TURNED = "head_turned"
    HEAD_DOWN = "head_down"
    HEAD_UP = "head_up"

    # A4. Facial Expression
    EXPR_NEUTRAL = "expr_neutral"
    EXPR_HAPPY = "expr_happy"
    EXPR_SURPRISE = "expr_surprise"
    EXPR_SAD = "expr_sad"
    EXPR_ANGRY = "expr_angry"
    EXPR_FEAR = "expr_fear"
    EXPR_DISGUST = "expr_disgust"

    # A5. Body & Hands
    HAND_NEAR_FACE = "hand_near_face"
    HAND_WRITING = "hand_writing"
    HAND_HOLDING_PHONE_LIKELY = "hand_holding_phone_likely"
    MOUTH_OPEN_WIDE = "mouth_open_wide"
    YAWN = "yawn"
    STRETCH = "stretch"
    LEAN_FORWARD = "lean_forward"
    LEAN_BACK = "lean_back"
    TALKING_LIKELY = "talking_likely"


class CompositeEventType(str, Enum):
    # Focused — hành vi học tập hợp lệ
    TAKING_NOTES = "taking_notes"           # ghi chú
    READING_SCREEN = "reading_screen"       # đọc trên màn hình
    READING_MATERIALS = "reading_materials" # nhìn tài liệu / đọc sách
    THINKING_POSE = "thinking_pose"         # suy nghĩ ngắn
    ACTIVELY_ENGAGED = "actively_engaged"   # tập trung chủ động
    WRITING = "writing"                     # viết bài

    # Neutral
    PASSIVE_WATCHING = "passive_watching"   # xem thụ động (không tính lỗi)

    # Distracted — mất tập trung
    LOOKING_AWAY = "looking_away"                   # nhìn khỏi vùng học quá lâu
    FREQUENT_HEAD_TURNING = "frequent_head_turning" # quay đầu liên tục
    PHONE_DISTRACTION = "phone_distraction"         # dùng điện thoại
    TALKING_TO_SOMEONE = "talking_to_someone"       # nói chuyện
    AWAY_FROM_DESK = "away_from_desk"               # rời khỏi bàn học

    # Sleepy — mệt mỏi
    DROWSY = "drowsy"           # nhắm mắt lâu / đầu cúi + mắt nhắm
    HEAD_NODDING = "head_nodding" # gật gù (đầu cúi liên tục nhiều lần)


class AttentionState(str, Enum):
    FOCUSED = "focused"       # đang học (đọc, ghi, suy nghĩ)
    DISTRACTED = "distracted" # mất tập trung (nhìn chỗ khác, rời bàn, quay đầu)
    SLEEPY = "sleepy"         # mệt mỏi (nhắm mắt, gật gù, đầu cúi liên tục)


class AlertType(str, Enum):
    NUDGE = "nudge"
    ALERT = "alert"
    STRONG_ALERT = "strong_alert"


# Sets used by attention scorer
COMPOSITE_ENGAGEMENT: set[CompositeEventType] = {
    CompositeEventType.TAKING_NOTES,
    CompositeEventType.READING_SCREEN,
    CompositeEventType.READING_MATERIALS,
    CompositeEventType.THINKING_POSE,
    CompositeEventType.ACTIVELY_ENGAGED,
    CompositeEventType.WRITING,
}

COMPOSITE_DISTRACTION: set[CompositeEventType] = {
    CompositeEventType.LOOKING_AWAY,
    CompositeEventType.FREQUENT_HEAD_TURNING,
    CompositeEventType.PHONE_DISTRACTION,
    CompositeEventType.TALKING_TO_SOMEONE,
    CompositeEventType.AWAY_FROM_DESK,
}

COMPOSITE_SLEEPY: set[CompositeEventType] = {
    CompositeEventType.DROWSY,
    CompositeEventType.HEAD_NODDING,
}

COMPOSITE_NEUTRAL: set[CompositeEventType] = {
    CompositeEventType.PASSIVE_WATCHING,
}

ATOMIC_GROUP_MAP: dict[AtomicEventType, EventGroup] = {
    AtomicEventType.FACE_PRESENT: EventGroup.PRESENCE,
    AtomicEventType.FACE_ABSENT_SHORT: EventGroup.PRESENCE,
    AtomicEventType.FACE_ABSENT_LONG: EventGroup.PRESENCE,
    AtomicEventType.MULTIPLE_FACES: EventGroup.PRESENCE,
    AtomicEventType.GAZE_ON_SCREEN: EventGroup.GAZE,
    AtomicEventType.GAZE_OFF_SCREEN: EventGroup.GAZE,
    AtomicEventType.BLINK: EventGroup.GAZE,
    AtomicEventType.EYES_CLOSED: EventGroup.GAZE,
    AtomicEventType.HEAD_FACING_SCREEN: EventGroup.HEAD_POSE,
    AtomicEventType.HEAD_TURNED: EventGroup.HEAD_POSE,
    AtomicEventType.HEAD_DOWN: EventGroup.HEAD_POSE,
    AtomicEventType.HEAD_UP: EventGroup.HEAD_POSE,
    AtomicEventType.EXPR_NEUTRAL: EventGroup.FACIAL_EXPRESSION,
    AtomicEventType.EXPR_HAPPY: EventGroup.FACIAL_EXPRESSION,
    AtomicEventType.EXPR_SURPRISE: EventGroup.FACIAL_EXPRESSION,
    AtomicEventType.EXPR_SAD: EventGroup.FACIAL_EXPRESSION,
    AtomicEventType.EXPR_ANGRY: EventGroup.FACIAL_EXPRESSION,
    AtomicEventType.EXPR_FEAR: EventGroup.FACIAL_EXPRESSION,
    AtomicEventType.EXPR_DISGUST: EventGroup.FACIAL_EXPRESSION,
    AtomicEventType.HAND_NEAR_FACE: EventGroup.BODY_HANDS,
    AtomicEventType.HAND_WRITING: EventGroup.BODY_HANDS,
    AtomicEventType.HAND_HOLDING_PHONE_LIKELY: EventGroup.BODY_HANDS,
    AtomicEventType.MOUTH_OPEN_WIDE: EventGroup.BODY_HANDS,
    AtomicEventType.YAWN: EventGroup.BODY_HANDS,
    AtomicEventType.STRETCH: EventGroup.BODY_HANDS,
    AtomicEventType.LEAN_FORWARD: EventGroup.BODY_HANDS,
    AtomicEventType.LEAN_BACK: EventGroup.BODY_HANDS,
    AtomicEventType.TALKING_LIKELY: EventGroup.BODY_HANDS,
}


@dataclass
class BehaviorEvent:
    event_type: str
    category: EventCategory
    event_group: EventGroup
    timestamp_start: float
    confidence: float
    session_id: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp_end: Optional[float] = None
    duration_ms: Optional[int] = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def finalize(self, timestamp_end: float) -> None:
        self.timestamp_end = timestamp_end
        self.duration_ms = int((timestamp_end - self.timestamp_start) * 1000)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "category": self.category.value,
            "event_group": self.event_group.value,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "duration_ms": self.duration_ms,
            "confidence": self.confidence,
            "attributes": self.attributes,
        }


@dataclass
class AttentionScore:
    session_id: str
    timestamp: float
    score: float
    state: AttentionState
    active_composites: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "score": self.score,
            "state": self.state.value,
            "active_composites": self.active_composites,
        }


@dataclass
class Alert:
    session_id: str
    timestamp: float
    alert_type: AlertType
    reason: str
    message: str
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "alert_type": self.alert_type.value,
            "reason": self.reason,
            "message": self.message,
        }
