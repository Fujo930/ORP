"""捕获层 — 进程/工具/测试/OTel 数据采集"""

import os
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from orp.schema import TimelineEvent, EventKind


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def capture_command(
    command: list[str],
    workdir: Optional[str] = None,
    timeout: int = 300,
) -> dict[str, Any]:
    """运行命令并捕获输出、退出码和耗时"""
    start = time.time()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=workdir or os.getcwd(),
            timeout=timeout,
        )
        duration = time.time() - start
        return {
            "command": " ".join(command),
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration": round(duration, 2),
            "success": result.returncode == 0,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "command": " ".join(command),
            "exit_code": -1,
            "stdout": e.stdout or "",
            "stderr": e.stderr or "",
            "duration": timeout,
            "success": False,
            "timed_out": True,
        }


def capture_git_diff(workdir: Optional[str] = None) -> str:
    """捕获工作目录的 git diff"""
    try:
        cwd = workdir or os.getcwd()
        result = subprocess.run(
            ["git", "diff"],
            capture_output=True, text=True, cwd=cwd, timeout=30,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def capture_git_status(workdir: Optional[str] = None) -> str:
    """捕获 git 状态"""
    try:
        cwd = workdir or os.getcwd()
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, cwd=cwd, timeout=30,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def capture_pytest_result(workdir: Optional[str] = None) -> dict[str, Any]:
    """运行 pytest 并捕获结果"""
    try:
        cwd = workdir or os.getcwd()
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=short"],
            capture_output=True, text=True, cwd=cwd, timeout=120,
        )
        output = result.stdout + result.stderr
        passed = "passed" in output or result.returncode == 0
        failed_count = 0
        passed_count = 0
        for line in output.split("\n"):
            if "failed" in line and "passed" in line:
                parts = line.split()
                for p in parts:
                    if "failed" in p:
                        try:
                            failed_count = int(p.split("failed")[0])
                        except ValueError:
                            pass
                    elif "passed" in p:
                        try:
                            passed_count = int(p.split("passed")[0])
                        except ValueError:
                            pass
        return {
            "exit_code": result.returncode,
            "summary": result.stdout.strip().split("\n")[-1] if result.stdout else "",
            "passed": passed,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "output": output,
        }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {"exit_code": -1, "passed": False, "error": "could not run pytest"}


@contextmanager
def capture_trace_context(goal: str):
    """上下文管理器 — 创建一个带有基本 trace 的作用域
    
    用法:
        with capture_trace_context("修复登录错误") as ctx:
            result = agent.run()
            ctx.set_outcome(result)
    """
    events: list[TimelineEvent] = []
    outcome = {"status": "unknown"}
    start = time.time()
    
    class CaptureContext:
        def add_event(self, kind: str, content: str, source: str = "agent",
                      evidence_refs: Optional[list[str]] = None):
            events.append(TimelineEvent(
                kind=kind,
                content=content,
                source=source,
                evidence_refs=evidence_refs or [],
            ))
        
        def set_outcome(self, status: str, signals: Optional[dict[str, Any]] = None):
            nonlocal outcome
            outcome = {"status": status, "objective_signals": [signals] if signals else []}
        
        def get_events(self) -> list[TimelineEvent]:
            return events.copy()
        
        def get_duration(self) -> float:
            return time.time() - start
    
    ctx = CaptureContext()
    try:
        yield ctx
        ctx.add_event("outcome", f"Completed in {time.time()-start:.1f}s", source="system")
    except Exception as e:
        ctx.set_outcome("failed", {"error": str(e)})
        ctx.add_event("observation", f"Error: {e}", source="system")
    finally:
        pass
