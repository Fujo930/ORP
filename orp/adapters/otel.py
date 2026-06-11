"""OpenTelemetry Adapter — 从 OTel GenAI trace 导入"""

from typing import Any, Optional

from orp.schema import ExperienceRecord, TimelineEvent, EventKind
from orp.experience import ExperienceBuilder


class OTelAdapter:
    """OpenTelemetry GenAI trace 适配器
    
    解析符合 OTel GenAI 语义约定的 trace/span 数据。
    """

    def parse(self, spans: list[dict[str, Any]],
              agent_id: str = "unknown",
              goal: str = "") -> ExperienceRecord:
        builder = ExperienceBuilder()
        events = []
        for span in spans:
            kind = self._map_kind(span)
            events.append(TimelineEvent(
                kind=kind,
                content=span.get("name", span.get("attributes", {}).get("gen_ai.request.model", "")),
                source=span.get("attributes", {}).get("gen_ai.system", "agent"),
            ))
        if not events:
            events.append(TimelineEvent(kind="observation", content="Empty OTel trace"))
        return builder.from_events(events, goal=goal, agent_id=agent_id)

    def _map_kind(self, span: dict[str, Any]) -> str:
        attrs = span.get("attributes", {})
        kind = span.get("kind", "SPAN_KIND_INTERNAL")
        if "gen_ai.request.model" in attrs:
            return "action"
        if "gen_ai.evaluation.result" in attrs:
            return "feedback"
        if "exception" in span or "error" in span:
            return "observation"
        return "action"

    def from_otel_json(self, path: str) -> list[ExperienceRecord]:
        import json
        with open(path) as f:
            data = json.load(f)
        records = []
        for resource_span in data.get("resourceSpans", []):
            for scope_span in resource_span.get("scopeSpans", []):
                spans = scope_span.get("spans", [])
                if spans:
                    records.append(self.parse(spans))
        return records
