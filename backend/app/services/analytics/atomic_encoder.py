"""
Atomic Event Encoder — converts raw MediaPipe features into atomic behavior events.

Rules are purely based on thresholds (no semantic interpretation).
Composite layer handles meaning.
"""
from __future__ import annotations

import time
from typing import Any, Optional

from app.config import settings
from app.services.analytics.vocabulary import (
    AtomicEventType,
    BehaviorEvent,
    EventCategory,
    EventGroup,
    ATOMIC_GROUP_MAP,
)


FeatureFrame = dict[str, Any]
Baseline = dict[str, Any]


def _ear(frame: FeatureFrame, side: str) -> float:
    """Return Eye Aspect Ratio for 'left' or 'right' eye."""
    gaze = frame.get("gaze", {})
    return gaze.get(f"ear_{side}", 0.3)


def _avg_ear(frame: FeatureFrame) -> float:
    return (_ear(frame, "left") + _ear(frame, "right")) / 2.0


def _head_pose(frame: FeatureFrame) -> tuple[float, float, float]:
    hp = frame.get("head_pose", {})
    return hp.get("yaw", 0.0), hp.get("pitch", 0.0), hp.get("roll", 0.0)


def _gaze_on_screen(frame: FeatureFrame) -> bool:
    return frame.get("gaze", {}).get("on_screen", True)


def _gaze_direction(frame: FeatureFrame) -> str:
    return frame.get("gaze", {}).get("direction", "center")


def _face_info(frame: FeatureFrame) -> dict:
    return frame.get("face", {"detected": False, "count": 0, "confidence": 0.0})


def _hands(frame: FeatureFrame) -> dict:
    return frame.get("hands", {})


def _pose(frame: FeatureFrame) -> dict:
    return frame.get("pose", {})


def _expression(frame: FeatureFrame) -> dict:
    return frame.get("expression", {})


def _mouth_open_ratio(frame: FeatureFrame) -> float:
    return frame.get("mouth_open_ratio", 0.0)


def _make_event(
    event_type: AtomicEventType,
    session_id: str,
    timestamp: float,
    confidence: float,
    attributes: Optional[dict] = None,
) -> BehaviorEvent:
    return BehaviorEvent(
        event_type=event_type.value,
        category=EventCategory.ATOMIC,
        event_group=ATOMIC_GROUP_MAP[event_type],
        timestamp_start=timestamp,
        confidence=confidence,
        session_id=session_id,
        attributes=attributes or {},
    )


