"""Tests for ORP compiler"""

from orp.schema import (
    ExperienceRecord, TimelineEvent, Outcome,
)
from orp.compiler import ExperienceCompiler


def test_compile_failed_experience():
    """Test compiling a failed experience generates lesson + eval"""
    record = ExperienceRecord(
        agent={"id": "test-agent"},
        task={"goal": "Fix auth bug", "domain": "coding"},
        timeline=[
            TimelineEvent(kind="observation", content="pytest: 1 failed", source="tool"),
            TimelineEvent(kind="claim", content="The fix is complete", source="agent"),
        ],
        outcome=Outcome(status="failed", objective_signals=[{"name": "exit_code", "value": 1}]),
    )
    compiler = ExperienceCompiler()
    artifacts = compiler.compile(record)
    
    assert len(artifacts["lessons"]) >= 1
    assert len(artifacts["evals"]) >= 1
    assert len(record.artifacts["lessons"]) >= 1


def test_compile_success_experience():
    """Test compiling a successful experience"""
    record = ExperienceRecord(
        agent={"id": "test-agent"},
        task={"goal": "Simple task", "domain": "coding"},
        timeline=[TimelineEvent(kind="observation", content="all good", source="tool")],
        outcome=Outcome(status="success"),
    )
    compiler = ExperienceCompiler()
    artifacts = compiler.compile(record)
    # Success shouldn't generate lessons
    assert len(artifacts["lessons"]) == 0
