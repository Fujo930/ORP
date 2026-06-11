# ORP Core Schema v0.3
# 代码即规范 — 此文件中的所有 Pydantic 模型构成 ORP 协议的官方定义
# 
# 设计原则:
# 1. Evidence first: 结论必须引用证据，无证据的标记为 claim
# 2. 区分事实与声明: observation/action 是事实，claim/decision 是声明
# 3. 可执行: 反思优先编译为 Lesson/Eval/Guardrail
# 4. Outcome based: 经验价值由后续任务结果决定
# 5. 基于 OpenTelemetry: 不替代 tracing，而是扩展它

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator, model_validator


# ─── Helpers ─────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _uuid() -> UUID:
    return uuid4()


# ─── Enums ───────────────────────────────────────────────────

class EventKind(str, Enum):
    """TimelineEvent 类型 — 必须区分可观察事实与 Agent 声明"""
    OBSERVATION = "observation"   # 工具/环境/外部系统产生的可观察结果
    ACTION = "action"             # Agent 或用户执行的动作
    CLAIM = "claim"               # Agent 对原因/状态/结果的声明
    DECISION = "decision"         # Agent 在多个方案间做出的选择
    FEEDBACK = "feedback"         # 人工/规则/模型/用户评价
    OUTCOME = "outcome"           # 测试/验收/生产指标等结果


class TrustLevel(str, Enum):
    """可信等级 — 不使用缺乏校准的单一评分"""
    ASSERTED = "asserted"                    # 未经外部证据支持的声明
    OBSERVED = "observed"                    # 被工具/环境/trace 观察到
    REPRODUCED = "reproduced"                # 独立重跑中复现
    EXTERNALLY_VERIFIED = "externally_verified"  # 被规则/测试/系统验证
    HUMAN_CONFIRMED = "human_confirmed"      # 被授权人工确认
    REGRESSION_GUARDED = "regression_guarded" # 已形成持续运行的回归 Eval


class LessonStatus(str, Enum):
    CANDIDATE = "candidate"        # 由单次经验生成，尚未验证
    ACTIVE = "active"              # 通过外部验证，可被检索
    UNDER_REVIEW = "under_review"  # 发现冲突/负面效果，暂停默认交付
    DEPRECATED = "deprecated"      # 效果不佳/冲突/过期
    REJECTED = "rejected"          # 被证明错误


class DeliveryStrategy(str, Enum):
    MCP_TOOL = "mcp_tool"           # Agent 主动调用 MCP 工具
    PROMPT_CONTEXT = "prompt_context"  # 运行时注入系统/任务上下文
    POLICY_FILE = "policy_file"     # 写入 AGENTS.md 等策略文件
    RUNTIME_HOOK = "runtime_hook"   # 高风险动作前条件式注入


class FeedbackSourceType(str, Enum):
    HUMAN = "human"
    DETERMINISTIC = "deterministic"
    LLM_JUDGE = "llm_judge"
    USER = "user"
    PRODUCTION_METRIC = "production_metric"


class EvaluationMethod(str, Enum):
    DESCRIPTIVE = "descriptive"              # 仅记录，不声称因果
    MATCHED_BASELINE = "matched_baseline"    # 与相似任务基线比较
    RANDOMIZED = "randomized"                # A/B 实验
    CAUSAL_MODEL = "causal_model"            # 贝叶斯分层等因果方法


class TrainingFormat(str, Enum):
    SFT_EXAMPLE = "sft_example"
    PREFERENCE_PAIR = "preference_pair"
    CRITIQUE_REVISION = "critique_revision"
    NEGATIVE_EXAMPLE = "negative_example"


