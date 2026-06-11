"""Generic JSON Adapter — 从任意 JSON trace 导入"""

from typing import Any, Optional

from orp.schema import ExperienceRecord
from orp.experience import ExperienceBuilder


class GenericJSONAdapter:
    """通用 JSON trace 适配器"""

    def __init__(self):
        self._builder = ExperienceBuilder()

    def parse(self, data: dict[str, Any],
              agent_id: str = "unknown",
              goal: str = "") -> ExperienceRecord:
        return self._builder.from_trace(data, agent_id=agent_id, goal=goal)

    def parse_file(self, path: str) -> ExperienceRecord:
        import json
        with open(path) as f:
            data = json.load(f)
        return self.parse(data)
