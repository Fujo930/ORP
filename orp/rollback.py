"""Rollback Manager — Lesson 降级、撤回与恢复"""

from typing import Optional

from orp.schema import (
    Lesson, LessonRollback, LessonStatus,
)
from orp.storage import ORPStorage


class RollbackManager:
    """回滚管理 — 坏 Lesson 的审计撤回"""

    def __init__(self, storage: Optional[ORPStorage] = None):
        self._storage = storage or ORPStorage()

    def rollback(self, lesson_id: str, reason: str,
                 new_status: LessonStatus = LessonStatus.UNDER_REVIEW,
                 replacement_id: Optional[str] = None) -> Optional[LessonRollback]:
        """撤回一条 Lesson
        
        默认进入 under_review 而非直接 rejected，保留复审机会。
        """
        lesson = self._storage.get_lesson(lesson_id)
        if not lesson:
            return None
        
        previous = lesson.status
        rollback = LessonRollback(
            lesson_id=lesson_id,
            reason=reason,
            previous_status=previous,
            new_status=new_status,
            replacement_lesson_id=replacement_id,
            affected_deliveries=[
                d.delivery_id
                for d in self._storage.get_deliveries_for_lesson(lesson_id)
            ],
        )
        
        # 更新 Lesson 状态
        self._storage.update_lesson_status(lesson_id, new_status)
        # 保存回滚记录
        self._storage.save_rollback(rollback)
        
        # 如果是 POLICY_FILE 交付的，尝试从 AGENTS.md 移除
        if previous == LessonStatus.ACTIVE:
            self._cleanup_policy_file(lesson_id)
        
        return rollback

    def restore(self, lesson_id: str) -> bool:
        """将 under_review 的 Lesson 恢复到 active"""
        lesson = self._storage.get_lesson(lesson_id)
        if not lesson or lesson.status != LessonStatus.UNDER_REVIEW:
            return False
        self._storage.update_lesson_status(lesson_id, LessonStatus.ACTIVE)
        return True

    def _cleanup_policy_file(self, lesson_id: str) -> None:
        """从 AGENTS.md 中移除指定 Lesson 相关的区块"""
        import os
        try:
            agents_path = os.path.join(os.getcwd(), "AGENTS.md")
            if not os.path.exists(agents_path):
                return
            with open(agents_path, "r") as f:
                content = f.read()
            start_marker = f"<!-- ORP Lesson: {lesson_id} -->"
            end_marker = "<!-- END ORP Lesson -->"
            start = content.find(start_marker)
            if start == -1:
                return
            end = content.find(end_marker, start)
            if end == -1:
                return
            end += len(end_marker)
            new_content = content[:start] + content[end:]
            with open(agents_path, "w") as f:
                f.write(new_content)
        except (IOError, PermissionError, FileNotFoundError):
            pass
