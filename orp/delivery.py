"""Delivery Router — 将 Lesson 交付给 Agent"""

from typing import Any, Optional

from orp.schema import (
    Lesson, LessonDelivery, DeliveryStrategy,
)
from orp.storage import ORPStorage


class DeliveryRouter:
    """Lesson 交付路由 — 支持多种交付策略"""

    def __init__(self, storage: Optional[ORPStorage] = None):
        self._storage = storage or ORPStorage()

    def deliver(self, lesson: Lesson, experience_id: str,
                strategy: DeliveryStrategy = DeliveryStrategy.MCP_TOOL,
                context: Optional[str] = None) -> LessonDelivery:
        """交付 Lesson 并记录"""
        delivery = LessonDelivery(
            lesson_id=lesson.lesson_id,
            experience_id=experience_id,
            strategy=strategy,
            delivery_context=context,
        )
        # 如果策略需要写入文件，同步执行
        if strategy == DeliveryStrategy.POLICY_FILE:
            self._write_policy_file(lesson)
        elif strategy == DeliveryStrategy.PROMPT_CONTEXT:
            delivery.acknowledged = True  # 假设注入成功
        
        self._storage.save_delivery(delivery)
        
        # 更新 Lesson 指标
        lesson.metrics["delivered"] = lesson.metrics.get("delivered", 0) + 1
        self._storage.save_lesson(lesson)
        
        return delivery

    def acknowledge(self, lesson_id: str, delivery_id: str) -> None:
        """记录 Agent 已确认接收到 Lesson"""
        # In a real implementation, this would update the delivery record
        # For now, we update metrics on the lesson
        lesson = self._storage.get_lesson(lesson_id)
        if lesson:
            lesson.metrics["acknowledged"] = lesson.metrics.get("acknowledged", 0) + 1
            self._storage.save_lesson(lesson)

    def report_outcome(self, lesson_id: str, outcome: str,
                       evidence_refs: Optional[list[str]] = None) -> None:
        """记录 Lesson 应用后的实际结果"""
        lesson = self._storage.get_lesson(lesson_id)
        if not lesson:
            return
        lesson.metrics["applied"] = lesson.metrics.get("applied", 0) + 1
        if outcome in ("success", "improved", "passed"):
            lesson.metrics["successful_after_apply"] = lesson.metrics.get("successful_after_apply", 0) + 1
        self._storage.save_lesson(lesson)

    def _write_policy_file(self, lesson: Lesson) -> None:
        """将 Lesson 写入 AGENTS.md 等策略文件"""
        import os
        try:
            agents_path = os.path.join(os.getcwd(), "AGENTS.md")
            comment = f"\n<!-- ORP Lesson: {lesson.lesson_id} -->\n- {lesson.recommendation}\n<!-- END ORP Lesson -->\n"
            if os.path.exists(agents_path):
                with open(agents_path, "a") as f:
                    f.write(comment)
        except (IOError, PermissionError):
            pass

    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """返回 MCP Server 的工具定义"""
        return [
            {
                "name": "orp_retrieve_lessons",
                "description": "Retrieve relevant lessons for a task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Task description"},
                        "limit": {"type": "integer", "default": 3},
                        "domain": {"type": "string", "optional": True},
                    },
                },
            },
            {
                "name": "orp_acknowledge_lesson",
                "description": "Acknowledge a delivered lesson",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lesson_id": {"type": "string"},
                    },
                },
            },
            {
                "name": "orp_report_outcome",
                "description": "Report the outcome of applying a lesson",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lesson_id": {"type": "string"},
                        "outcome": {"type": "string", "enum": ["success", "failed", "improved", "worse"]},
                        "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        ]
