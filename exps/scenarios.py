"""Experiment scenarios — 10 failure patterns for coding agents"""

import random
from typing import Any

random.seed(42)


def _auth_boundary(apply_lesson: bool) -> dict[str, Any]:
    """Task 1: Agent misses anonymous user path when fixing auth"""
    if apply_lesson:
        return {
            "task": "Fix authentication for anonymous users",
            "domain": "coding",
            "steps": 3, "passed": 35, "failed": 0, "exit_code": 0,
            "success": True, "lesson_applied": True,
        }
    # Without lesson: 80% chance of missing anonymous path
    if random.random() < 0.8:
        return {
            "task": "Fix authentication for anonymous users",
            "domain": "coding",
            "steps": 2, "passed": 34, "failed": 1, "exit_code": 1,
            "success": False, "lesson_applied": False,
        }
    return {
        "task": "Fix authentication for anonymous users",
        "domain": "coding",
        "steps": 3, "passed": 35, "failed": 0, "exit_code": 0,
        "success": True, "lesson_applied": False,
    }


def _wrong_file(apply_lesson: bool) -> dict[str, Any]:
    """Task 2: Agent modifies wrong file"""
    if apply_lesson:
        return {
            "task": "Fix bug in UserController.java",
            "domain": "coding",
            "steps": 3, "passed": 35, "failed": 0, "exit_code": 0,
            "success": True, "lesson_applied": True,
        }
    if random.random() < 0.7:
        return {
            "task": "Fix bug in UserController.java",
            "domain": "coding",
            "steps": 2, "passed": 20, "failed": 15, "exit_code": 1,
            "success": False, "lesson_applied": False,
        }
    return {
        "task": "Fix bug in UserController.java",
        "domain": "coding",
        "steps": 2, "passed": 35, "failed": 0, "exit_code": 0,
        "success": True, "lesson_applied": False,
    }


def _project_convention(apply_lesson: bool) -> dict[str, Any]:
    """Task 3: Agent ignores project conventions (tabs vs spaces)"""
    if apply_lesson:
        return {
            "task": "Add new module following project style",
            "domain": "coding",
            "steps": 3, "passed": 35, "failed": 0, "exit_code": 0,
            "success": True, "lesson_applied": True,
        }
    if random.random() < 0.65:
        return {
            "task": "Add new module following project style",
            "domain": "coding",
            "steps": 1, "passed": 32, "failed": 3, "exit_code": 1,
            "success": False, "lesson_applied": False,
        }
    return {
        "task": "Add new module following project style",
        "domain": "coding",
        "steps": 2, "passed": 35, "failed": 0, "exit_code": 0,
        "success": True, "lesson_applied": False,
    }


def _premature_conclusion(apply_lesson: bool) -> dict[str, Any]:
    """Task 4: Agent jumps to wrong conclusion from partial error"""
    if apply_lesson:
        return {
            "task": "Fix database connection timeout",
            "domain": "coding",
            "steps": 4, "passed": 35, "failed": 0, "exit_code": 0,
            "success": True, "lesson_applied": True,
        }
    if random.random() < 0.75:
        return {
            "task": "Fix database connection timeout",
            "domain": "coding",
            "steps": 2, "passed": 20, "failed": 15, "exit_code": 1,
            "success": False, "lesson_applied": False,
        }
    return {
        "task": "Fix database connection timeout",
        "domain": "coding",
        "steps": 3, "passed": 35, "failed": 0, "exit_code": 0,
        "success": True, "lesson_applied": False,
    }


def _repeated_tool(apply_lesson: bool) -> dict[str, Any]:
    """Task 5: Agent repeatedly runs same failing command"""
    if apply_lesson:
        return {
            "task": "Debug failing test suite",
            "domain": "coding",
            "steps": 4, "passed": 35, "failed": 0, "exit_code": 0,
            "success": True, "lesson_applied": True, "repeated_calls": 0,
        }
    repeated = random.randint(3, 7) if not apply_lesson else 0
    return {
        "task": "Debug failing test suite",
        "domain": "coding",
        "steps": 2, "passed": 34, "failed": 1, "exit_code": 1,
        "success": False, "lesson_applied": False, "repeated_calls": repeated,
    }


def _regression(apply_lesson: bool) -> dict[str, Any]:
    """Task 6: Fix one bug, introduce another"""
    if apply_lesson:
        return {
            "task": "Fix login error without breaking registration",
            "domain": "coding",
            "steps": 4, "passed": 42, "failed": 0, "exit_code": 0,
            "success": True, "lesson_applied": True, "regressions": 0,
        }
    if random.random() < 0.7:
        reg = random.randint(1, 3)
        return {
            "task": "Fix login error without breaking registration",
            "domain": "coding",
            "steps": 2, "passed": 42 - reg, "failed": reg, "exit_code": 1,
            "success": False, "lesson_applied": False, "regressions": reg,
        }
    return {
        "task": "Fix login error without breaking registration",
        "domain": "coding",
        "steps": 3, "passed": 42, "failed": 0, "exit_code": 0,
        "success": True, "lesson_applied": False, "regressions": 0,
    }