class AtomicEncoder:
    """
    Stateful encoder: tracks ongoing states to implement state-change detection.
    Only emits events when state transitions occur.
    """

    def __init__(self, session_id: str, baseline: Optional[Baseline] = None):
        self.session_id = session_id
        self.baseline = baseline or {}
        self._state: dict[str, Any] = {
            "face_present": False,
            "face_absent_start": None,
            "multiple_faces": False,
            "gaze_on_screen": True,
            "gaze_off_start": None,
            "eye_state": "open",       # open | blinking | closed
            "eye_state_start": None,
            "low_ear_start": None,     # mốc bắt đầu mắt sụp mí (lim dim hoặc nhắm)
            "head_state": "facing",    # facing | turned_left | turned_right | down | up
            "head_state_start": None,
            "lean_state": "neutral",   # neutral | forward | back
            "lean_baseline_z": None,
            "hand_near_face": False,
            "hand_near_face_start": None,
            "hand_writing": False,
            "phone_holding_likely": False,
            "phone_holding_start": None,
            "phone_detected": False,
            "phone_detected_start": None,
            "mouth_open": False,
            "mouth_open_start": None,
            "yawn_times": [],
            "expr": "neutral",
            "talking": False,
        }
        self._emitted_events: list[BehaviorEvent] = []

    def process(self, frame: FeatureFrame) -> list[BehaviorEvent]:
        """Process one feature frame. Returns newly emitted events."""
        self._emitted_events = []
        ts = frame.get("timestamp", time.time())

        self._process_presence(frame, ts)
        self._process_gaze(frame, ts)
        self._process_head_pose(frame, ts)
        self._process_expression(frame, ts)
        self._process_body_hands(frame, ts)
        self._process_phone_detected(frame, ts)

        # Filter low-confidence events
        return [e for e in self._emitted_events if e.confidence >= 0.5]

    def _emit(self, event: BehaviorEvent) -> None:
        self._emitted_events.append(event)

    # ── A1. Presence ─────────────────────────────────────────────────────────

    def _process_presence(self, frame: FeatureFrame, ts: float) -> None:
        info = _face_info(frame)
        detected = info.get("detected", False)
        count = info.get("count", 0)
        conf = info.get("confidence", 0.0)

        # Face present / absent transitions
        was_present = self._state["face_present"]
        if detected and count >= 1:
            if not was_present:
                # Transition: absent → present
                absent_start = self._state["face_absent_start"]
                if absent_start is not None:
                    duration_ms = int((ts - absent_start) * 1000)
                    etype = (
                        AtomicEventType.FACE_ABSENT_SHORT
                        if duration_ms < settings.FACE_ABSENT_SHORT_THRESHOLD_MS
                        else AtomicEventType.FACE_ABSENT_LONG
                    )
                    ev = _make_event(etype, self.session_id, absent_start, 0.95,
                                     {"duration_ms": duration_ms})
                    ev.finalize(ts)
                    self._emit(ev)
                self._state["face_absent_start"] = None
            self._state["face_present"] = True
            self._emit(_make_event(AtomicEventType.FACE_PRESENT, self.session_id, ts, conf))

            # Multiple faces
            multi_now = count > 1
            if multi_now and not self._state["multiple_faces"]:
                self._emit(_make_event(AtomicEventType.MULTIPLE_FACES, self.session_id, ts, conf,
                                       {"face_count": count}))
            self._state["multiple_faces"] = multi_now
        else:
            if was_present:
                # Start of absence
                self._state["face_absent_start"] = ts
            self._state["face_present"] = False
            self._state["multiple_faces"] = False

    # ── A2. Gaze ─────────────────────────────────────────────────────────────

    def _process_gaze(self, frame: FeatureFrame, ts: float) -> None:
        avg_ear = _avg_ear(frame)
        on_screen = _gaze_on_screen(frame)
        direction = _gaze_direction(frame)

        # Theo dõi mắt sụp mí (lim dim hoặc nhắm): EAR < ngưỡng drowsy.
        # Bao trùm cả "nhắm hờ" mà state machine open/blinking/closed bỏ sót.
        if avg_ear < settings.EAR_DROWSY_THRESHOLD:
            if self._state["low_ear_start"] is None:
                self._state["low_ear_start"] = ts
        else:
            self._state["low_ear_start"] = None

        # Eye state machine (open → blinking → closed)
        eye_state = self._state["eye_state"]
        eye_start = self._state["eye_state_start"]

        if avg_ear < settings.EAR_BLINK_THRESHOLD:
            if eye_state == "open":
                self._state["eye_state"] = "blinking"
                self._state["eye_state_start"] = ts
        else:
            if eye_state in ("blinking", "closed"):
                duration_ms = int((ts - eye_start) * 1000) if eye_start else 0
                if duration_ms < settings.EAR_BLINK_MAX_MS:
                    ev = _make_event(AtomicEventType.BLINK, self.session_id, eye_start or ts, 0.9,
                                     {"duration_ms": duration_ms})
                    ev.finalize(ts)
                    self._emit(ev)
                elif duration_ms >= settings.EAR_EYES_CLOSED_MIN_MS:
                    ev = _make_event(AtomicEventType.EYES_CLOSED, self.session_id, eye_start or ts, 0.9,
                                     {"duration_ms": duration_ms})
                    ev.finalize(ts)
                    self._emit(ev)
            self._state["eye_state"] = "open"
            self._state["eye_state_start"] = None

        # Upgrade blinking → closed after threshold
        if self._state["eye_state"] == "blinking" and eye_start:
            if (ts - eye_start) * 1000 >= settings.EAR_EYES_CLOSED_MIN_MS:
                self._state["eye_state"] = "closed"

        # Gaze on/off screen
        was_on = self._state["gaze_on_screen"]
        gaze_conf = frame.get("gaze", {}).get("confidence", 0.8)

        if on_screen:
            if not was_on:
                off_start = self._state["gaze_off_start"]
                if off_start:
                    ev = _make_event(AtomicEventType.GAZE_OFF_SCREEN, self.session_id, off_start, gaze_conf,
                                     {"direction": self._state.get("gaze_direction", "center"),
                                      "duration_ms": int((ts - off_start) * 1000)})
                    ev.finalize(ts)
                    self._emit(ev)
                self._state["gaze_off_start"] = None
            self._state["gaze_on_screen"] = True
            self._emit(_make_event(AtomicEventType.GAZE_ON_SCREEN, self.session_id, ts, gaze_conf))
        else:
            if was_on:
                self._state["gaze_off_start"] = ts
                self._state["gaze_direction"] = direction
            self._state["gaze_on_screen"] = False

    # ── A3. Head Pose ─────────────────────────────────────────────────────────

    def _process_head_pose(self, frame: FeatureFrame, ts: float) -> None:
        yaw, pitch, roll = _head_pose(frame)
        self._state["head_roll"] = roll
        cfg = settings

        if abs(yaw) <= cfg.HEAD_FACING_YAW_MAX and abs(pitch) <= cfg.HEAD_FACING_PITCH_MAX:
            new_state = "facing"
        # Ưu tiên "down" hơn "turned": khi vừa cúi vừa nghiêng (đọc sách/viết
        # vở để cạnh bàn) thì coi là cúi đầu — đó là tư thế học, không phải sao nhãng.
        elif pitch < cfg.HEAD_PITCH_DOWN_THRESHOLD:
            new_state = "down"
        elif abs(yaw) > cfg.HEAD_YAW_THRESHOLD:
            new_state = "turned_left" if yaw < 0 else "turned_right"
        elif pitch > cfg.HEAD_PITCH_UP_THRESHOLD:
            new_state = "up"
        else:
            new_state = "facing"  # in-between zone, keep as facing

        old_state = self._state["head_state"]
        old_start = self._state["head_state_start"]

        if new_state != old_state:
            # Finalize old state event if it was non-facing
            if old_state != "facing" and old_start:
                duration_ms = int((ts - old_start) * 1000)
                if old_state in ("turned_left", "turned_right"):
                    direction = "left" if old_state == "turned_left" else "right"
                    ev = _make_event(AtomicEventType.HEAD_TURNED, self.session_id, old_start, 0.9,
                                     {"direction": direction, "angle_deg": abs(yaw), "duration_ms": duration_ms})
                    ev.finalize(ts)
                    self._emit(ev)
                elif old_state == "down":
                    ev = _make_event(AtomicEventType.HEAD_DOWN, self.session_id, old_start, 0.9,
                                     {"angle_deg": abs(pitch), "duration_ms": duration_ms})
                    ev.finalize(ts)
                    self._emit(ev)
                elif old_state == "up":
                    ev = _make_event(AtomicEventType.HEAD_UP, self.session_id, old_start, 0.9,
                                     {"angle_deg": abs(pitch), "duration_ms": duration_ms})
                    ev.finalize(ts)
                    self._emit(ev)

            self._state["head_state"] = new_state
            self._state["head_state_start"] = ts

        if new_state == "facing":
            self._emit(_make_event(AtomicEventType.HEAD_FACING_SCREEN, self.session_id, ts, 0.9,
                                   {"yaw": yaw, "pitch": pitch}))

    # ── A4. Facial Expression ─────────────────────────────────────────────────

    _EXPR_MAP = {
        "neutral": AtomicEventType.EXPR_NEUTRAL,
        "happy": AtomicEventType.EXPR_HAPPY,
        "surprise": AtomicEventType.EXPR_SURPRISE,
        "sad": AtomicEventType.EXPR_SAD,
        "angry": AtomicEventType.EXPR_ANGRY,
        "fear": AtomicEventType.EXPR_FEAR,
        "disgust": AtomicEventType.EXPR_DISGUST,
    }

    def _process_expression(self, frame: FeatureFrame, ts: float) -> None:
        expr = _expression(frame)
        if not expr:
            return
        dominant = max(expr, key=lambda k: expr[k])
        conf = expr[dominant]
        if conf < 0.5:
            return
        etype = self._EXPR_MAP.get(dominant)
        if etype and dominant != self._state["expr"]:
            self._emit(_make_event(etype, self.session_id, ts, conf, {"probabilities": expr}))
            self._state["expr"] = dominant

    # ── A5. Body & Hands ─────────────────────────────────────────────────────

    def _process_body_hands(self, frame: FeatureFrame, ts: float) -> None:
        hands = _hands(frame)
        face_bbox = _face_info(frame).get("bbox", {})
        mouth_ratio = _mouth_open_ratio(frame)
        pose = _pose(frame)

        # Hand near face
        self._check_hand_near_face(hands, face_bbox, ts)

        # Hand writing (head down + hand moving at bottom of frame)
        self._check_hand_writing(frame, hands, ts)

        # Phone likely
        self._check_phone_likely(frame, hands, ts)

        # Mouth / yawn
        self._check_mouth(mouth_ratio, frame, ts)

        # Lean forward / back
        self._check_lean(pose, ts)

        # Talking likely
        self._check_talking(mouth_ratio, frame, ts)

    def _check_hand_near_face(self, hands: dict, face_bbox: dict, ts: float) -> None:
        face_cx = face_bbox.get("x", 0.5) + face_bbox.get("width", 0.3) / 2
        face_cy = face_bbox.get("y", 0.3) + face_bbox.get("height", 0.4) / 2

        near = False
        which = None
        for side in ("left", "right"):
            h = hands.get(side, {})
            if not h.get("detected"):
                continue
            wrist = h.get("wrist", {})
            dx = wrist.get("x", 0) - face_cx
            dy = wrist.get("y", 0) - face_cy
            dist = (dx ** 2 + dy ** 2) ** 0.5
            if dist < settings.HAND_NEAR_FACE_THRESHOLD_PX:
                near = True
                which = side
                break

        was_near = self._state["hand_near_face"]
        if near and not was_near:
            self._state["hand_near_face"] = True
            self._state["hand_near_face_start"] = ts
        elif not near and was_near:
            start = self._state["hand_near_face_start"]
            if start:
                ev = _make_event(AtomicEventType.HAND_NEAR_FACE, self.session_id, start, 0.85,
                                 {"which_hand": which, "duration_ms": int((ts - start) * 1000)})
                ev.finalize(ts)
                self._emit(ev)
            self._state["hand_near_face"] = False
            self._state["hand_near_face_start"] = None

    def _check_hand_writing(self, frame: FeatureFrame, hands: dict, ts: float) -> None:
        yaw, pitch, _ = _head_pose(frame)
        head_down = pitch < settings.HEAD_PITCH_DOWN_THRESHOLD
        gaze_down = _gaze_direction(frame) in ("down",)
        any_hand_low = any(
            hands.get(s, {}).get("wrist", {}).get("y", 0) > 0.6
            for s in ("left", "right")
            if hands.get(s, {}).get("detected")
        )
        writing_now = head_down and any_hand_low and gaze_down

        if writing_now and not self._state["hand_writing"]:
            self._emit(_make_event(AtomicEventType.HAND_WRITING, self.session_id, ts, 0.75))
        self._state["hand_writing"] = writing_now

    def _check_phone_likely(self, frame: FeatureFrame, hands: dict, ts: float) -> None:
        gaze_dir = _gaze_direction(frame)
        head_down = _head_pose(frame)[1] < settings.HEAD_PITCH_DOWN_THRESHOLD
        any_hand_mid = any(
            0.3 < hands.get(s, {}).get("wrist", {}).get("y", 0) < 0.7
            for s in ("left", "right")
            if hands.get(s, {}).get("detected")
        )
        if head_down and gaze_dir == "down" and any_hand_mid:
            self._emit(_make_event(AtomicEventType.HAND_HOLDING_PHONE_LIKELY, self.session_id, ts, 0.65))

    def _check_mouth(self, ratio: float, frame: FeatureFrame, ts: float) -> None:
        was_open = self._state["mouth_open"]
        open_now = ratio > settings.MOUTH_OPEN_THRESHOLD

        if open_now and not was_open:
            self._state["mouth_open_start"] = ts
            self._state["mouth_open"] = True
        elif not open_now and was_open:
            start = self._state["mouth_open_start"]
            if start:
                dur = int((ts - start) * 1000)
                if dur >= settings.MOUTH_OPEN_MIN_MS:
                    avg_ear = _avg_ear(frame)
                    eyes_closed = avg_ear < settings.EAR_BLINK_THRESHOLD
                    if eyes_closed and dur >= settings.YAWN_MIN_MS:
                        ev = _make_event(AtomicEventType.YAWN, self.session_id, start, 0.8,
                                         {"duration_ms": dur})
                        ev.finalize(ts)
                        self._emit(ev)
                        self._state["yawn_times"].append(ts)
                    else:
                        ev = _make_event(AtomicEventType.MOUTH_OPEN_WIDE, self.session_id, start, 0.8,
                                         {"duration_ms": dur})
                        ev.finalize(ts)
                        self._emit(ev)
            self._state["mouth_open"] = False

    def _check_lean(self, pose: dict, ts: float) -> None:
        if not pose.get("detected"):
            return
        shoulder_z = (pose.get("left_shoulder_z", 0.0) + pose.get("right_shoulder_z", 0.0)) / 2.0
        baseline_z = self._state["lean_baseline_z"]
        if baseline_z is None:
            self._state["lean_baseline_z"] = shoulder_z
            return
        ratio = (baseline_z - shoulder_z) / (abs(baseline_z) + 1e-6)
        thresh = settings.LEAN_THRESHOLD_RATIO

        if ratio > thresh:
            new_lean = "forward"
        elif ratio < -thresh:
            new_lean = "back"
        else:
            new_lean = "neutral"

        old_lean = self._state["lean_state"]
        if new_lean != old_lean:
            if new_lean == "forward":
                self._emit(_make_event(AtomicEventType.LEAN_FORWARD, self.session_id, ts, 0.75))
            elif new_lean == "back":
                self._emit(_make_event(AtomicEventType.LEAN_BACK, self.session_id, ts, 0.75))
            self._state["lean_state"] = new_lean

    def _check_talking(self, mouth_ratio: float, frame: FeatureFrame, ts: float) -> None:
        # Mouth moving but not a yawn and not eyes closed
        avg_ear = _avg_ear(frame)
        eyes_open = avg_ear >= settings.EAR_BLINK_THRESHOLD
        mouth_moving = mouth_ratio > settings.MOUTH_OPEN_THRESHOLD * 0.5
        yawn_likely = mouth_ratio > settings.MOUTH_OPEN_THRESHOLD and not eyes_open

        talking_now = mouth_moving and eyes_open and not yawn_likely
        was_talking = self._state["talking"]
        if talking_now and not was_talking:
            self._emit(_make_event(AtomicEventType.TALKING_LIKELY, self.session_id, ts, 0.6))
        self._state["talking"] = talking_now

    def _process_phone_detected(self, frame: FeatureFrame, ts: float) -> None:
        now = frame.get("phone_detected", False)
        was = self._state["phone_detected"]
        if now and not was:
            self._state["phone_detected_start"] = ts
            self._emit(_make_event(AtomicEventType.HAND_HOLDING_PHONE_LIKELY,
                                   self.session_id, ts, 0.9,
                                   {"source": "object_detector"}))
        elif not now and was:
            self._state["phone_detected_start"] = None
        self._state["phone_detected"] = now

    def get_current_state(self) -> dict[str, Any]:
        """Returns a snapshot of current atomic states for composite inference."""
        return {
            "face_present": self._state["face_present"],
            "multiple_faces": self._state["multiple_faces"],
            "gaze_on_screen": self._state["gaze_on_screen"],
            "gaze_direction": self._state.get("gaze_direction", "center"),
            "eye_state": self._state["eye_state"],
            "eye_state_duration_ms": (
                int((time.time() - self._state["eye_state_start"]) * 1000)
                if self._state["eye_state_start"] else 0
            ),
            "low_ear_duration_ms": (
                int((time.time() - self._state["low_ear_start"]) * 1000)
                if self._state["low_ear_start"] else 0
            ),
            "head_state": self._state["head_state"],
            "head_state_duration_ms": (
                int((time.time() - self._state["head_state_start"]) * 1000)
                if self._state["head_state_start"] else 0
            ),
            "hand_near_face": self._state["hand_near_face"],
            "hand_near_face_duration_ms": (
                int((time.time() - self._state["hand_near_face_start"]) * 1000)
                if self._state["hand_near_face_start"] else 0
            ),
            "hand_writing": self._state["hand_writing"],
            "lean_state": self._state["lean_state"],
            "expr": self._state["expr"],
            "talking": self._state["talking"],
            "yawn_times": self._state["yawn_times"],
            "head_roll": self._state.get("head_roll", 0.0),
            "gaze_off_duration_ms": (
                int((time.time() - self._state["gaze_off_start"]) * 1000)
                if self._state["gaze_off_start"] else 0
            ),
            "phone_detected": self._state["phone_detected"],
            "phone_detected_duration_ms": (
                int((time.time() - self._state["phone_detected_start"]) * 1000)
                if self._state["phone_detected_start"] else 0
            ),
        }
