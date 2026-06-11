"""Lesson Store — 检索、冲突检测、过期处理"""

from datetime import datetime, timezone
from typing import Any, Optional

from orp.schema import Lesson, LessonStatus, check_lesson_conflict
from orp.storage import ORPStorage


class LessonStore:
    """Lesson 存储与检索"""

    def __init__(self, storage: Optional[ORPStorage] = None):
        self._storage = storage or ORPStorage()

    def retrieve(self, task: str, limit: int = 3,
                 status: LessonStatus = LessonStatus.ACTIVE,
                 domain: Optional[str] = None) -> list[Lesson]:
        """检索与当前任务相关 Lesson
        
        排序信号: 语义相关性 → 验证等级 → 历史有效性
        """
        candidates = self._storage.list_lessons(status=status, limit=50)
        
        # 过滤过期
        now = datetime.now(timezone.utc)
        candidates = [l for l in candidates if not l.expires_at or l.expires_at > now]
        
        # 按相关性评分排序
        scored = []
        task_lower = task.lower()
        for lesson in candidates:
            score = self._relevance_score(lesson, task_lower, domain)
            if score > 0:
                scored.append((score, lesson))
        
        scored.sort(key=lambda x: -x[0])
        return [lesson for _, lesson in scored[:limit]]

    def _relevance_score(self, lesson: Lesson, task: str, domain: Optional[str] = None) -> float:
        """计算 Lesson 与任务的语义相关性分数"""
        score = 0.0
        # 领域匹配
        if domain and domain in lesson.scope.get("task_domains", []):
            score += 3.0
        
        # 条件匹配
        for condition in lesson.trigger.get("conditions", []):
            if any(word in task for word in condition.lower().split()):
                score += 2.0
            if condition.lower() in task:
                score += 4.0
        
        # 验证等级加权
        validation_level = lesson.validation.get("level", "asserted")
        level_bonus = {
            "asserted": 0.5, "observed": 1.0, "reproduced": 1.5,
            "externally_verified": 2.0, "human_confirmed": 2.5,
            "regression_guarded": 3.0,
        }
        score += level_bonus.get(validation_level, 0.5)
        
        # 历史效果
        effect = lesson.metrics.get("estimated_effect")
        if effect is not None and effect > 0:
            score += min(effect * 2, 2.0)
        
        return score

    def check_expired(self) -> list[Lesson]:
        """找出所有过期的 Lesson 并自动 deprecated"""
        now = datetime.now(timezone.utc)
        expired = []
        for lesson in self._storage.list_lessons(status=LessonStatus.ACTIVE):
            if lesson.expires_at and lesson.expires_at < now:
                self._storage.update_lesson_status(
                    lesson.lesson_id, LessonStatus.DEPRECATED
                )
                lesson.status = LessonStatus.DEPRECATED
                expired.append(lesson)
        return expired

    def validate_lesson(self, lesson_id: str) -> list[str]:
        """验证一条 Lesson 的完整性"""
        lesson = self._storage.get_lesson(lesson_id)
        if not lesson:
            return ["Lesson not found"]
        issues = []
        if not lesson.recommendation:
            issues.append("Missing recommendation")
        if not lesson.trigger.get("conditions"):
            issues.append("Missing trigger conditions")
        if not lesson.scope.get("task_domains"):
            issues.append("Missing task_domains in scope")
        return issues
