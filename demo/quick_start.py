"""最简单的 ORP 接入演示 — 10秒跑通完整闭环"""

from orp.schema import (
    ExperienceRecord, TimelineEvent, EventKind, Outcome,
    Lesson, LessonStatus,
)
from orp.storage import ORPStorage
from orp.compiler import ExperienceCompiler
from orp.mcp_server import MCPServer
from orp.delivery import DeliveryRouter, DeliveryStrategy
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    storage = ORPStorage(base_dir=tmpdir)

    # 1. 记录一次 Agent 失败
    exp = ExperienceRecord(
        agent={"id": "my-agent", "model": "deepseek-v4-flash"},
        task={"goal": "修复登录页面", "domain": "coding"},
        timeline=[
            TimelineEvent(kind="observation",
                content="pytest: 1 failed, 34 passed", source="tool"),
            TimelineEvent(kind="claim",
                content="修复完成了", source="agent"),
            TimelineEvent(kind="observation",
                content="测试结果: 匿名用户路径仍然失败", source="tool"),
            TimelineEvent(kind="outcome",
                content="failed", source="system"),
        ],
        outcome=Outcome(status="failed"),
    )
    storage.save_experience(exp)
    print("1. ✅ Experience 已保存")

    # 2. ORP 自动编译出 Lesson
    arts = ExperienceCompiler().compile(exp)
    lesson = arts["lessons"][0]
    lesson.recommendation = "修改认证逻辑后，必须覆盖匿名/已登录/无权限三类路径的测试"
    lesson.status = LessonStatus.ACTIVE
    storage.save_lesson(lesson)
    print(f"2. ✅ Lesson 已生成: {lesson.recommendation[:30]}...")

    # 3. 启动 MCP — Agent 查询 Lesson
    mcp = MCPServer(storage)
    result = mcp.handle_call("orp_retrieve_lessons",
                             {"task": "修复登录", "limit": 3})
    print(f"3. ✅ Agent 查询到 {result['count']} 条 Lesson")
    for r in result["lessons"]:
        print(f"   → {r['recommendation']}")

    # 4. Agent 确认收到
    mcp.handle_call("orp_acknowledge_lesson",
                    {"lesson_id": lesson.lesson_id})
    print(f"4. ✅ Agent 确认收到 Lesson {lesson.lesson_id[:12]}...")

    # 5. Agent 报告效果
    mcp.handle_call("orp_report_outcome",
                    {"lesson_id": lesson.lesson_id,
                     "outcome": "success",
                     "evidence_refs": ["test:anonymous_user_path"]})
    print("5. ✅ Agent 报告效果: success")

    storage.close()
    print("\n🎉 完整闭环完成")
    print("Experience → Lesson → MCP retrieve → Acknowledge → Report outcome")
    print(f"\nLesson ID: {lesson.lesson_id}")
    print(f"Lesson 内容: {lesson.recommendation}")
