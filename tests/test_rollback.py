
import tempfile
from pathlib import Path
from orp.schema import Lesson, LessonStatus
from orp.storage import ORPStorage
from orp.rollback import RollbackManager


def test_rollback_to_under_review():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        lesson = Lesson(recommendation="T", trigger={"domain":"t","conditions":["t"]},
                        status=LessonStatus.ACTIVE)
        s.save_lesson(lesson)
        rb = RollbackManager(s).rollback(lesson.lesson_id, reason="Negative")
        assert rb is not None
        assert rb.new_status == LessonStatus.UNDER_REVIEW
        assert s.get_lesson(lesson.lesson_id).status == LessonStatus.UNDER_REVIEW
        s.close()


def test_rollback_nonexistent():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        rb = RollbackManager(s).rollback("x", reason="test")
        assert rb is None
        s.close()


def test_restore():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        lesson = Lesson(recommendation="T", trigger={"domain":"t","conditions":["t"]},
                        status=LessonStatus.UNDER_REVIEW)
        s.save_lesson(lesson)
        ok = RollbackManager(s).restore(lesson.lesson_id)
        assert ok
        assert s.get_lesson(lesson.lesson_id).status == LessonStatus.ACTIVE
        s.close()


def test_restore_non_under_review():
    with tempfile.TemporaryDirectory() as tmp:
        s = ORPStorage(base_dir=Path(tmp))
        lesson = Lesson(recommendation="T", trigger={"domain":"t","conditions":["t"]},
                        status=LessonStatus.ACTIVE)
        s.save_lesson(lesson)
        assert not RollbackManager(s).restore(lesson.lesson_id)
        s.close()
