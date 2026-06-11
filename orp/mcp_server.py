"""MCP Lesson Server — 通过 MCP 协议让 Agent 查询和回报 Lesson

提供工具:
- orp_retrieve_lessons(task, limit, scope)
- orp_acknowledge_lesson(lesson_id)
- orp_report_outcome(lesson_id, outcome, evidence_refs)
"""

import json
import sys
from typing import Any, Optional

from orp.schema import LessonStatus, DeliveryStrategy
from orp.storage import ORPStorage
from orp.lessons import LessonStore
from orp.delivery import DeliveryRouter


class MCPServer:
    """MCP Lesson Server — 通过 stdio 或 HTTP 提供 MCP 工具"""

    def __init__(self, storage: Optional[ORPStorage] = None,
                 transport: str = "stdio"):
        self.transport = transport
        self._store = LessonStore(storage)
        self._router = DeliveryRouter(storage)

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """返回 MCP 工具定义（符合 MCP 规范）"""
        return [
            {
                "name": "orp_retrieve_lessons",
                "description": "Retrieve relevant lessons for a task. Call at the START of a task to learn from past experiences.",
                "parameters": {
                    "type": "object",
                    "required": ["task"],
                    "properties": {
                        "task": {"type": "string", "description": "The task description to find relevant lessons for"},
                        "limit": {"type": "integer", "description": "Max lessons to return", "default": 3},
                        "domain": {"type": "string", "description": "Optional domain filter (e.g. coding, research)"},
                    },
                },
            },
            {
                "name": "orp_acknowledge_lesson",
                "description": "Confirm that a lesson has been received and understood. Call after receiving a lesson.",
                "parameters": {
                    "type": "object",
                    "required": ["lesson_id"],
                    "properties": {
                        "lesson_id": {"type": "string", "description": "The lesson ID to acknowledge"},
                    },
                },
            },
            {
                "name": "orp_report_outcome",
                "description": "Report whether applying a lesson improved the outcome. Call at the END of a task.",
                "parameters": {
                    "type": "object",
                    "required": ["lesson_id", "outcome"],
                    "properties": {
                        "lesson_id": {"type": "string", "description": "The lesson ID that was applied"},
                        "outcome": {"type": "string", "enum": ["success", "failed", "improved", "worse"],
                                    "description": "Did the lesson help?"},
                        "evidence_refs": {
                            "type": "array", "items": {"type": "string"},
                            "description": "Optional evidence references (test results, git diff, etc.)",
                        },
                    },
                },
            },
        ]

    def handle_call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """处理 MCP 工具调用"""
        if tool_name == "orp_retrieve_lessons":
            task = arguments.get("task", "")
            limit = arguments.get("limit", 3)
            domain = arguments.get("domain")
            lessons = self._store.retrieve(
                task=task, limit=limit,
                domain=domain,
            )
            return {
                "lessons": [
                    {
                        "lesson_id": l.lesson_id,
                        "recommendation": l.recommendation,
                        "status": l.status.value,
                        "validation_level": l.validation.get("level", "asserted"),
                        "scope": l.scope,
                    }
                    for l in lessons
                ],
                "count": len(lessons),
            }

        elif tool_name == "orp_acknowledge_lesson":
            lesson_id = arguments.get("lesson_id", "")
            lesson = self._store._storage.get_lesson(lesson_id)
            if lesson:
                lesson.metrics["acknowledged"] = lesson.metrics.get("acknowledged", 0) + 1
                self._store._storage.save_lesson(lesson)
                return {"status": "acknowledged", "lesson_id": lesson_id}
            return {"status": "error", "message": "Lesson not found"}

        elif tool_name == "orp_report_outcome":
            lesson_id = arguments.get("lesson_id", "")
            outcome = arguments.get("outcome", "")
            evidence_refs = arguments.get("evidence_refs", [])
            self._router.report_outcome(lesson_id, outcome, evidence_refs)
            return {"status": "recorded", "lesson_id": lesson_id, "outcome": outcome}

        return {"status": "error", "message": f"Unknown tool: {tool_name}"}

    def run_stdio(self) -> None:
        """通过 stdio 运行 MCP Server（符合 MCP 协议）"""
        # MCP 初始化
        init_msg = json.dumps({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {
                    "tools": {},
                },
                "clientInfo": {"name": "orp-mcp-server", "version": "0.3.0"},
            },
        })
        sys.stdout.write(f"Content-Length: {len(init_msg)}\r\n\r\n{init_msg}")
        sys.stdout.flush()

        # 发送工具列表
        tool_msg = json.dumps({
            "jsonrpc": "2.0",
            "method": "notifications/tools/list_changed",
            "params": {"tools": self.get_tool_definitions()},
        })
        sys.stdout.write(f"Content-Length: {len(tool_msg)}\r\n\r\n{tool_msg}")
        sys.stdout.flush()

        # 主循环
        buffer = ""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                buffer += line
                if "\r\n\r\n" in buffer:
                    parts = buffer.split("\r\n\r\n", 1)
                    body = parts[1]
                    buffer = ""
                    try:
                        request = json.loads(body)
                        if request.get("method") == "tools/call":
                            result = self.handle_call(
                                request["params"]["name"],
                                request["params"].get("arguments", {}),
                            )
                            response = json.dumps({
                                "jsonrpc": "2.0",
                                "id": request.get("id"),
                                "result": result,
                            })
                            sys.stdout.write(f"Content-Length: {len(response)}\r\n\r\n{response}")
                            sys.stdout.flush()
                    except json.JSONDecodeError:
                        pass
            except (EOFError, KeyboardInterrupt):
                break
