"""OpenAI Agents SDK Adapter"""

from typing import Any, Optional

from orp.schema import ExperienceRecord, TimelineEvent
from orp.experience import ExperienceBuilder


class OpenAIAgentsAdapter:
    """OpenAI Agents SDK trace 适配器"""

    def parse(self, trace_data: dict[str, Any],
              agent_id: str = "openai-agent",
              goal: str = "") -> ExperienceRecord:
        builder = ExperienceBuilder()
        events = []
        # OpenAI Agents SDK trace 结构: trace -> runs -> steps
        runs = trace_data.get("runs", [trace_data])
        for run in runs:
            for step in run.get("steps", []):
                events.append(TimelineEvent(
                    kind=step.get("type", "action"),
                    content=step.get("output", step.get("input", str(step)))[:500],
                    source="agent",
                    evidence_refs=[f"otel:{step.get('span_id', '')}"] if step.get("span_id") else [],
                ))
        return builder.from_events(events, goal=goal, agent_id=agent_id)
