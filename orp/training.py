"""Training Candidate Pipeline — 经验转训练数据"""

from typing import Any, Optional

from orp.schema import (
    ExperienceRecord, TrainingCandidate, TrainingFormat, TrainingStatus,
)
from orp.storage import ORPStorage


class TrainingPipeline:
    """训练候选管道 — 生成待审批的训练数据"""

    def __init__(self, storage: Optional[ORPStorage] = None):
        self._storage = storage or ORPStorage()

    def create_candidate(self, source_exp: ExperienceRecord,
                         format: TrainingFormat) -> Optional[TrainingCandidate]:
        """从已验证的 Experience 创建训练候选"""
        if source_exp.outcome.status != "success":
            return None  # 只从成功 trace 创建 SFT 候选
        
        tc = TrainingCandidate(
            source_experience_ids=[source_exp.experience_id],
            format=format,
            validation={
                "outcome_verified": source_exp.outcome.status == "success",
                "human_reviewed": False,
                "privacy_reviewed": False,
                "license_reviewed": False,
            },
            status=TrainingStatus.CANDIDATE,
        )
        
        # 生成 artifact
        artifact = self._render_artifact(source_exp, format)
        if artifact:
            artifact_path = f"training_{tc.candidate_id}.jsonl"
            self._storage.save_artifact(artifact_path, artifact)
            tc.artifact_ref = f"artifact:{artifact_path}"
        
        self._storage.save_training_candidate(tc)
        return tc

    def approve(self, candidate_id: str,
                human_reviewed: bool = True,
                privacy_reviewed: bool = True,
                license_reviewed: bool = True) -> bool:
        """审批训练候选（四重审批）"""
        for tc in self._storage.list_training_candidates():
            if tc.candidate_id == candidate_id:
                tc.validation["human_reviewed"] = human_reviewed
                tc.validation["privacy_reviewed"] = privacy_reviewed
                tc.validation["license_reviewed"] = license_reviewed
                all_ok = all(tc.validation.values())
                tc.status = TrainingStatus.APPROVED if all_ok else TrainingStatus.CANDIDATE
                self._storage.save_training_candidate(tc)
                return all_ok
        return False

    def export_approved(self) -> list[dict[str, Any]]:
        """导出所有已审批的训练候选"""
        approved = [
            tc for tc in self._storage.list_training_candidates()
            if tc.status == TrainingStatus.APPROVED
        ]
        results = []
        for tc in approved:
            results.append({
                "candidate_id": tc.candidate_id,
                "format": tc.format.value,
                "artifact_ref": tc.artifact_ref,
            })
        return results

    def _render_artifact(self, exp: ExperienceRecord, fmt: TrainingFormat) -> Optional[str]:
        """渲染训练数据 artifact"""
        if fmt == TrainingFormat.SFT_EXAMPLE:
            return self._render_sft(exp)
        elif fmt == TrainingFormat.PREFERENCE_PAIR:
            return self._render_preference(exp)
        return None

    def _render_sft(self, exp: ExperienceRecord) -> str:
        """渲染为 SFT 示例"""
        timeline_text = "\n".join(
            f"[{e.kind.value}] {e.content[:200]}"
            for e in exp.timeline
        )
        return f'{{"messages": [{{"role": "user", "content": "{exp.task.get("goal", "")}"}}, {{"role": "assistant", "content": "{timeline_text}"}}]}}\n'

    def _render_preference(self, exp: ExperienceRecord) -> str:
        """渲染为偏好对（DPO 格式）"""
        return f'{{"prompt": "{exp.task.get("goal", "")}", "chosen": "success", "rejected": "failed"}}\n'
