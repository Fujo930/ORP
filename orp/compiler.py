"""Experience Compiler — 将候选经验编译为可执行资产"""

from typing import Any, Optional

from orp.schema import (
    ExperienceRecord, Lesson, EvalArtifact,
    EventKind, LessonStatus,
)
from orp.reflect import Challenger, ReflectionAnalyzer


class ExperienceCompiler:
    """经验编译器 — 诊断 → Lesson / Eval / Guardrail 候选"""

    def compile(self, record: ExperienceRecord) -> dict[str, list[Any]]:
        """编译 ExperienceRecord 生成可执行资产"""
        lessons: list[Lesson] = []
        evals: list[EvalArtifact] = []
        guardrails: list[dict[str, Any]] = []

        # 如果任务失败，生成 Lesson 候选
        if record.outcome.status in ("failed", "partial"):
            lesson = self._generate_lesson(record)
            if lesson:
                lessons.append(lesson)

        # 生成回归 Eval
        eval_artifact = self._generate_eval(record)
        if eval_artifact:
            evals.append(eval_artifact)

        # 检查重复动作模式
        guardrail = self._check_repeated_patterns(record)
        if guardrail:
            guardrails.append(guardrail)

        # 更新 record 的 artifacts 引用
        record.artifacts = {
            "lessons": [l.lesson_id for l in lessons],
            "evals": [e.eval_id for e in evals],
            "guardrails": [g.get("id", "") for g in guardrails],
        }

        return {"lessons": lessons, "evals": evals, "guardrails": guardrails}

    def _generate_lesson(self, record: ExperienceRecord) -> Optional[Lesson]:
        """从失败的运行生成 Lesson 候选"""
        challenger = Challenger()
        challenged = challenger.challenge(record)
        
        # 从被挑战的声明中提取建议
        recommendations = set()
        for c in challenged:
            content = c.get("content", "")
            if "fix" in content.lower() or "complete" in content.lower():
                recommendations.add("Verify fixes with before/after tests")
            if "test" in content.lower():
                recommendations.add("Run all tests after changes, not just affected ones")

        if not recommendations:
            if record.outcome.status == "failed":
                recommendations.add("Review full timeline before drawing conclusions")
            else:
                return None

        task_goal = record.task.get("goal", "")
        task_domain = record.task.get("domain", "coding")

        return Lesson(
            trigger={
                "domain": task_domain,
                "conditions": [task_goal[:200]] if task_goal else [],
            },
            recommendation="; ".join(sorted(recommendations)),
            provenance={"experience_ids": [record.experience_id]},
            scope={"task_domains": [task_domain], "frameworks": [],
                   "agent_versions": [record.agent.get("version", "")] if record.agent.get("version") else []},
            status=LessonStatus.CANDIDATE,
        )

    def _generate_eval(self, record: ExperienceRecord) -> Optional[EvalArtifact]:
        """从失败的运行生成回归 Eval"""
        error_events = [
            e for e in record.timeline
            if e.kind == EventKind.OBSERVATION
            and any(w in e.content.lower() for w in ["error", "fail", "exception", "exit code", "traceback"])
        ]
        if not error_events and record.outcome.status != "failed":
            return None

        # 生成 pytest 测试
        test_content = self._make_pytest_eval(record)
        return EvalArtifact(
            origin_experience=record.experience_id,
            runner="pytest",
            command="pytest -q",
            expected={"exit_code": 0},
            generated_by="orp-compiler",
        )


    def _check_repeated_patterns(self, record):
        """检查重复的无效动作模式"""
        actions = [e for e in record.timeline if e.kind == EventKind.ACTION]
        contents = [a.content for a in actions]
        from collections import Counter
        duplicates = {k: v for k, v in Counter(contents).items() if v > 2}
        if duplicates:
            return {
                "id": "guard_" + record.experience_id[:8],
                "type": "repeated_action",
                "pattern": "Repeated action " + str(max(duplicates, key=duplicates.get)) + " " + str(max(duplicates.values())) + " times",
                "source_experience": record.experience_id,
            }
        return None

    def _make_pytest_eval(self, record: ExperienceRecord) -> str:
        """生成一个基本的 pytest 回归测试"""
        task_goal = record.task.get("goal", "unknown")
        return (
            f"ORP-generated regression test\n"
            f"Source: {record.experience_id}\n"
            f"Goal: {task_goal}\n"
        )
