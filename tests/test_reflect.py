"""Tests for ORP reflection"""

from orp.schema import ExperienceRecord, TimelineEvent, Outcome, EventKind
from orp.reflect import ReflectionAnalyzer, Challenger


def test_analyze_failed_experience():
    """Test analyzing a failed experience"""
    record = ExperienceRecord(
        agent={"id": "test"},
        task={"goal": "Fix bug"},
        timeline=[
            TimelineEvent(kind="observation", content="Error: null pointer", source="tool"),
            TimelineEvent(kind="outcome", content="Failed", source="system"),
        ],
        outcome=Outcome(status="failed"),
    )
    analyzer = ReflectionAnalyzer()
    reflection = analyzer.analyze(record)
    assert reflection.diagnosis is not None
    assert reflection.diagnosis is not None and "fail" in reflection.diagnosis.lower()


def test_challenger_finds_unsupported_claims():
    """Test challenger identifies claims without evidence"""
    record = ExperienceRecord(
        agent={"id": "test"},
        task={"goal": "Fix bug"},
        timeline=[
            TimelineEvent(kind="claim", content="The fix is complete", source="agent"),
            TimelineEvent(kind="claim", content="All edge cases handled", source="agent",
                          evidence_refs=["test:result"]),
            TimelineEvent(kind="observation", content="Test passed", source="tool"),
        ],
        outcome=Outcome(status="success"),
    )
    challenger = Challenger()
    challenged = challenger.challenge(record)
    assert len(challenged) >= 1
    # The first claim has no evidence
    assert any("No evidence" in c["issue"] for c in challenged)


def test_challenger_no_false_positives():
    """Test challenger doesn't flag well-evidenced claims"""
    record = ExperienceRecord(
        agent={"id": "test"},
        task={"goal": "Fix bug"},
        timeline=[
            TimelineEvent(kind="claim", content="Verified fix", source="agent",
                          evidence_refs=["test:output", "artifact:diff"]),
        ],
        outcome=Outcome(status="success"),
    )
    challenger = Challenger()
    challenged = challenger.challenge(record)
    # Well-evidenced claim should not be challenged (2+ refs)
    assert len(challenged) == 0
