"""Reflection Analyzer — 诊断、替代策略、Challenger"""

from typing import Any, Optional

from orp.schema import (
    ExperienceRecord, TimelineEvent, EventKind, ReflectionAnalysis,
)
from orp.storage import ORPStorage


class ReflectionAnalyzer:
    """反思分析 — 输出结构化候选，不直接修改 Agent"""

    def analyze(self, record: ExperienceRecord) -> ReflectionAnalysis:
        """对 ExperienceRecord 执行反思分析"""
        diagnosis = self._diagnose(record)
        alternatives = self._suggest_alternatives(record)
        limitations = self._find_limitations(record)
        return ReflectionAnalysis(
            diagnosis=diagnosis,
            alternatives=alternatives,
            limitations=limitations,
        )

    def _diagnose(self, record: ExperienceRecord) -> Optional[str]:
        """从失败的运行中生成诊断"""
        outcome_events = [
            e for e in record.timeline
            if e.kind == EventKind.OUTCOME
        ]
        error_events = [
            e for e in record.timeline
            if e.kind == EventKind.OBSERVATION
            and any(w in e.content.lower() for w in ["error", "fail", "exception", "traceback"])
        ]
        if outcome_events:
            return f"Outcome: {outcome_events[-1].content}"
        if error_events:
            return f"Detected error: {error_events[-1].content[:200]}"
        if record.outcome.status == "failed":
            return "Task failed — review timeline for root cause"
        return None

    def _suggest_alternatives(self, record: ExperienceRecord) -> list[str]:
        """基于失败的运行提出替代策略"""
        suggestions = []
        has_test = any(
            "test" in e.content.lower() or "pytest" in e.content.lower()
            for e in record.timeline
        )
        has_diff = any(
            "git diff" in e.content.lower() or "diff" in e.content.lower()
            for e in record.timeline
        )
        if record.outcome.status == "failed":
            if not has_test:
                suggestions.append("Run tests first to confirm the failure")
            if not has_diff:
                suggestions.append("Check git diff to understand what changed")
        return suggestions

    def _find_limitations(self, record: ExperienceRecord) -> list[str]:
        """识别这次运行的局限性"""
        limits = []
        if not record.task.get("input_ref"):
            limits.append("No input reference recorded — cannot reproduce exact input")
        claim_count = sum(1 for e in record.timeline if e.kind == EventKind.CLAIM)
        evidence_count = sum(len(e.evidence_refs) for e in record.timeline)
        if claim_count > evidence_count:
            limits.append(f"More claims ({claim_count}) than evidence refs ({evidence_count})")
        return limits


class Challenger:
    """Challenger — 质疑未经证明的声明
    
    自动查找 ExperienceRecord 中的 claim 及其证据支持情况。
    """

    def challenge(self, record: ExperienceRecord) -> list[dict[str, Any]]:
        """找出所有未经充分支持的声明"""
        challenged: list[dict[str, Any]] = []
        for evt in record.timeline:
            if evt.kind == EventKind.CLAIM:
                if not evt.evidence_refs:
                    challenged.append({
                        "event_id": evt.id,
                        "content": evt.content[:100],
                        "issue": "No evidence references provided",
                    })
                elif len(evt.evidence_refs) < 2:
                    challenged.append({
                        "event_id": evt.id,
                        "content": evt.content[:100],
                        "issue": "Only 1 evidence ref — may be insufficient",
                    })
        return challenged
