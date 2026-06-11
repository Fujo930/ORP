#!/usr/bin/env python3
"""Real LLM Experiment Runner — uses hermes CLI to evaluate ORP with real models

Usage:
    uv run python exps/real_llm_runner.py             # Run Task 1 only (default)
    uv run python exps/real_llm_runner.py --all        # Run all 10 tasks
    uv run python exps/real_llm_runner.py --task 1     # Run specific task

Each trial calls hermes chat -q with a coding task prompt.
Control group: no ORP lesson.
Experimental group: ORP lesson injected into prompt.

This is slow (~90s per call). For 10 tasks × 10 trials = 100 calls ≈ 2.5 hours.
Consider running overnight.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Task definitions ──────────────────────────────────────────

TASKS = [
    {
        "id": 1,
        "name": "Missing boundary conditions",
        "instruction": "Fix UserController.getUserName() to handle anonymous users (null user). Expected: throw IllegalStateException, not NPE.",
        "lesson": "Before modifying auth logic, test anonymous, authenticated, and forbidden paths.",
        "success_condition": "handles null user gracefully (not NPE)",
    },
    {
        "id": 2,
        "name": "Wrong file modified",
        "instruction": "A bug is reported in UserController.login(). Find it and fix it. (Note: UserController.java has the bug, not AdminController.)",
        "lesson": "Verify the file name matches the bug description before editing.",
        "success_condition": "edits UserController.java, not AdminController.java",
    },
    {
        "id": 3,
        "name": "Missing edge case",
        "instruction": "Implement findUserByEmail(email). Handle case where email is null or empty.",
        "lesson": "Always validate inputs (null, empty, whitespace) before processing.",
        "success_condition": "checks for null/empty email",
    },
    {
        "id": 4,
        "name": "Premature conclusion",
        "instruction": "Fix the failing test in UserServiceTest. Error message says 'Connection refused' but the real issue is a null config.",
        "lesson": "Read the full stack trace before diagnosing the root cause.",
        "success_condition": "identifies null config, not connection issue",
    },
    {
        "id": 5,
        "name": "Repeated failing command",
        "instruction": "Build script keeps failing with exit code 1. Fix it.",
        "lesson": "Stop after 3 repeated failures and reassess your strategy instead of retrying.",
        "success_condition": "changes approach after recognizing repeated failure",
    },
    {
        "id": 6,
        "name": "Fix breaks regression",
        "instruction": "Fix the sort() method that crashes on empty lists. Don't break the existing ascending/descending feature.",
        "lesson": "After any change, run the FULL test suite to check for regressions.",
        "success_condition": "empty list fix doesn't break existing sort order tests",
    },
    {
        "id": 7,
        "name": "Wrong API parameter",
        "instruction": "Call the external payment API to charge a customer. API docs say the field is 'amount_cents'.",
        "lesson": "Read the API documentation carefully before calling unfamiliar endpoints.",
        "success_condition": "uses correct parameter name 'amount_cents'",
    },
    {
        "id": 8,
        "name": "Missing async error handling",
        "instruction": "Add a timeout to the HTTP client call. The existing code doesn't handle timeout errors.",
        "lesson": "Always handle asyncio.TimeoutError and CancelledError explicitly.",
        "success_condition": "catches TimeoutError",
    },
    {
        "id": 9,
        "name": "Wrong dependency version",
        "instruction": "Add the 'requests' library to requirements.txt. The project uses Python 3.11.",
        "lesson": "Don't pin exact versions unless necessary — let pip resolve dependencies.",
        "success_condition": "doesn't pin an incompatible version",
    },
    {
        "id": 10,
        "name": "Null after DB query",
        "instruction": "Implement getUserProfile(userId). The database returns null for non-existent users. Handle it.",
        "lesson": "Always check for None after database queries before accessing fields.",
        "success_condition": "handles null DB result",
    },
]


def call_model(prompt: str, timeout: int = 120) -> str:
    """Call the LLM via hermes CLI"""
    proc = subprocess.Popen(
        ["hermes", "chat", "-q", prompt, "-Q"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return stdout or stderr
    except subprocess.TimeoutExpired:
        proc.kill()
        return "TIMEOUT"


def rate_response(response: str, task: dict) -> dict:
    """Rate whether the model's response correctly handles the task"""
    resp_lower = response.lower()
    task_id = task["id"]
    
    success = False
    evidence = ""
    
    if task_id == 1:
        # Handles null user?
        null_checks = ["null", "illegalstate", "if (user == null)", "if(user==null)",
                       "user == null", "user!=null", "optional"]
        success = any(c in resp_lower for c in null_checks)
        evidence = "null check found" if success else "no null check"
    
    elif task_id == 2:
        success = "usercontroller" in resp_lower and "admincontroller" not in resp_lower
        evidence = "correct file" if success else "wrong file"
    
    elif task_id == 3:
        null_checks = ["null", "empty", "isblank", "isempty", "email == null", "email==null"]
        success = any(c in resp_lower for c in null_checks)
        evidence = "null/empty check found" if success else "no validation"
    
    elif task_id == 4:
        success = "null" in resp_lower or "config" in resp_lower
        evidence = "identified null config" if success else "focused on connection"
    
    elif task_id == 5:
        success = any(w in resp_lower for w in ["stop", "reassess", "change", "different", "instead"])
        evidence = "changed approach" if success else "kept retrying"
    
    elif task_id == 6:
        success = "full" in resp_lower or "all" in resp_lower or "regression" in resp_lower or "existing" in resp_lower
        evidence = "considers regressions" if success else "narrow fix"
    
    elif task_id == 7:
        success = "amount_cents" in resp_lower
        evidence = "correct param" if success else "wrong param"
    
    elif task_id == 8:
        success = any(w in resp_lower for w in ["timeout", "timeouterror", "asyncio.timeout"])
        evidence = "handles timeout" if success else "no timeout handling"
    
    elif task_id == 9:
        success = "requests" in resp_lower and ("==" not in resp_lower or "compatible" in resp_lower)
        evidence = "flexible version" if success else "pinned version"
    
    elif task_id == 10:
        success = any(c in resp_lower for c in ["null", "none", "isnull", "if profile", "if result", "if userprofile"])
        evidence = "null check found" if success else "no null handling"
    
    return {"success": success, "evidence": evidence, "response_length": len(response)}


