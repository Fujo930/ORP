#!/usr/bin/env python3
"""
ORP + Agent Integration Demo
Shows how any AI coding agent integrates with ORP via MCP.

Run: uv run python demo_agent_integration.py
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orp.schema import (
    ExperienceRecord, TimelineEvent, Outcome, EventKind,
    Lesson, LessonStatus, DeliveryStrategy,
)
from orp.storage import ORPStorage
from orp.compiler import ExperienceCompiler
from orp.delivery import DeliveryRouter
from orp.mcp_server import MCPServer


def simulate_agent_task(task: str, use_orp: bool) -> dict:
    """
    Simulate a coding agent performing a task.
    When use_orp=True, the agent queries ORP for lessons first.
    """
    steps = []
    if use_orp:
        steps.append("[MCP] orp_retrieve_lessons(task, limit=3)")
        steps.append("[MCP] Got 1 lesson: Test auth paths")
        steps.append("[MCP] orp_acknowledge_lesson(lesson_id)")
        steps.append("Applied lesson: wrote anonymous-user regression test")
        steps.append("Ran tests: 35 passed, 0 failed")
        return {"success": True, "passed": 35, "failed": 0, "steps": steps,
                "lesson_used": True}
    else:
        steps.append("Modified UserController.java directly")
        steps.append("Ran tests: 34 passed, 1 failed (anonymous-user)")
        return {"success": False, "passed": 34, "failed": 1, "steps": steps,
                "lesson_used": False}


def main():
    print("=" * 66)
    print("  ORP + AI Agent Integration Demo")
    print("  Shows the agent-side interaction with ORP MCP tools")
    print("=" * 66)

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = ORPStorage(base_dir=tmpdir)
        task = "Fix authentication controller"

        # ── Phase 1: First run (fails) ──────────────────────
        print("\n[Phase 1] Agent runs WITHOUT ORP -> FAILS")
        run1 = simulate_agent_task(task, use_orp=False)
        exp1 = ExperienceRecord(
            agent={"id": "demo-agent", "model": "gpt-4"},
            task={"goal": task, "domain": "coding"},
            timeline=[
                TimelineEvent(kind="observation",
                    content=f"pytest: {run1['passed']} passed, {run1['failed']} failed",
                    source="tool"),
                TimelineEvent(kind="observation",
                    content="FAILED test_anonymous_user_access",
                    source="tool"),
                TimelineEvent(kind="claim",
                    content="The authentication fix is complete",
                    source="agent"),
            ],
            outcome=Outcome(status="failed"),
        )
        storage.save_experience(exp1)
        for s in run1["steps"]:
            print(f"  {s}")

        # ── Phase 2: ORP processes the failure ──────────────
        print("\n[Phase 2] ORP processes the failure")
        compiler = ExperienceCompiler()
        arts = compiler.compile(exp1)
        lesson = arts["lessons"][0]
        lesson.status = LessonStatus.ACTIVE
        lesson.recommendation = "Test anonymous, authenticated, and forbidden paths"
        lesson.scope = {"task_domains": ["coding"], "frameworks": [],
                        "agent_versions": []}
        storage.save_lesson(lesson)
        print(f"  ORP generated Lesson: {lesson.recommendation}")

        # ── Phase 3: Agent integration pattern ──────────────
        print("\n[Phase 3] Agent integration pattern")
        print("  ┌─────────────────────────────────────────────────────┐")
        print("  │  MCP Tool: orp_retrieve_lessons                      │")
        print("  │  Request:  {'task': 'Fix authentication'}            │")
        print("  │  Response: [{'lesson_id': '...',                     │")
        print("  │              'recommendation': 'Test auth paths'}]   │")
        print("  └─────────────────────────────────────────────────────┘")

        # Simulate agent calling MCP
        mcp = MCPServer(storage)
        result = mcp.handle_call("orp_retrieve_lessons",
                                 {"task": task, "limit": 3})
        print(f"\n  >> Agent queries MCP: found {result['count']} lesson(s)")
        for r in result["lessons"]:
            print(f"     -> {r['recommendation']}")
        mcp.handle_call("orp_acknowledge_lesson",
                        {"lesson_id": lesson.lesson_id})
        print("  >> Agent acknowledges lesson")

        # ── Phase 4: Second run (succeeds) ───────────────────
        print("\n[Phase 4] Agent runs WITH ORP -> SUCCEEDS")
        run2 = simulate_agent_task(task, use_orp=True)
        for s in run2["steps"]:
            print(f"  {s}")

        # Report outcome
        mcp.handle_call("orp_report_outcome",
                        {"lesson_id": lesson.lesson_id,
                         "outcome": "success",
                         "evidence_refs": ["pytest:35-passed"]})
        print("\n  >> Agent reports outcome via MCP")

        # ── Summary ─────────────────────────────────────────
        print("\n" + "=" * 66)
        print("  Result")
        print("=" * 66)
        print(f"\n  Without ORP: 34/35 FAILED")
        print(f"  With ORP:    35/35 PASSED")
        print(f"  Lesson applied: Yes")
        print(f"  Lesson status: active (verified)")
        print(f"\n  Integration pattern:")
        print(f"  1. Start task: call orp_retrieve_lessons")
        print(f"  2. Apply lesson: call orp_acknowledge_lesson")
        print(f"  3. End task: call orp_report_outcome")
        print(f"\n  To integrate your own agent:")
        print(f"  - Codex:     add config to ~/.codex/config.toml")
        print(f"  - Claude:    add config to ~/.claude/settings.json")
        print(f"  - Custom:    use the MCP server or CLI directly")
        print()

        storage.close()


if __name__ == "__main__":
    main()
