"""Experience Builder — 从异构 trace 构建 ExperienceRecord"""

import json
from datetime import datetime, timezone
from typing import Any, Optional

from orp.schema import (
    ExperienceRecord, TimelineEvent, EventKind, Outcome, ReflectionAnalysis,
)
from orp.evidence import redact_text, redact_sensitive_fields, make_evidence_ref


class ExperienceBuilder:
    """将异构 trace 统一为 ExperienceRecord"""

    def from_trace(self, trace: dict[str, Any],
                   agent_id: str = "unknown",
                   goal: str = "") -> ExperienceRecord:
        """从通用 trace dict 构建 ExperienceRecord"""
        timeline = self._extract_timeline(trace)
        outcome = self._extract_outcome(trace)
        reflection = self._extract_reflection(trace)
        
        return ExperienceRecord(
            agent={"id": agent_id, "version": trace.get("agent_version", ""),
                   "model": trace.get("model", "")},
            task={"goal": goal or trace.get("goal", ""),
                  "domain": trace.get("domain", ""),
                  "input_ref": trace.get("input_ref", "")},
            trace_ref=trace.get("trace_id") or trace.get("trace_ref"),
            timeline=timeline,
            outcome=outcome,
            reflection=reflection,
        )

    def from_events(self, events: list[TimelineEvent],
                    goal: str = "",
                    agent_id: str = "unknown") -> ExperienceRecord:
        """直接从 TimelineEvent 列表构建"""
        outcome = Outcome()
        # 检查是否有 outcome event
        for evt in events:
            if evt.kind == EventKind.OUTCOME:
                outcome.status = evt.content
                break
        return ExperienceRecord(
            agent={"id": agent_id},
            task={"goal": goal},
            timeline=events,
            outcome=outcome,
        )

    def _extract_timeline(self, trace: dict[str, Any]) -> list[TimelineEvent]:
        """从 trace dict 提取时间线事件"""
        events: list[TimelineEvent] = []
        raw_events = trace.get("events") or trace.get("spans") or trace.get("steps", [])
        for i, raw in enumerate(raw_events):
            events.append(TimelineEvent(
                kind=raw.get("kind", raw.get("type", "observation")),
                source=raw.get("source", "agent"),
                content=raw.get("content", raw.get("message", str(raw))),
                evidence_refs=raw.get("evidence_refs", []),
            ))
        if not events:
            events.append(TimelineEvent(
                kind="observation",
                content=f"Trace captured {len(raw_events)} unknown events"
            ))
        return events

    def _extract_outcome(self, trace: dict[str, Any]) -> Outcome:
        raw = trace.get("outcome", {})
        if isinstance(raw, str):
            return Outcome(status=raw)
        return Outcome(**raw)

    def _extract_reflection(self, trace: dict[str, Any]) -> Optional[ReflectionAnalysis]:
        raw = trace.get("reflection")
        if not raw:
            return None
        if isinstance(raw, ReflectionAnalysis):
            return raw
        return ReflectionAnalysis(**raw)


class Redactor:
    """对 ExperienceRecord 应用脱敏"""

    @staticmethod
    def apply(record: ExperienceRecord) -> ExperienceRecord:
        record.task["goal"] = redact_text(record.task.get("goal", ""))
        for evt in record.timeline:
            evt.content = redact_text(evt.content)
            evt.evidence_refs = [
                r if r.startswith(("artifact:", "eval:")) else f"ref:{hash(r)}"
                for r in evt.evidence_refs
            ]
        return record


class EvidenceLinker:
    """链接与验证证据引用"""

    @staticmethod
    def link(record: ExperienceRecord) -> ExperienceRecord:
        for evt in record.timeline:
            seen = set()
            linked = []
            for ref in evt.evidence_refs:
                if ref not in seen:
                    seen.add(ref)
                    linked.append(ref)
            evt.evidence_refs = linked
        return record