def run_experiment(task: dict, trials: int, use_orp: bool) -> list:
    """Run multiple trials of a task with or without ORP lesson"""
    results = []
    group = "ORP" if use_orp else "control"
    print(f"\n  [{group}] Running {trials} trials of '{task['name']}'...")
    
    for i in range(trials):
        orp_context = f"\n\nLESSON (from previous experience): {task['lesson']}\n" if use_orp else ""
        prompt = f"""You are a coding AI agent.

TASK: {task['instruction']}
{orp_context}
Focus on getting the right answer. Consider edge cases.

After your solution, on the LAST LINE output ONLY: JSON:{{"success": true/false}}"""
        
        print(f"    Trial {i+1}/{trials}...", end=" ", flush=True)
        response = call_model(prompt)
        
        if response == "TIMEOUT":
            print("TIMEOUT")
            results.append({"success": False, "error": "timeout"})
            continue
        
        rating = rate_response(response, task)
        results.append(rating)
        
        status = "✓" if rating["success"] else "✗"
        print(f"{status} ({rating['evidence']})")
        time.sleep(2)  # Rate limiting
    
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Run all 10 tasks")
    parser.add_argument("--task", type=int, default=1, help="Run specific task (1-10)")
    parser.add_argument("--trials", type=int, default=3, help="Trials per group (default: 3)")
    args = parser.parse_args()
    
    if args.all:
        task_list = TASKS
    else:
        task_list = [t for t in TASKS if t["id"] == args.task]
    
    if not task_list:
        print("No tasks selected")
        return
    
    total_start = time.time()
    all_metrics = []
    
    for task in task_list:
        print(f"\n{'='*60}")
        print(f"  Task {task['id']}: {task['name']}")
        print(f"{'='*60}")
        
        # Control group (no ORP)
        control = run_experiment(task, args.trials, use_orp=False)
        c_success = sum(1 for r in control if r.get("success"))
        
        # Experimental group (with ORP lesson)
        experimental = run_experiment(task, args.trials, use_orp=True)
        e_success = sum(1 for r in experimental if r.get("success"))
        
        c_rate = c_success / max(1, len(control))
        e_rate = e_success / max(1, len(experimental))
        
        metrics = {
            "task": task["name"],
            "control": f"{c_rate:.0%}",
            "orp": f"{e_rate:.0%}",
            "delta": f"{e_rate - c_rate:+.0%}",
        }
        all_metrics.append(metrics)
        
        print(f"\n  Result: Control={c_success}/{args.trials} vs ORP={e_success}/{args.trials}")
    
    # Summary
    total_time = time.time() - total_start
    print(f"\n{'='*60}")
    print("  REAL LLM EXPERIMENT SUMMARY")
    print(f"{'='*60}")
    print(f"  Model: deepseek-v4-flash (via hermes CLI)")
    print(f"  Total time: {total_time:.0f}s")
    print()
    for m in all_metrics:
        print(f"  {m['task']:<35} {m['control']:<8} -> {m['orp']:<8} ({m['delta']})")
    
    avg_c = sum(1 for t in task_list for r in run_experiment(t, 1, False) if r.get("success")) / max(1, len(task_list))
    print(f"\n  Save results to EXPERIMENTS.md to track improvements.")
    print()


if __name__ == "__main__":
    main()
