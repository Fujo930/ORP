"""Tests for ORP experience builder"""

from orp.schema import TimelineEvent
from orp.experience import ExperienceBuilder, Redactor, EvidenceLinker


def test_from_events():
    builder = ExperienceBuilder()
    events = [
        TimelineEvent(kind="observation", content="Test failed", source="tool"),
        TimelineEvent(kind="claim", content="Bug found", source="agent"),
    ]
    record = builder.from_events(events, goal="Fix bug", agent_id="test-agent")
    assert record.agent["id"] == "test-agent"
    assert record.task["goal"] == "Fix bug"
    assert len(record.timeline) == 2


def test_from_trace():
    builder = ExperienceBuilder()
    trace = {
        "agent_version": "1.0",
        "model": "gpt-4",
        "goal": "Fix login",
        "events": [
            {"kind": "observation", "source": "tool", "content": "Error: 500"},
            {"kind": "action", "source": "agent", "content": "Checking logs"},
        ],
    }
    record = builder.from_trace(trace, agent_id="test")
    assert record.agent["version"] == "1.0"
    assert record.task["goal"] == "Fix login"
    assert len(record.timeline) == 2


def test_redactor():
    builder = ExperienceBuilder()
    record = builder.from_events(
        [TimelineEvent(kind="observation", content="api_key=sk-12345", source="tool")],
    )
    redacted = Redactor.apply(record)
    assert "sk-12345" not in redacted.timeline[0].content
    assert "REDACTED" in redacted.timeline[0].content


def test_evidence_linker():
    builder = ExperienceBuilder()
    record = builder.from_events([
        TimelineEvent(kind="observation", content="test", source="tool",
                      evidence_refs=["ref_a", "ref_a", "ref_b"]),
    ])
    linked = EvidenceLinker.link(record)
    # ref_a should only appear once
    assert len(linked.timeline[0].evidence_refs) == 2
