
import tempfile
from pathlib import Path
from orp.schema import Lesson, LessonStatus, EvaluationMethod
from orp.storage import ORPStorage
from orp.effects import EffectEvaluator


def _mk(storage, lid="l1", retrieved=10, applied=8, successes=7):
    l = Lesson(
        lesson_id=lid,
        recommendation="Test auth paths",
        trigger={"domain": "coding", "conditions": ["modify auth"]},
        metrics={"retrieved": retrieved, "delivered": applied,
                 "acknowledged": applied, "applied": applied,
                 "successful_after_apply": successes, "estimated_effect": None},
        status=LessonStatus.ACTIVE,
    )
    storage.save_lesson(l)
    return l


def test_describe_evaluation():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        lesson = _mk(s)
        ev = EffectEvaluator(s)
        evaluation = ev.describe(lesson)
        assert evaluation.method == EvaluationMethod.DESCRIPTIVE
        assert evaluation.decision == "keep_active"
        s.close()


def test_matched_baseline_positive():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        lesson = _mk(s, applied=20, successes=16)
        ev = EffectEvaluator(s)
        evaluation = ev.evaluate_matched_baseline(lesson, baseline_success_rate=0.50)
        assert evaluation.results["estimated_effect"] > 0
        s.close()


def test_matched_baseline_negative():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        lesson = _mk(s, applied=20, successes=3)
        ev = EffectEvaluator(s)
        evaluation = ev.evaluate_matched_baseline(lesson, baseline_success_rate=0.50)
        assert evaluation.results["estimated_effect"] < 0
        s.close()


def test_auto_evaluate_all():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        _mk(s, "la", retrieved=5, applied=4, successes=4)
        _mk(s, "lb", retrieved=5, applied=4, successes=1)
        ev = EffectEvaluator(s)
        results = ev.auto_evaluate_all()
        assert len(results) == 2
        s.close()
