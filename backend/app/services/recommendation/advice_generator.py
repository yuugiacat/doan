"""
Advice Generator — produces post-session personalized advice based on patterns.
"""
from __future__ import annotations

from typing import Any


_ADVICE_RULES: list[tuple[str, float, str]] = [
    # (distraction_cause, distracted_pct_threshold, advice_text)
    (
        "drowsy",
        10.0,
        "Bạn có nhiều lúc buồn ngủ trong phiên học này. Hãy đảm bảo ngủ đủ giấc (7-8 tiếng) "
        "và thử học vào buổi sáng khi năng lượng cao hơn.",
    ),
    (
        "phone_distraction",
        5.0,
        "Điện thoại làm bạn sao nhãng khá nhiều. Hãy để điện thoại ở xa hoặc bật chế độ 'Không làm phiền' "
        "trước khi bắt đầu học.",
    ),
    (
        "looking_away",
        10.0,
        "Ánh mắt của bạn thường xuyên rời khỏi màn hình. Hãy tìm góc học yên tĩnh, ít xao nhãng hơn.",
    ),
    (
        "talking_to_someone",
        5.0,
        "Bạn thường bị gián đoạn bởi việc nói chuyện. Hãy học ở không gian riêng tư hoặc đặt giờ "
        "học cố định để người khác không làm phiền.",
    ),
    (
        "away_from_desk",
        5.0,
        "Bạn rời chỗ nhiều lần trong phiên học. Hãy chuẩn bị đầy đủ (nước uống, tài liệu) trước khi ngồi học.",
    ),
]

_GENERIC_POSITIVE = (
    "Tuyệt vời! Bạn đã duy trì sự tập trung rất tốt trong phiên học này. "
    "Tiếp tục phát huy nhé!"
)

_GENERIC_IMPROVE = (
    "Phiên học này có một số lúc mất tập trung. Hãy thử kỹ thuật Pomodoro: "
    "25 phút học tập trung, 5 phút nghỉ — để duy trì năng lượng tốt hơn."
)


def generate_advice(analysis: dict[str, Any]) -> list[str]:
    advice_list: list[str] = []

    distracted_pct: float = analysis.get("distracted_pct", 0.0) + analysis.get("drowsy_pct", 0.0)
    cause_counts: dict[str, int] = analysis.get("distraction_cause_counts", {})
    total_events = sum(cause_counts.values()) or 1

    for cause_key, threshold, advice in _ADVICE_RULES:
        matching = sum(
            v for k, v in cause_counts.items()
            if cause_key in k
        )
        if matching / total_events * 100 >= threshold or (
            cause_key == "drowsy" and analysis.get("drowsy_pct", 0) >= threshold
        ):
            advice_list.append(advice)

    if not advice_list:
        if distracted_pct < 10:
            advice_list.append(_GENERIC_POSITIVE)
        else:
            advice_list.append(_GENERIC_IMPROVE)

    return advice_list
