"""LangGraph Adapter"""

from typing import Any, Optional

from orp.schema import ExperienceRecord, TimelineEvent
from orp.experience import ExperienceBuilder


class LangGraphAdapter:
    """LangGraph trace 适配器"""

    def parse(self, state_snapshots: list[dict[str, Any]],
              agent_id: str = "langgraph-agent",
              goal: str = "") -> ExperienceRecord:
        builder = ExperienceBuilder()
        events = []
        for i, snapshot in enumerate(state_snapshots):
            node = snapshot.get("node", f"step_{i}")
            events.append(TimelineEvent(
                kind=snapshot.get("kind", "action"),
                content=f"Node {node}: {snapshot.get('keys', '')}",
                source="agent",
            ))
        return builder.from_events(events, goal=goal, agent_id=agent_id)
