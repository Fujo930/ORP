#!/usr/bin/env python3
"""
ORP 5-Minute Demo - Give your agent a mistake once. ORP helps it prove it learned.

Usage:
    uv run python demo/orp_demo.py

Shows the full ORP pipeline:
    1. Agent fails (misses anonymous user path)
    2. ORP captures Experience, challenges claims
    3. ORP compiles Lesson + Eval
    4. MCP delivers Lesson to Agent
    5. Agent applies Lesson and succeeds
    6. EffectEvaluator measures improvement
"""

import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orp.schema import (
    ExperienceRecord, TimelineEvent, Outcome, EventKind,
    Lesson, LessonStatus, DeliveryStrategy,
)
from orp.storage import ORPStorage
from orp.reflect import ReflectionAnalyzer, Challenger
from orp.compiler import ExperienceCompiler
from orp.lessons import LessonStore
from orp.delivery import DeliveryRouter
from orp.effects import EffectEvaluator
from orp.mcp_server import MCPServer
from orp.export import ExportEngine
from orp.viewer import HTMLReporter


def simulate_run(task, apply_lesson=False):
    steps = []
    if apply_lesson:
        steps.append("[1/3] Read Lesson: must test anonymous/authenticated/admin paths")
        steps.append("[2/3] Wrote boundary tests for all three user types")
        steps.append("[3/3] Ran tests: 35 passed, 0 failed")
        passed, failed = 35, 0
    else:
        steps.append("[1/2] Modified UserController.java directly")
        steps.append("[2/2] Ran existing tests: 34 passed, 1 failed (anonymous-user)")
        passed, failed = 34, 1
    return {
        "task": task, "steps": steps,
        "passed": passed, "failed": failed,
        "success": failed == 0,
        "exit_code": 0 if failed == 0 else 1,
    }


def make_timeline(r):
    evts = []
    evts.append(TimelineEvent(
        kind="observation",
        content=f"pytest: {r['passed']} passed, {r['failed']} failed",
        source="tool", evidence_refs=["artifact:pytest-output"],
    ))
    if r["failed"] > 0:
        evts.append(TimelineEvent(
            kind="observation",
            content="FAILED test_anonymous_user_access - fix missed anonymous path",
            source="tool", evidence_refs=["artifact:pytest-output"],
        ))
        evts.append(TimelineEvent(
            kind="claim", content="The authentication fix is complete", source="agent",
        ))
    else:
        evts.append(TimelineEvent(
            kind="observation",
            content="All 35 tests passed including anonymous, authenticated, admin",
            source="tool", evidence_refs=["artifact:pytest-output"],
        ))
    evts.append(TimelineEvent(
        kind="outcome",
        content=f"Task {'succeeded' if r['success'] else 'failed'}: {r['passed']}/{r['passed']+r['failed']}",
        source="system",
    ))
    return evts


def header(title):
    print()
    print("=" * 64)
    print("  " + title)
    print("=" * 64)


