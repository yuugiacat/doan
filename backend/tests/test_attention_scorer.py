import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.analytics.attention_scorer import AttentionScorer
from app.services.analytics.vocabulary import AttentionState
import time


def test_starts_at_100():
    scorer = AttentionScorer("s1")
    result = scorer.update(time.time(), [])
    assert result.score == 100.0


def test_neutral_stays_at_100():
    # Ngồi yên không sao nhãng → không giảm điểm, có thể tăng nhẹ
    scorer = AttentionScorer("s1")
    ts = time.time()
    for i in range(10):
        result = scorer.update(ts + i, [])
    assert result.score >= 100.0
    assert result.state == AttentionState.FOCUSED


def test_focused_stays_at_100():
    scorer = AttentionScorer("s2")
    ts = time.time()
    for i in range(10):
        result = scorer.update(ts + i, ["reading_screen"])
    assert result.score == 100.0
    assert result.state == AttentionState.FOCUSED


def test_distraction_drops_score():
    # 60 giây sao nhãng: -1.0 pt/s × 60 = -60 điểm → còn 40
    scorer = AttentionScorer("s3")
    ts = time.time()
    for i in range(60):
        result = scorer.update(ts + i, ["looking_away"])
    assert result.score < 60
    assert result.state == AttentionState.DISTRACTED


def test_sleepy_drops_score_slower():
    # 60 giây buồn ngủ: -0.5 pt/s × 60 = -30 điểm → còn 70
    scorer = AttentionScorer("s4")
    ts = time.time()
    for i in range(60):
        result = scorer.update(ts + i, ["drowsy"])
    assert result.score < 80
    assert result.state == AttentionState.SLEEPY


def test_recovery_after_distraction():
    # Sao nhãng 60s → tập trung lại, điểm phải tăng
    scorer = AttentionScorer("s5")
    ts = time.time()
    for i in range(60):
        scorer.update(ts + i, ["looking_away"])
    distracted_score = scorer.get_last_score()
    for i in range(30):
        result = scorer.update(ts + 60 + i, ["reading_screen"])
    assert result.score > distracted_score


def test_no_decrease_when_not_distracted():
    # Điểm đầu 100, không sao nhãng → không bao giờ giảm
    scorer = AttentionScorer("s6")
    ts = time.time()
    prev = 100.0
    for i in range(30):
        result = scorer.update(ts + i, [])
        assert result.score >= prev
        prev = result.score


def test_empty_composites_high_score():
    scorer = AttentionScorer("s7")
    result = scorer.update(time.time(), [])
    assert result.score >= 40


def test_history_grows():
    scorer = AttentionScorer("s8")
    ts = time.time()
    for i in range(5):
        scorer.update(ts + i, [])
    assert len(scorer.get_history()) == 5