class TrainingStatus(str, Enum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"


# ─── Core Objects ────────────────────────────────────────────

class EvidenceRef(BaseModel):
    """证据引用 — 必须可定位、可校验"""
    evidence_id: str
    kind: str = Field(default="tool_output")
    uri: Optional[str] = None
    digest: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    redaction: Optional[dict[str, Any]] = None


class Feedback(BaseModel):
    """外部评价 — 必须记录来源"""
    target_ref: str
    source_type: FeedbackSourceType
    source_id: str
    verdict: str
    explanation: Optional[str] = None
    evidence_refs: list[str] = Field(default_factory=list)


class TimelineEvent(BaseModel):
    """时间线事件 — 推理/操作/观察序列中的一个原子项"""
    id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:8]}")
    kind: EventKind
    source: str = Field(default="agent")  # agent | tool | human | system
    content: str
    evidence_refs: list[str] = Field(default_factory=list)
    parent_event: Optional[str] = None
    timestamp: datetime = Field(default_factory=_now)

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Event content cannot be empty")
        return v


class Outcome(BaseModel):
    """运行结果 — 基于客观信号"""
    status: str = Field(default="unknown")  # success | failed | partial | unknown
    objective_signals: list[dict[str, Any]] = Field(default_factory=list)


class ReflectionAnalysis(BaseModel):
    """反思分析 — Agent 或 Challenger 对运行的结构化复盘"""
    diagnosis: Optional[str] = None
    alternatives: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ExperienceRecord(BaseModel):
    """经验记录 — 一次 Agent 运行及其复盘结果"""
    orp_version: str = Field(default="0.3")
    experience_id: str = Field(default_factory=lambda: f"exp_{uuid4().hex[:12]}")
    trace_ref: Optional[str] = None
    agent: dict[str, Any] = Field(default_factory=lambda: {"id": "unknown", "version": "", "model": ""})
    task: dict[str, Any] = Field(default_factory=lambda: {"goal": "", "domain": "", "input_ref": ""})
    timeline: list[TimelineEvent] = Field(default_factory=list)
    outcome: Outcome = Field(default_factory=Outcome)
    reflection: Optional[ReflectionAnalysis] = None
    artifacts: dict[str, list[str]] = Field(default_factory=lambda: {"lessons": [], "evals": [], "guardrails": []})
    feedback: list[Feedback] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)

    @field_validator("timeline")
    @classmethod
    def timeline_not_empty(cls, v: list[TimelineEvent]) -> list[TimelineEvent]:
        if not v:
            raise ValueError("Timeline must have at least one event")
        return v


class Lesson(BaseModel):
    """课程/经验 — 可在未来任务中检索的条件化经验"""
    lesson_id: str = Field(default_factory=lambda: f"lesson_{uuid4().hex[:12]}")
    trigger: dict[str, Any] = Field(default_factory=lambda: {"domain": "", "conditions": []})
    recommendation: str
    provenance: dict[str, Any] = Field(default_factory=lambda: {"experience_ids": [], "evals": []})
    scope: dict[str, Any] = Field(default_factory=lambda: {
        "task_domains": [], "frameworks": [], "agent_versions": []
    })
    relationships: dict[str, list[str]] = Field(default_factory=lambda: {
        "conflicts_with": [], "supersedes": [], "superseded_by": []
    })
    validation: dict[str, Any] = Field(default_factory=lambda: {"level": "asserted", "evidence_refs": []})
    metrics: dict[str, Any] = Field(default_factory=lambda: {
        "retrieved": 0, "delivered": 0, "acknowledged": 0, "applied": 0,
        "successful_after_apply": 0, "estimated_effect": None
    })
    status: LessonStatus = LessonStatus.CANDIDATE
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class EvalArtifact(BaseModel):
    """评估工件 — 将失败转换为可重复执行的评估"""
    eval_id: str = Field(default_factory=lambda: f"eval_{uuid4().hex[:12]}")
    origin_experience: str
    runner: str = Field(default="pytest")
    command: str
    expected: dict[str, Any] = Field(default_factory=lambda: {"exit_code": 0})
    generated_by: str = Field(default="agent")
    review: Optional[dict[str, Any]] = None
    last_result: Optional[dict[str, Any]] = None
    created_at: datetime = Field(default_factory=_now)


