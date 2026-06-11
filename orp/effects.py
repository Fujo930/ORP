"""Effect Evaluator — 分级效果评估

评估方法分级:
1. descriptive: 仅记录检索/应用/结果，不声称因果
2. matched_baseline: 匹配相似任务/Agent/模型版本的基线
3. randomized: A/B 实验
4. causal_model: 贝叶斯分层等因果方法
"""

from typing import Any, Optional

from orp.schema import (
    Lesson, LessonEvaluation, EvaluationMethod, LessonStatus,
)
from orp.storage import ORPStorage


class EffectEvaluator:
    """Lesson 效果评估"""

    def __init__(self, storage: Optional[ORPStorage] = None):
        self._storage = storage or ORPStorage()

    def describe(self, lesson: Lesson) -> LessonEvaluation:
        """Descriptive 评估 — 仅记录统计"""
        m = lesson.metrics
        return LessonEvaluation(
            lesson_id=lesson.lesson_id,
            method=EvaluationMethod.DESCRIPTIVE,
            population={"agent_version": lesson.scope.get("agent_versions", [])},
            results={
                "with_lesson": {
                    "tasks": m.get("retrieved", 0),
                    "successes": m.get("successful_after_apply", 0),
                },
                "baseline": {"tasks": 0, "successes": 0},
                "estimated_effect": None,
                "uncertainty_interval": None,
            },
            decision="keep_active",
        )

    def evaluate_matched_baseline(self, lesson: Lesson,
                                  baseline_success_rate: float = 0.5,
                                  baseline_tasks: int = 1) -> LessonEvaluation:
        """Matched Baseline 评估 — 与基线比较"""
        m = lesson.metrics
        applied = m.get("applied", 0)
        successes = m.get("successful_after_apply", 0)
        
        with_rate = successes / applied if applied > 0 else 0
        raw_effect = with_rate - baseline_success_rate
        
        return LessonEvaluation(
            lesson_id=lesson.lesson_id,
            method=EvaluationMethod.MATCHED_BASELINE,
            population={
                "agent_version": lesson.scope.get("agent_versions", []),
                "baseline_source": "matched_tasks",
            },
            results={
                "with_lesson": {
                    "tasks": applied,
                    "successes": successes,
                    "success_rate": round(with_rate, 3),
                },
                "baseline": {
                    "tasks": baseline_tasks,
                    "successes": int(baseline_tasks * baseline_success_rate),
                    "success_rate": round(baseline_success_rate, 3),
                },
                "estimated_effect": round(raw_effect, 3) if applied > 0 else None,
                "uncertainty_interval": None,
            },
            decision=self._decide(raw_effect, applied),
        )

    def _decide(self, effect: float, sample: int) -> str:
        """基于效果和样本量生成处置建议"""
        if sample < 3:
            return "keep_active"  # 样本太少，不做决定
        if effect > 0.1:
            return "keep_active"
        if effect < -0.1:
            return "review"
        if effect < -0.3:
            return "deprecate"
        return "keep_active"

    def auto_evaluate_all(self) -> list[LessonEvaluation]:
        """对所有 active Lesson 运行 matched_baseline 评估"""
        evaluations = []
        for lesson in self._storage.list_lessons(status=LessonStatus.ACTIVE):
            evals_list = self._storage.conn.execute(
                "SELECT * FROM lesson_evals WHERE lesson_id = ? ORDER BY created_at DESC LIMIT 5",
                (lesson.lesson_id,)
            ).fetchall()
            baseline_rate = 0.5
            if evals_list:
                # 尝试从上次评估获取基线
                for r in evals_list:
                    import json
                    results = json.loads(r["results_json"]) if r["results_json"] else {}
                    baseline = results.get("baseline", {})
                    if baseline.get("success_rate"):
                        baseline_rate = baseline["success_rate"]
                        break
            
            evaluation = self.evaluate_matched_baseline(lesson, baseline_rate)
            self._storage.save_lesson_evaluation(evaluation)
            evaluations.append(evaluation)
        return evaluations
