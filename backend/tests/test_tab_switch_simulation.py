"""
Simulation test: chứng minh fix bug "chuyển tab bị trừ điểm" hoạt động.

Kịch bản: user đầu cúi viết bài ở T0, đổi tab 2 phút (camera ngừng gửi frame),
quay lại tab. Pre-fix: head_state_duration_ms = 120s do dùng time.time().
Post-fix: duration đứng yên cho đến khi frame mới đến.
"""
from app.services.analytics.atomic_encoder import AtomicEncoder


def _frame(ts: float, *, head_pitch: float = -20.0, head_yaw: float = 0.0) -> dict:
    return {
        "timestamp": ts,
        "face": {"detected": True, "count": 1, "confidence": 0.95,
                 "bbox": {"x": 0.3, "y": 0.2, "width": 0.4, "height": 0.5}},
        "head_pose": {"yaw": head_yaw, "pitch": head_pitch, "roll": 0.0},
        "gaze": {"on_screen": True, "direction": "down",
                 "confidence": 0.85, "ear_left": 0.3, "ear_right": 0.3},
        "hands": {"left":  {"detected": False, "wrist": {"x": 0, "y": 0}},
                  "right": {"detected": False, "wrist": {"x": 0, "y": 0}}},
        "expression": {"neutral": 0.9, "happy": 0.05, "surprise": 0.01,
                       "sad": 0.01, "angry": 0.01, "fear": 0.01, "disgust": 0.01},
        "pose": {"detected": False, "left_shoulder_z": 0, "right_shoulder_z": 0},
        "mouth_open_ratio": 0.0,
        "phone_detected": False,
    }


def test_duration_uses_frame_ts_not_wallclock():
    """Khi không có frame mới, duration_ms KHÔNG được phép tăng theo wall clock."""
    enc = AtomicEncoder("test-session")

    # T0: frame đầu — đầu cúi (head_state → "down")
    enc.process(_frame(ts=1000.0))
    state_after_first = enc.get_current_state()
    assert state_after_first["head_state"] == "down"
    # Duration ≈ 0 vì vừa mới chuyển state
    assert state_after_first["head_state_duration_ms"] <= 10

    # Mô phỏng tab ẩn 2 phút — KHÔNG có frame mới gọi đến process()
    # Trước fix: get_current_state() sẽ dùng time.time() → duration tăng vô tội vạ
    # Sau fix: dùng self._last_frame_ts → duration đứng yên
    state_during_hidden = enc.get_current_state()
    assert state_during_hidden["head_state_duration_ms"] == state_after_first["head_state_duration_ms"], (
        f"Duration tăng giả khi tab ẩn: {state_during_hidden['head_state_duration_ms']}ms"
    )

    # T0 + 120s: frame mới đến (user quay lại tab, vẫn cúi đầu)
    enc.process(_frame(ts=1120.0))
    state_after_return = enc.get_current_state()
    assert state_after_return["head_state"] == "down"
    # Bây giờ duration mới = 120s — đúng đắn vì frame ts thật sự cách 120s
    assert state_after_return["head_state_duration_ms"] == 120_000


def test_duration_does_not_trigger_false_distraction_during_hidden_gap():
    """
    Composite inferrer check head_state_duration_ms ≥ 5000ms → LOOKING_AWAY.
    Trước fix: gap 2 phút khi tab ẩn sẽ trigger LOOKING_AWAY ngay lập tức.
    Sau fix: chỉ trigger khi thật sự có frame quay đầu liên tục 5s.
    """
    from app.services.analytics.composite_inferrer import CompositeInferrer
    from app.services.analytics.vocabulary import CompositeEventType

    enc = AtomicEncoder("test-session")
    inf = CompositeInferrer("test-session")

    # T0: user quay đầu sang phải (yaw lớn, head_state → "turned_right")
    enc.process(_frame(ts=1000.0, head_pitch=0.0, head_yaw=30.0))
    state = enc.get_current_state()
    assert state["head_state"] == "turned_right"

    # Mô phỏng tab ẩn 2 phút — không có frame.
    # Nếu vẫn dùng time.time(), get_current_state() lúc này sẽ trả về
    # head_state_duration_ms ≈ 120_000ms → LOOKING_AWAY trigger.
    # Sau fix, duration đứng yên ≈ 0 → KHÔNG trigger.
    state_during = enc.get_current_state()
    inf.infer(state_during, ts=1000.0)  # không truyền ts mới
    active = inf.get_active_composites()
    assert CompositeEventType.LOOKING_AWAY.value not in active, (
        f"False positive LOOKING_AWAY trong khi tab ẩn: {active}"
    )