def main():
    print()
    print("  ORP - Open Reflection Protocol  Demo")
    print("  Give your agent a mistake once.")
    print("  ORP helps it prove that it learned.")
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = ORPStorage(base_dir=tmpdir)
        task = "Fix authentication controller for anonymous users"

        # ── Run 1: Agent fails ──────────────────────────────
        header("Run 1: Agent misses anonymous user path -> FAILED")
        r1 = simulate_run(task, apply_lesson=False)
        exp1 = ExperienceRecord(
            agent={"id": "demo-agent", "version": "1.0", "model": "gpt-4"},
            task={"goal": task, "domain": "coding"},
            timeline=make_timeline(r1),
            outcome=Outcome(status="failed"),
        )
        storage.save_experience(exp1)
        print(f"  Saved experience: {exp1.experience_id[:12]}...")
        for s in r1["steps"]:
            print(f"    {s}")

        # ── ORP Analysis ────────────────────────────────────
        header("ORP analyzes the failure")
        reflection = ReflectionAnalyzer().analyze(exp1)
        print(f"  Diagnosis: {reflection.diagnosis}")

        challenged = Challenger().challenge(exp1)
        for c in challenged:
            print(f"  Challenged claim: {c['issue']}")

        # ── Compile Lesson + Eval ───────────────────────────
        header("ORP compiles Lesson + Eval")
        compiler = ExperienceCompiler()
        arts = compiler.compile(exp1)
        lesson = arts["lessons"][0]
        lesson.status = LessonStatus.ACTIVE
        lesson.validation["level"] = "externally_verified"
        lesson.scope = {"task_domains": ["coding"], "frameworks": [],
                        "agent_versions": []}
        storage.save_lesson(lesson)

        print(f"  Lesson: {lesson.lesson_id[:12]}... - {lesson.recommendation}")
        print(f"  Eval:   {arts['evals'][0].eval_id[:12]}...")

        # ── MCP Delivery ────────────────────────────────────
        header("MCP delivers Lesson to Agent")
        router = DeliveryRouter(storage)
        router.deliver(lesson, exp1.experience_id,
                       strategy=DeliveryStrategy.MCP_TOOL,
                       context="modifying auth controller")

        mcp = MCPServer(storage)
        result = mcp.handle_call("orp_retrieve_lessons",
                                  {"task": task, "limit": 3})
        print(f"  Agent retrieved {result['count']} lesson(s)")
        for r in result["lessons"]:
            print(f"    -> {r['recommendation'][:70]}...")
        mcp.handle_call("orp_acknowledge_lesson",
                        {"lesson_id": lesson.lesson_id})
        print("  Agent acknowledged lesson")

        # ── Run 2: Agent with Lesson succeeds ──────────────
        header("Run 2: Agent applies Lesson -> PASSED")
        r2 = simulate_run(task, apply_lesson=True)
        exp2 = ExperienceRecord(
            agent={"id": "demo-agent", "version": "1.0", "model": "gpt-4"},
            task={"goal": task, "domain": "coding"},
            timeline=make_timeline(r2),
            outcome=Outcome(status="success"),
        )
        storage.save_experience(exp2)
        print(f"  Saved experience: {exp2.experience_id[:12]}...")
        for s in r2["steps"]:
            print(f"    {s}")

        router.report_outcome(lesson.lesson_id, "success",
                              evidence_refs=[f"exp:{exp2.experience_id}"])
        print("  Lesson outcome reported")

        # Reload lesson to get updated metrics from report_outcome
        lesson = storage.get_lesson(lesson.lesson_id)

        # ── Effect Evaluation ───────────────────────────────
        header("ORP evaluates Lesson effect")
        evaluator = EffectEvaluator(storage)
        evaluation = evaluator.evaluate_matched_baseline(lesson)
        storage.save_lesson_evaluation(evaluation)
        print(f"  Method: {evaluation.method.value}")
        print(f"  Estimated effect: {evaluation.results.get('estimated_effect')}")
        print(f"  Decision: {evaluation.decision}")

        # ── Compare ─────────────────────────────────────────
        header("Before vs After comparison")
        print(f"  {'Metric':<30} {'Before':<20} {'After':<20}")
        print(f"  {'-'*28}  {'-'*18}  {'-'*18}")
        print(f"  {'Task success':<30} {'FAILED':<20} {'PASSED':<20}")
        print(f"  {'Tests passed':<30} {'34/35':<20} {'35/35':<20}")
        c1 = len([e for e in exp1.timeline if e.kind == EventKind.CLAIM])
        c2 = len([e for e in exp2.timeline if e.kind == EventKind.CLAIM])
        print(f"  {'Unproven claims':<30} {str(c1):<20} {str(c2):<20}")

        # ── Generate report ─────────────────────────────────
        html_path = "orp_demo_report.html"
        HTMLReporter(storage).write_report(html_path)
        print(f"\n  Full HTML report: {html_path}")

        # ── Summary ─────────────────────────────────────────
        print()
        print("=" * 64)
        print("  Summary")
        print("=" * 64)
        print("""
  Agent 第一次修复认证逻辑时遗漏了匿名用户路径。
  ORP 自动捕获失败、挑战未证明的声明、编译为 Lesson + Eval。
  第二次运行时 Agent 通过 MCP 检索到 Lesson 并应用。
  结果从 34/35 失败变成了 35/35 全部通过。

  ORP 核心价值:
    Give your agent a mistake once.
    ORP helps it prove that it learned.
""")
        storage.close()


if __name__ == "__main__":
    main()
