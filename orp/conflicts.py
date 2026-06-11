"""Conflict Defender — Lesson 作用域与冲突检测"""

from typing import Optional

from orp.schema import Lesson, LessonStatus, check_lesson_conflict
from orp.storage import ORPStorage


class ConflictDefender:
    """冲突防御 — 激活 Lesson 前执行检查"""

    def __init__(self, storage: Optional[ORPStorage] = None):
        self._storage = storage or ORPStorage()

    def check_new_lesson(self, new_lesson: Lesson) -> list[dict[str, str]]:
        """检查新 Lesson 与现有 active Lesson 的冲突"""
        conflicts = []
        active = self._storage.list_lessons(status=LessonStatus.ACTIVE)
        for existing in active:
            if existing.lesson_id == new_lesson.lesson_id:
                continue
            if check_lesson_conflict(new_lesson, existing):
                if self._are_contradictory(new_lesson.recommendation, existing.recommendation):
                    conflicts.append({
                        "type": "contradiction",
                        "existing_id": existing.lesson_id,
                        "existing": existing.recommendation[:100],
                        "new": new_lesson.recommendation[:100],
                    })
        return conflicts

    def _are_contradictory(self, a: str, b: str) -> bool:
        """检查两条建议是否语义相反（简单启发式）"""
        a_lower = a.lower()
        b_lower = b.lower()
        # 检查是否有反义词对
        opposites = [
            ("always", "never"),
            ("must", "must not"),
            ("do", "don't"),
            ("before", "after"),
            ("first", "last"),
        ]
        for a_word, b_word in opposites:
            has_a = a_word in a_lower
            has_b = b_word in b_lower
            if has_a and has_b:
                return True
        return False

    def auto_review_conflicts(self) -> list[str]:
        """自动将所有冲突的 Lesson 标记为 under_review"""
        reviewed: list[str] = []
        active = self._storage.list_lessons(status=LessonStatus.ACTIVE)
        for a in active:
            for b in active:
                if a.lesson_id >= b.lesson_id:
                    continue
                if check_lesson_conflict(a, b) and self._are_contradictory(a.recommendation, b.recommendation):
                    self._storage.update_lesson_status(b.lesson_id, LessonStatus.UNDER_REVIEW)
                    reviewed.append(b.lesson_id)
        return reviewed