class CounterfactualReplay(BaseModel):
    """反事实回放 — 记录替代策略是否得到了验证"""
    replay_id: str = Field(default_factory=lambda: f"replay_{uuid4().hex[:12]}")
    experience_id: str
    original_strategy: str
    alternative_strategy: str
    verification_mode: str = Field(default="sandbox_replay")  # predicted | sandbox_replay | production
    result: dict[str, Any] = Field(default_factory=lambda: {
        "status": "unknown", "objective_delta": {}
    })
    created_at: datetime = Field(default_factory=_now)


class LessonDelivery(BaseModel):
    """Lesson 交付 — 记录 Lesson 如何进入 Agent 上下文及是否被采纳"""
    delivery_id: str = Field(default_factory=lambda: f"delivery_{uuid4().hex[:12]}")
    lesson_id: str
    experience_id: str
    strategy: DeliveryStrategy
    delivered_at: datetime = Field(default_factory=_now)
    delivery_context: Optional[str] = None
    acknowledged: bool = False
    applied: bool = False
    application_evidence_refs: list[str] = Field(default_factory=list)


class LessonEvaluation(BaseModel):
    """Lesson 效果评估 — 记录效果、实验设计、负面证据与处置"""
    evaluation_id: str = Field(default_factory=lambda: f"leval_{uuid4().hex[:12]}")
    lesson_id: str
    method: EvaluationMethod
    population: dict[str, Any] = Field(default_factory=dict)
    results: dict[str, Any] = Field(default_factory=lambda: {
        "with_lesson": {"tasks": 0, "successes": 0},
        "baseline": {"tasks": 0, "successes": 0},
        "estimated_effect": None,
        "uncertainty_interval": None,
    })
    decision: str = Field(default="keep_active")  # keep_active | restrict_scope | review | deprecate | reject
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)


class LessonRollback(BaseModel):
    """Lesson 回滚 — 坏 Lesson 撤回的审计记录"""
    rollback_id: str = Field(default_factory=lambda: f"rollback_{uuid4().hex[:12]}")
    lesson_id: str
    reason: str
    previous_status: LessonStatus
    new_status: LessonStatus
    affected_deliveries: list[str] = Field(default_factory=list)
    replacement_lesson_id: Optional[str] = None
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)


class TrainingCandidate(BaseModel):
    """训练候选 — 将经验转化为训练资产的审批通道"""
    candidate_id: str = Field(default_factory=lambda: f"train_{uuid4().hex[:12]}")
    source_experience_ids: list[str] = Field(default_factory=list)
    format: TrainingFormat
    validation: dict[str, bool] = Field(default_factory=lambda: {
        "outcome_verified": False,
        "human_reviewed": False,
        "privacy_reviewed": False,
        "license_reviewed": False,
    })
    status: TrainingStatus = TrainingStatus.CANDIDATE
    artifact_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


# ─── High-level Schema Validation ────────────────────────────

def validate_lesson_scope(lesson: Lesson) -> list[str]:
    """检查 Lesson 的作用域定义是否完整"""
    issues = []
    if not lesson.scope.get("task_domains"):
        issues.append("Lesson missing task_domains in scope")
    if not lesson.trigger.get("conditions"):
        issues.append("Lesson missing trigger conditions")
    return issues


def check_lesson_conflict(a: Lesson, b: Lesson) -> bool:
    """检查两条 Lesson 是否有冲突
    
    先比较 scope，再比较建议内容。
    不同 scope 的两条建议即使语义相反也不应判定为冲突。
    """
    # 如果 scope 完全不重叠，不算冲突
    a_domains = set(a.scope.get("task_domains", []))
    b_domains = set(b.scope.get("task_domains", []))
    if a_domains and b_domains and not a_domains & b_domains:
        return False
    a_versions = set(a.scope.get("agent_versions", []))
    b_versions = set(b.scope.get("agent_versions", []))
    if a_versions and b_versions and not a_versions & b_versions:
        return False
    return True
