"""Tests for ORP schema"""

from datetime import datetime, timezone
from orp.schema import (
    ExperienceRecord, TimelineEvent, EventKind, Lesson,
    LessonStatus, EvalArtifact, CounterfactualReplay,
    LessonDelivery, LessonEvaluation, LessonRollback,
    TrainingCandidate, Outcome, ReflectionAnalysis,
    check_lesson_conflict,
)


def test_create_experience_record():
    """Test creating a basic ExperienceRecord"""
    record = ExperienceRecord(
        agent={"id": "test-agent"},
        task={"goal": "Fix anonymous user access", "domain": "coding"},
        timeline=[
            TimelineEvent(kind="observation", content="Test failed", source="tool",
                          evidence_refs=["artifact:test-output"]),
            TimelineEvent(kind="claim", content="Root cause is null pointer",
                          source="agent"),
        ],
        outcome=Outcome(status="failed", objective_signals=[{"name": "exit_code", "value": 1}]),
    )
    assert record.orp_version == "0.3"
    assert record.experience_id.startswith("exp_")
    assert len(record.timeline) == 2
    assert record.outcome.status == "failed"


def test_timeline_event_kinds():
    """Test all event kinds"""
    for kind in EventKind:
        evt = TimelineEvent(kind=kind.value, content=f"test {kind.value}")
        assert evt.kind == kind
        assert evt.content == f"test {kind.value}"


def test_lesson_lifecycle():
    """Test Lesson status transitions"""
    lesson = Lesson(
        recommendation="Test anonymous, authenticated, and forbidden paths",
        trigger={"domain": "coding", "conditions": ["modify auth logic"]},
        scope={"task_domains": ["coding"], "frameworks": [], "agent_versions": []},
    )
    assert lesson.status == LessonStatus.CANDIDATE
    
    lesson.status = LessonStatus.ACTIVE
    assert lesson.status == LessonStatus.ACTIVE
    
    lesson.status = LessonStatus.DEPRECATED
    assert lesson.status == LessonStatus.DEPRECATED


def test_experience_timeline_not_empty():
    """Test timeline must have at least one event"""
    try:
        ExperienceRecord(
            agent={"id": "test"},
            task={"goal": "test"},
            timeline=[],
        )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Timeline must have at least one event" in str(e)


def test_lesson_scope_validation():
    """Test validate_lesson_scope"""
    from orp.schema import validate_lesson_scope
    
    # Missing scope
    lesson = Lesson(recommendation="test", trigger={})
    issues = validate_lesson_scope(lesson)
    assert len(issues) >= 1
    
    # Complete scope
    lesson = Lesson(
        recommendation="test",
        trigger={"domain": "coding", "conditions": ["test"]},
        scope={"task_domains": ["coding"], "frameworks": [], "agent_versions": []},
    )
    issues = validate_lesson_scope(lesson)
    assert len(issues) == 0


def test_conflict_detection():
    """Test check_lesson_conflict"""
    a = Lesson(
        recommendation="Always write tests first",
        scope={"task_domains": ["coding"], "frameworks": [], "agent_versions": []},
    )
    b = Lesson(
        recommendation="Never write tests before code",
        scope={"task_domains": ["research"], "frameworks": [], "agent_versions": []},
    )
    # Different domains = no conflict
    assert not check_lesson_conflict(a, b)
    
    c = Lesson(
        recommendation="Never write tests before code",
        scope={"task_domains": ["coding"], "frameworks": [], "agent_versions": []},
    )
    # Same domain = potential conflict
    assert check_lesson_conflict(a, c)


def test_counterfactual_replay():
    """Test CounterfactualReplay creation"""
    replay = CounterfactualReplay(
        experience_id="exp_test",
        original_strategy="Fix directly",
        alternative_strategy="Write test first",
        result={"status": "improved", "tests_passed": 1},
    )
    assert replay.replay_id.startswith("replay_")
    assert replay.result["status"] == "improved"


def test_delivery():
    """Test LessonDelivery"""
    from orp.schema import DeliveryStrategy
    delivery = LessonDelivery(
        lesson_id="lesson_test",
        experience_id="exp_test",
        strategy=DeliveryStrategy.MCP_TOOL,
        acknowledged=True,
        applied=True,
    )
    assert delivery.strategy == DeliveryStrategy.MCP_TOOL
    assert delivery.acknowledged
    assert delivery.applied


def test_training_candidate():
    """Test TrainingCandidate"""
    from orp.schema import TrainingFormat, TrainingStatus
    tc = TrainingCandidate(
        source_experience_ids=["exp_01"],
        format=TrainingFormat.SFT_EXAMPLE,
    )
    assert tc.status == TrainingStatus.CANDIDATE
    assert tc.format == TrainingFormat.SFT_EXAMPLE
    assert not tc.validation["human_reviewed"]


def test_full_roundtrip():
    """Test creating, serializing, and deserializing a full experience"""
    record = ExperienceRecord(
        agent={"id": "test-agent", "version": "1.0", "model": "gpt-4"},
        task={"goal": "Fix bug", "domain": "coding", "input_ref": "sha256:abc"},
        timeline=[
            TimelineEvent(kind="observation", content="Error found", source="tool"),
            TimelineEvent(kind="claim", content="Analysis complete", source="agent"),
            TimelineEvent(kind="outcome", content="Fixed", source="system"),
        ],
        outcome=Outcome(status="success"),
        reflection=ReflectionAnalysis(diagnosis="Missing null check"),
    )
    data = record.model_dump()
    restored = ExperienceRecord(**data)
    assert restored.experience_id == record.experience_id
    assert len(restored.timeline) == 3
    assert restored.reflection is not None
    assert restored.reflection.diagnosis == "Missing null check"
