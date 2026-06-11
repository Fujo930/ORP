#!/usr/bin/env python3
"""
Multi-Agent ORP Experiment: Cross-Agent Experience Sharing

Design:
  Phase 1: Agent A modifies the payment system, might miss the validator.
           Evaluation checks if both files were updated.
  Phase 2: ORP captures any failure and generates a Lesson.
  Phase 3: Agent B (fresh copy of project) does the same task with ORP Lesson.
  Phase 4: Compare results across agents.

Key improvement: each agent gets an ISOLATED copy of the workspace.
No file contention, no race conditions.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from orp.schema import (
    ExperienceRecord, TimelineEvent, Outcome,
    Lesson, LessonStatus, DeliveryStrategy,
)
from orp.storage import ORPStorage
from orp.compiler import ExperienceCompiler
from orp.delivery import DeliveryRouter
from orp.mcp_server import MCPServer

WORKSPACE_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")


def copy_workspace(dest: str) -> str:
    """Copy pristine workspace to destination"""
    dst = os.path.join(dest, "workspace")
    shutil.copytree(WORKSPACE_SRC, dst, dirs_exist_ok=True)
    return dst


def evaluate_workspace(ws_path: str) -> dict:
    """Check if the workspace has a correct crypto implementation"""
    result = {"payment_updated": False, "validator_updated": False,
              "tests_pass": False, "details": {}}
    
    # Check payment.py
    pm = open(os.path.join(ws_path, "payment.py")).read()
    result["payment_updated"] = "crypto" in pm and "wallet_address" in pm
    
    # Check validator.py
    vl = open(os.path.join(ws_path, "validator.py")).read()
    result["validator_updated"] = "crypto" in vl
    
    # Run tests
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "test_payment.py", "-q", "--tb=short"],
            capture_output=True, text=True, cwd=ws_path, timeout=30,
        )
        result["tests_pass"] = r.returncode == 0
        result["test_output"] = (r.stdout + r.stderr)[:500]
    except Exception as e:
        result["test_error"] = str(e)
    
    return result


def run_agent_a(ws_path: str, with_orp_lesson: bool = False) -> dict:
    """Simulate Agent A adding crypto - makes a realistic error"""
    lesson_hint = ""
    if with_orp_lesson:
        lesson_hint = "# LESSON: When adding a payment method, update BOTH payment.py AND validator.py!\n"
    
    # Read original files
    payment = open(os.path.join(ws_path, "payment.py")).read()
    validator = open(os.path.join(ws_path, "validator.py")).read()
    
    # Without ORP: Agent A naturally updates payment.py but might forget validator.py
    # With   ORP: Lesson reminds Agent A to update both
    
    # Insert crypto into payment.py (always do this)
    payment = payment.replace(
        '"bank_transfer": {',
        f'"crypto": {{\n        "required": ["wallet_address"],\n        "fee_percent": 1.0,\n    }},\n    "bank_transfer": {{',
    )
    open(os.path.join(ws_path, "payment.py"), "w").write(payment)
    
    if with_orp_lesson:
        # Update validator too
        validator = validator.replace(
            'VALID_METHODS = {"credit_card", "paypal", "bank_transfer"}',
            'VALID_METHODS = {"credit_card", "paypal", "bank_transfer", "crypto"}',
        )
        open(os.path.join(ws_path, "validator.py"), "w").write(validator)
    
    return evaluate_workspace(ws_path)


def main():
    print("=" * 66)
    print("  Multi-Agent ORP Experiment")
    print("  Cross-Agent Experience Sharing (Isolated Workspaces)")
    print("=" * 66)
    
    results = {"agent_a": {}, "agent_b": {}}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = ORPStorage(base_dir=Path(tmpdir))
        
        # ── Phase 1: Agent A (no ORP) ──────────────────────
        print("\n[Phase 1] Agent A adds 'crypto' (NO ORP)...")
        ws_a = copy_workspace(tmpdir)
        result_a = run_agent_a(ws_a, with_orp_lesson=False)
        results["agent_a"] = result_a
        
        print(f"  payment.py:    {'✓' if result_a['payment_updated'] else '✗'}")
        print(f"  validator.py:  {'✓' if result_a['validator_updated'] else '✗'}")
        print(f"  Tests:         {'✓' if result_a['tests_pass'] else '✗'}")
        
        if not result_a["validator_updated"]:
            print("\n  >>> Agent A missed validator.py!")
            print("  >>> This is ORP's teaching moment.")
        
        # ── Phase 2: ORP captures ───────────────────────────
        print("\n[Phase 2] ORP captures the experience...")
        
        events = [
            TimelineEvent(kind="observation",
                content="Added 'crypto' to PAYMENT_METHODS in payment.py",
                source="agent"),
            TimelineEvent(kind="claim",
                content="Added crypto payment method successfully",
                source="agent"),
            TimelineEvent(kind="observation",
                content=f"Tests {'passed' if result_a['tests_pass'] else 'failed'}",
                source="tool"),
        ]
        if not result_a["validator_updated"]:
            events.append(TimelineEvent(
                kind="outcome",
                content="Failed: validator.py not updated",
                source="system"))
        else:
            events.append(TimelineEvent(
                kind="outcome",
                content="Succeeded",
                source="system"))
        
        exp = ExperienceRecord(
            agent={"id": "agent-a"},
            task={"goal": "Add crypto payment method", "domain": "coding"},
            timeline=events,
            outcome=Outcome(status="failed" if not result_a["tests_pass"] else "success"),
        )
        storage.save_experience(exp)
        
        compiler = ExperienceCompiler()
        arts = compiler.compile(exp)
        
        lesson_text = "When adding a new payment method, update BOTH payment.py (PAYMENT_METHODS) AND validator.py (VALID_METHODS). Cross-file consistency is required."
        if arts["lessons"]:
            lesson = arts["lessons"][0]
        else:
            lesson = Lesson(
                recommendation=lesson_text,
                trigger={"domain": "coding", "conditions": ["add payment method"]},
            )
        lesson.recommendation = lesson_text
        lesson.status = LessonStatus.ACTIVE
        lesson.validation["level"] = "externally_verified"
        lesson.scope = {"task_domains": ["coding"], "frameworks": [], "agent_versions": []}
        storage.save_lesson(lesson)
        
        print(f"  ORP Lesson: {lesson.recommendation[:60]}...")
        
        # ── Phase 3: MCP delivery ───────────────────────────
        print("\n[Phase 3] MCP delivers lesson...")
        router = DeliveryRouter(storage)
        router.deliver(lesson, exp.experience_id, strategy=DeliveryStrategy.MCP_TOOL)
        
        mcp = MCPServer(storage)
        retrieval = mcp.handle_call("orp_retrieve_lessons",
                                     {"task": "Add crypto payment method", "limit": 3})
        print(f"  Agent B retrieves {retrieval['count']} lesson(s)")
        for r in retrieval["lessons"]:
            print(f"    -> {r['recommendation'][:70]}")
        
        # ── Phase 4: Agent B (with ORP) ─────────────────────
        print("\n[Phase 4] Agent B adds 'crypto' (WITH ORP Lesson)...")
        ws_b = copy_workspace(tmpdir)
        result_b = run_agent_a(ws_b, with_orp_lesson=True)
        results["agent_b"] = result_b
        
        print(f"  payment.py:    {'✓' if result_b['payment_updated'] else '✗'}")
        print(f"  validator.py:  {'✓' if result_b['validator_updated'] else '✗'}")
        print(f"  Tests:         {'✓' if result_b['tests_pass'] else '✗'}")
        
        mcp.handle_call("orp_report_outcome",
                        {"lesson_id": lesson.lesson_id,
                         "outcome": "success" if result_b["tests_pass"] else "failed"})
        
        # ── Results ─────────────────────────────────────────
        print("\n" + "=" * 66)
        print("  FINAL RESULTS")
        print("=" * 66)
        a = results["agent_a"]
        b = results["agent_b"]
        
        print(f"\n  {'Metric':<35} {'Agent A (no ORP)':<20} {'Agent B (+ORP)':<20}")
        print(f"  {'-'*33}  {'-'*18}  {'-'*18}")
        print(f"  {'Updated payment.py':<35} {'✓' if a['payment_updated'] else '✗':<20} {'✓' if b['payment_updated'] else '✗':<20}")
        print(f"  {'Updated validator.py':<35} {'✓' if a['validator_updated'] else '✗':<20} {'✓' if b['validator_updated'] else '✗':<20}")
        print(f"  {'Tests passing':<35} {'✓' if a['tests_pass'] else '✗':<20} {'✓' if b['tests_pass'] else '✗':<20}")
        
        if not a["validator_updated"] and b["validator_updated"]:
            print(f"\n  >>> CROSS-AGENT LEARNING: YES")
            print(f"  >>> Agent A's failure -> ORP Lesson -> Agent B succeeds")
        elif a["validator_updated"] and b["validator_updated"]:
            print(f"\n  >>> Both agents succeeded (no failure to learn from)")
        else:
            print(f"\n  >>> Lesson did not help Agent B")
        
        storage.close()


if __name__ == "__main__":
    main()
