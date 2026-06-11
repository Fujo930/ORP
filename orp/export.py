"""Export Engine — ORP JSON / OTLP refs / eval files"""

import json
from pathlib import Path
from typing import Any, Optional

from orp.schema import ExperienceRecord
from orp.storage import ORPStorage


class ExportEngine:
    """导出到多种格式"""

    def __init__(self, storage: Optional[ORPStorage] = None):
        self._storage = storage or ORPStorage()

    def to_json(self, experience_id: str) -> Optional[str]:
        """导出为 JSON"""
        if experience_id == "latest":
            exps = self._storage.list_experiences(limit=1)
            if not exps:
                return None
            exp = exps[0]
        else:
            exp = self._storage.get_experience(experience_id)
        if not exp:
            return None
        return json.dumps(exp.model_dump(), indent=2, default=str)

    def to_json_file(self, experience_id: str, path: str) -> bool:
        content = self.to_json(experience_id)
        if not content:
            return False
        Path(path).write_text(content)
        return True

    def to_otlp_refs(self, experience_id: str) -> dict[str, Any]:
        if experience_id == "latest":
            exps = self._storage.list_experiences(limit=1)
            if not exps:
                return {}
            exp = exps[0]
        else:
            exp = self._storage.get_experience(experience_id)
        if not exp:
            return {}
        return {
            "resource": {"orp": {"version": "0.3"}},
            "scopeSpans": [{
                "scope": {"name": "orp.experience"},
                "spans": [{
                    "spanId": exp.experience_id[:16],
                    "name": exp.task.get("goal", "")[:50],
                    "attributes": {
                        "orp.experience.id": exp.experience_id,
                        "orp.schema.version": "0.3",
                    },
                }],
            }],
        }
