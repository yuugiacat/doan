import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.analytics.composite_inferrer import CompositeInferrer
from app.services.analytics.vocabulary import CompositeEventType
import time


def _state(**kwargs):
    base = {
        "face_present": True,
        "multiple_faces": False,
        "gaze_on_screen": True,
        "gaze_direction": "center",
        "eye_state": "open",
        "eye_state_duration_ms": 0,
        "head_state": "facing",
        "head_state_duration_ms": 0,
        "hand_near_face": False,
        "hand_near_face_duration_ms": 0,
        "hand_writing": False,
        "lean_state": "neutral",
        "expr": "neutral",
        "talking": False,
        "yawn_times": [],
    }
    base.update(kwargs)
    return base


def test_taking_notes():
    inf = CompositeInferrer("s1")
    s = _state(head_state="down", hand_writing=True, eye_state="open")
    events = inf.infer(s, time.time())
    active = inf.get_active_composites()
    assert CompositeEventType.TAKING_NOTES.value in active


def test_taking_notes_not_when_eyes_closed():
    inf = CompositeInferrer("s2")
    s = _state(head_state="down", hand_writing=True, eye_state="closed")
    inf.infer(s, time.time())
    active = inf.get_active_composites()
    assert CompositeEventType.TAKING_NOTES.value not in active


def test_drowsy_from_eyes_closed():
    inf = CompositeInferrer("s3")
    s = _state(eye_state="closed", eye_state_duration_ms=3000)
    inf.infer(s, time.time())
    active = inf.get_active_composites()
    assert CompositeEventType.DROWSY.value in active


def test_drowsy_from_eyes_closed_fires_fast():
    # Ngưỡng mới 1.2s — chỉ 1.5s nhắm mắt là đã DROWSY
    inf = CompositeInferrer("s3b")
    s = _state(eye_state="closed", eye_state_duration_ms=1500)
    inf.infer(s, time.time())
    assert CompositeEventType.DROWSY.value in inf.get_active_composites()


def test_drowsy_from_lim_dim_eyes():
    # Mắt lim dim (chưa nhắm hẳn, EAR thấp) ≥4s → DROWSY
    inf = CompositeInferrer("s3c")
    s = _state(eye_state="blinking", low_ear_duration_ms=4500)
    inf.infer(s, time.time())
    assert CompositeEventType.DROWSY.value in inf.get_active_composites()


def test_drowsy_from_head_down_dozy():
    # Đầu cúi 7s + mắt sụp mí 2s + không viết → ngủ gục
    inf = CompositeInferrer("s3d")
    s = _state(
        head_state="down",
        head_state_duration_ms=7000,
        low_ear_duration_ms=2000,
        hand_writing=False,
    )
    inf.infer(s, time.time())
    assert CompositeEventType.DROWSY.value in inf.get_active_composites()


def test_not_drowsy_when_writing():
    # Đầu cúi + mắt sụp mí NHƯNG đang viết → KHÔNG phải ngủ gục
    inf = CompositeInferrer("s3e")
    s = _state(
        head_state="down",
        head_state_duration_ms=7000,
        low_ear_duration_ms=2000,
        hand_writing=True,
        eye_state="open",       # tránh các rule drowsy khác
        eye_state_duration_ms=0,
    )
    inf.infer(s, time.time())
    assert CompositeEventType.DROWSY.value not in inf.get_active_composites()


def test_phone_distraction():
    # Ngưỡng mới: 30s (30_000ms) đầu cúi liên tục → điện thoại
    inf = CompositeInferrer("s4")
    s = _state(
        head_state="down",
        gaze_on_screen=False,
        gaze_direction="down",
        hand_writing=False,
        head_state_duration_ms=31_000,  # 31s > 30s threshold
    )
    inf.infer(s, time.time())
    active = inf.get_active_composites()
    assert CompositeEventType.PHONE_DISTRACTION.value in active


def test_reading_materials_short_head_down():
    # Cúi đầu < 30s → đọc sách/tài liệu (KHÔNG phải điện thoại)
    inf = CompositeInferrer("s4b")
    s = _state(
        head_state="down",
        face_present=True,
        eye_state="open",
        hand_writing=False,
        head_state_duration_ms=5_000,   # 5s → reading_materials
    )
    inf.infer(s, time.time())
    active = inf.get_active_composites()
    assert CompositeEventType.READING_MATERIALS.value in active
    assert CompositeEventType.PHONE_DISTRACTION.value not in active


def test_phone_NOT_when_writing():
    inf = CompositeInferrer("s5")
    s = _state(
        head_state="down",
        gaze_on_screen=False,
        gaze_direction="down",
        hand_writing=True,   # <-- writing, not phone
        head_state_duration_ms=31_000,
    )
    inf.infer(s, time.time())
    active = inf.get_active_composites()
    assert CompositeEventType.PHONE_DISTRACTION.value not in active


def test_looking_away():
    inf = CompositeInferrer("s6")
    s = _state(
        head_state="turned_left",
        head_state_duration_ms=5500,   # > ngưỡng mới 5s
    )
    inf.infer(s, time.time())
    active = inf.get_active_composites()
    assert CompositeEventType.LOOKING_AWAY.value in active


def test_away_from_desk():
    inf = CompositeInferrer("s7")
    s = _state(face_present=False)
    inf.infer(s, time.time())
    active = inf.get_active_composites()
    assert CompositeEventType.AWAY_FROM_DESK.value in active


def test_reading_screen():
    inf = CompositeInferrer("s8")
    s = _state(
        gaze_on_screen=True,
        head_state="facing",
        head_state_duration_ms=6000,  # > 5000ms threshold
    )
    inf.infer(s, time.time())
    active = inf.get_active_composites()
    assert CompositeEventType.READING_SCREEN.value in active


def test_head_tilt_phone():
    # Đầu nghiêng ≥35° → LOOKING_AWAY (điện thoại quay ngang)
    inf = CompositeInferrer("s9")
    s = _state(face_present=True, head_roll=40.0)
    inf.infer(s, time.time())
    active = inf.get_active_composites()
    assert CompositeEventType.LOOKING_AWAY.value in active


def test_sustained_distraction_becomes_phone():
    # Sao nhãng liên tục ≥60s → PHONE_DISTRACTION
    inf = CompositeInferrer("s10")
    t0 = time.time()
    s = _state(head_state="turned_left", head_state_duration_ms=5500)
    # Gọi frame đầu tiên để bắt đầu tracking
    inf.infer(s, t0)
    # Gọi frame sau 61 giây
    inf.infer(s, t0 + 61.0)
    active = inf.get_active_composites()
    assert CompositeEventType.PHONE_DISTRACTION.value in active


def test_sustained_distraction_resets_on_focus():
    # Khi tập trung trở lại → bộ đếm reset, không còn phone distraction
    inf = CompositeInferrer("s11")
    t0 = time.time()
    s_distracted = _state(head_state="turned_left", head_state_duration_ms=4000)
    inf.infer(s_distracted, t0)
    inf.infer(s_distracted, t0 + 30.0)
    # Trở lại tập trung
    s_focused = _state(head_state="facing", head_state_duration_ms=2000, gaze_on_screen=True)
    inf.infer(s_focused, t0 + 31.0)
    # 60s nữa vẫn focused → không có phone distraction
    inf.infer(s_focused, t0 + 91.0)
    active = inf.get_active_composites()
    assert CompositeEventType.PHONE_DISTRACTION.value not in active