def _api_param(apply_lesson: bool) -> dict[str, Any]:
    """Task 7: Agent uses wrong API parameter name"""
    if apply_lesson:
        return {
            "task": "Integrate payment API",
            "domain": "coding",
            "steps": 3, "passed": 35, "failed": 0, "exit_code": 0,
            "success": True, "lesson_applied": True, "api_calls": 1,
        }
    if random.random() < 0.6:
        return {
            "task": "Integrate payment API",
            "domain": "coding",
            "steps": 2, "passed": 20, "failed": 15, "exit_code": 1,
            "success": False, "lesson_applied": False, "api_calls": 3,
        }
    return {
        "task": "Integrate payment API",
        "domain": "coding",
        "steps": 2, "passed": 35, "failed": 0, "exit_code": 0,
        "success": True, "lesson_applied": False, "api_calls": 1,
    }


def _async_error(apply_lesson: bool) -> dict[str, Any]:
    """Task 8: Agent misses async error handling"""
    if apply_lesson:
        return {
            "task": "Add async timeout handling to HTTP client",
            "domain": "coding",
            "steps": 3, "passed": 35, "failed": 0, "exit_code": 0,
            "success": True, "lesson_applied": True,
        }
    if random.random() < 0.7:
        return {
            "task": "Add async timeout handling to HTTP client",
            "domain": "coding",
            "steps": 2, "passed": 30, "failed": 5, "exit_code": 1,
            "success": False, "lesson_applied": False,
        }
    return {
        "task": "Add async timeout handling to HTTP client",
        "domain": "coding",
        "steps": 2, "passed": 35, "failed": 0, "exit_code": 0,
        "success": True, "lesson_applied": False,
    }


def _dep_version(apply_lesson: bool) -> dict[str, Any]:
    """Task 9: Agent pins incompatible dependency version"""
    if apply_lesson:
        return {
            "task": "Add pagination library to project",
            "domain": "coding",
            "steps": 3, "passed": 35, "failed": 0, "exit_code": 0,
            "success": True, "lesson_applied": True,
        }
    if random.random() < 0.55:
        return {
            "task": "Add pagination library to project",
            "domain": "coding",
            "steps": 2, "passed": 15, "failed": 20, "exit_code": 1,
            "success": False, "lesson_applied": False,
        }
    return {
        "task": "Add pagination library to project",
        "domain": "coding",
        "steps": 2, "passed": 35, "failed": 0, "exit_code": 0,
        "success": True, "lesson_applied": False,
    }


def _null_handling(apply_lesson: bool) -> dict[str, Any]:
    """Task 10: Agent forgets null check after DB query"""
    if apply_lesson:
        return {
            "task": "Implement user profile lookup",
            "domain": "coding",
            "steps": 3, "passed": 35, "failed": 0, "exit_code": 0,
            "success": True, "lesson_applied": True,
        }
    if random.random() < 0.75:
        return {
            "task": "Implement user profile lookup",
            "domain": "coding",
            "steps": 2, "passed": 30, "failed": 5, "exit_code": 1,
            "success": False, "lesson_applied": False,
        }
    return {
        "task": "Implement user profile lookup",
        "domain": "coding",
        "steps": 2, "passed": 35, "failed": 0, "exit_code": 0,
        "success": True, "lesson_applied": False,
    }


# All scenarios indexed
SCENARIOS = [
    ("Missing boundary conditions", _auth_boundary, "Test anonymous, authenticated, and forbidden paths"),
    ("Wrong file modified", _wrong_file, "Verify file matches bug description before editing"),
    ("Project conventions ignored", _project_convention, "Check .editorconfig and linter config before coding"),
    ("Premature conclusion", _premature_conclusion, "Read full stack trace before diagnosing"),
    ("Repeated failing command", _repeated_tool, "Stop after 3 failures and reassess strategy"),
    ("Fix breaks regression", _regression, "Run full test suite after every change"),
    ("Wrong API parameter", _api_param, "Query API docs before using unfamiliar parameters"),
    ("Async error handling", _async_error, "Always handle asyncio.TimeoutError and CancelledError"),
    ("Dependency version conflict", _dep_version, "Let pip resolver choose versions unless explicitly required"),
    ("Null handling after query", _null_handling, "Always check for None after DB query"),
]
