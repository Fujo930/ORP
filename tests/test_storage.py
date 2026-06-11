"""Tests for ORP storage"""

import tempfile
from pathlib import Path

from orp.schema import (
    ExperienceRecord, TimelineEvent, Lesson, LessonStatus,
    EvalArtifact, CounterfactualReplay, Outcome,
)
from orp.storage import ORPStorage


def test_save_and_get_experience():
    """Test saving and retrieving an experience"""
    with tempfile.TemporaryDirectory() as tmp:
        storage = ORPStorage(base_dir=Path(tmp))
        storage.conn.execute("PRAGMA journal_mode=WAL")
        record = ExperienceRecord(
            agent={"id": "test"},
            task={"goal": "test story", "domain": "coding"},
            timeline=[TimelineEvent(kind="observation", content="test")],
        )
        storage.save_experience(record)

        loaded = storage.get_experience(record.experience_id)
        assert loaded is not None
        assert loaded.experience_id == record.experience_id
        assert len(loaded.timeline) == 1
        storage.close()


def test_save_and_list_experiences():
    """Test listing experiences"""
    with tempfile.TemporaryDirectory() as tmp:
        storage = ORPStorage(base_dir=Path(tmp))
        storage.conn.execute("PRAGMA journal_mode=WAL")
        for i in range(3):
            record = ExperienceRecord(
                agent={"id": "test"},
                task={"goal": f"task {i}", "domain": "coding"},
                timeline=[TimelineEvent(kind="observation", content=f"event {i}")],
            )
            storage.save_experience(record)

        exps = storage.list_experiences(limit=10)
        assert len(exps) == 3
        storage.close()


def test_save_and_get_lesson():
    """Test saving and retrieving a lesson"""
    with tempfile.TemporaryDirectory() as tmp:
        storage = ORPStorage(base_dir=Path(tmp))
        storage.conn.execute("PRAGMA journal_mode=WAL")
        lesson = Lesson(
            recommendation="Always run tests",
            trigger={"domain": "coding", "conditions": ["modify code"]},
        )
        storage.save_lesson(lesson)

        loaded = storage.get_lesson(lesson.lesson_id)
        assert loaded is not None
        assert loaded.recommendation == "Always run tests"
        storage.close()


def test_list_lessons_by_status():
    """Test filtering lessons by status"""
    with tempfile.TemporaryDirectory() as tmp:
        storage = ORPStorage(base_dir=Path(tmp))
        storage.conn.execute("PRAGMA journal_mode=WAL")
        for status in [LessonStatus.CANDIDATE, LessonStatus.ACTIVE, LessonStatus.DEPRECATED]:
            lesson = Lesson(
                recommendation=f"Lesson {status.value}",
                trigger={"domain": "test", "conditions": ["test"]},
                status=status,
            )
            storage.save_lesson(lesson)

        active = storage.list_lessons(status=LessonStatus.ACTIVE)
        assert len(active) == 1
        assert active[0].status == LessonStatus.ACTIVE
        storage.close()


def test_save_eval():
    """Test saving an eval artifact"""
    with tempfile.TemporaryDirectory() as tmp:
        storage = ORPStorage(base_dir=Path(tmp))
        storage.conn.execute("PRAGMA journal_mode=WAL")
        eval_ = EvalArtifact(
            origin_experience="exp_test",
            command="pytest -q",
        )
        storage.save_eval(eval_)
        row = storage.conn.execute(
            "SELECT * FROM evals WHERE eval_id = ?", (eval_.eval_id,)
        ).fetchone()
        assert row is not None
        assert row["command"] == "pytest -q"
        storage.close()


def test_save_replay():
    """Test saving a replay"""
    with tempfile.TemporaryDirectory() as tmp:
        storage = ORPStorage(base_dir=Path(tmp))
        storage.conn.execute("PRAGMA journal_mode=WAL")
        replay = CounterfactualReplay(
            experience_id="exp_test",
            original_strategy="A",
            alternative_strategy="B",
            result={"status": "improved"},
        )
        storage.save_replay(replay)
        row = storage.conn.execute(
            "SELECT * FROM replays WHERE replay_id = ?", (replay.replay_id,)
        ).fetchone()
        assert row is not None
        storage.close()


def test_update_lesson_status():
    """Test updating lesson status"""
    with tempfile.TemporaryDirectory() as tmp:
        storage = ORPStorage(base_dir=Path(tmp))
        storage.conn.execute("PRAGMA journal_mode=WAL")
        lesson = Lesson(
            recommendation="Test",
            trigger={"domain": "test", "conditions": ["test"]},
            status=LessonStatus.CANDIDATE,
        )
        storage.save_lesson(lesson)
        storage.update_lesson_status(lesson.lesson_id, LessonStatus.ACTIVE)

        loaded = storage.get_lesson(lesson.lesson_id)
        assert loaded is not None
        assert loaded.status == LessonStatus.ACTIVE
        storage.close()
