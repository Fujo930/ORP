# ORP 协议规范 v0.3 草案

> Open Reflection Protocol：让 Agent 将一次运行转化为可验证、可复用、可淘汰的经验。

## 1. 定位与边界

ORP 不宣称记录模型真实的内部推理。它记录：

- 可观察事实：输入、输出、工具调用、测试结果、环境状态。
- Agent 声明：诊断、计划、推理摘要、置信度。
- 外部评价：规则、测试、其他模型、人工审查。
- 可执行经验：回归测试、守卫规则、可检索 Lesson。
- 经验效果：Lesson 被使用后，是否真正改善结果。

必须区分事实与声明。模型提供的推理摘要不得自动视为事实或审计证据。

## 2. 设计原则

1. **Evidence first**：结论必须引用证据；没有证据时明确标记为声明。
2. **Executable reflection**：反思优先编译为 Eval、Guardrail 或 Lesson，而不是只生成文字。
3. **Outcome based**：经验价值由后续任务结果决定，不由模型自评决定。
4. **Interoperable**：ORP 是 OpenTelemetry GenAI trace 的扩展 Profile，不替代 tracing 系统。
5. **Local first**：默认本地存储、默认脱敏、默认不上传完整 Prompt 与工具输出。
6. **Easy adoption**：允许从现有 trace 自动生成记录，不要求开发者手写推理步骤。

## 3. 核心对象

### 3.1 ExperienceRecord

一次 Agent 运行及其复盘结果。

```yaml
orp_version: "0.3"
experience_id: "exp_01..."
trace_ref: "otel-trace-id"
agent:
  id: "coding-agent"
  version: "git-sha-or-semver"
  model: "provider/model"
task:
  goal: "修复匿名用户访问时报错的问题"
  domain: "coding"
  input_ref: "sha256:..."
timeline:
  - id: "evt_1"
    kind: "observation"
    source: "tool"
    content: "pytest: 1 failed, 34 passed"
    evidence_refs: ["artifact:test-output"]
  - id: "evt_2"
    kind: "claim"
    source: "agent"
    content: "失败原因是匿名用户路径缺少空值处理"
    evidence_refs: ["artifact:test-output", "file:UserController.java:45"]
outcome:
  status: "failed"
  objective_signals:
    - name: "test_pass_rate"
      value: 0.971
reflection:
  diagnosis: "修改只覆盖已登录用户"
  alternatives:
    - "先运行匿名用户测试"
  limitations:
    - "尚未确认其他公开端点"
artifacts:
  lessons: ["lesson_01..."]
  evals: ["eval_01..."]
  guardrails: []
```

### 3.2 TimelineEvent

`kind` 必须为以下之一：

| 类型 | 含义 | 默认可信等级 |
|---|---|---|
| `observation` | 工具、环境或外部系统产生的可观察结果 | observed |
| `action` | Agent 或用户执行的动作 | observed |
| `claim` | Agent 对原因、状态或未来结果的声明 | asserted |
| `decision` | Agent 在多个方案间做出的选择 | asserted |
| `feedback` | 人工、规则、模型或用户评价 | 按来源确定 |
| `outcome` | 测试、验收、生产指标等结果 | observed |

### 3.3 EvidenceRef

证据引用必须尽可能可定位、可校验。

```yaml
evidence_id: "artifact:test-output"
kind: "tool_output"
uri: "file://local-artifacts/test-output.txt"
digest: "sha256:..."
created_at: "2026-06-11T20:00:00Z"
redaction:
  applied: true
  policy: "default"
```

证据可只保存摘要与哈希。协议不要求跨系统公开原始敏感数据。

### 3.4 Lesson

Lesson 是可以在未来任务中检索的条件化经验。

```yaml
lesson_id: "lesson_01..."
trigger:
  domain: "coding"
  conditions:
    - "修改认证或授权逻辑"
recommendation: "必须测试匿名、已登录和无权限三类路径"
provenance:
  experience_ids: ["exp_01..."]
validation:
  level: "regression_guarded"
  evidence_refs: ["eval:eval_01..."]
scope:
  task_domains: ["coding"]
  frameworks: ["spring-security"]
  agent_versions: [">=1.4,<2.0"]
relationships:
  conflicts_with: []
  supersedes: []
status: "active"
expires_at: "2026-12-11T00:00:00Z"
```

Lesson 状态：

- `candidate`：由单次经验生成，尚未验证。
- `active`：至少通过一次外部验证，可以被检索。
- `under_review`：发现冲突、负面效果或适用范围不明，暂停默认交付。
- `deprecated`：效果不佳、冲突或过期。
- `rejected`：被证明错误。

Lesson 必须声明适用范围。两条建议文本相反但适用范围不同，不应自动判定为冲突。

### 3.5 EvalArtifact

将失败转换为可重复执行的评估。

```yaml
eval_id: "eval_01..."
origin_experience: "exp_01..."
runner: "pytest"
command: "pytest tests/test_anonymous_access.py -q"
expected:
  exit_code: 0
generated_by: "agent"
review:
  status: "human_approved"
last_result:
  status: "passed"
  evidence_ref: "artifact:eval-output"
```

### 3.6 CounterfactualReplay

记录替代策略是否在同一任务或隔离环境中得到验证。

```yaml
replay_id: "replay_01..."
experience_id: "exp_01..."
original_strategy: "直接修改实现后提交"
alternative_strategy: "先补匿名用户回归测试，再修改实现"
verification_mode: "sandbox_replay"
result:
  status: "improved"
  objective_delta:
    tests_passed: 1
    tool_calls: -2
```

反事实结果必须注明是 `predicted` 还是 `verified`。

### 3.7 LessonDelivery

记录 Lesson 如何进入 Agent 上下文，以及是否真正被 Agent 采纳和应用。检索不等于交付，交付不等于应用。

```yaml
delivery_id: "delivery_01..."
lesson_id: "lesson_01..."
experience_id: "exp_02..."
strategy: "mcp_tool" # mcp_tool | prompt_context | policy_file | runtime_hook
delivered_at: "2026-06-11T21:00:00Z"
delivery_context: "Agent 正在修改认证控制器"
acknowledged: true
applied: true
application_evidence_refs:
  - "artifact:agent-created-anonymous-user-test"
```

支持的交付方式：

| 策略 | 含义 |
|---|---|
| `mcp_tool` | Agent 主动调用 MCP 工具查询 Lesson |
| `prompt_context` | 运行时将 Lesson 注入系统或任务上下文 |
| `policy_file` | 写入 `AGENTS.md` 等 Agent 可读取的策略文件 |
| `runtime_hook` | 在高风险动作前按条件注入 Lesson |

MCP 是推荐适配器，但 ORP Core 不依赖 MCP。

### 3.8 LessonEvaluation

记录 Lesson 的效果、实验设计、负面证据与处置决定。

```yaml
evaluation_id: "leval_01..."
lesson_id: "lesson_01..."
method: "matched_baseline" # descriptive | matched_baseline | randomized | causal_model
population:
  task_domain: "coding"
  agent_version: "1.5.0"
results:
  with_lesson:
    tasks: 20
    successes: 14
  baseline:
    tasks: 20
    successes: 10
  estimated_effect: 0.20
  uncertainty_interval: [0.03, 0.37]
decision: "keep_active" # keep_active | restrict_scope | review | deprecate | reject
evidence_refs: ["artifact:experiment-report"]
```

效果评估分级：

1. `descriptive`：只记录检索、应用与结果，不声称因果效果。
2. `matched_baseline`：与相似任务、相同 Agent/模型版本的基线比较。
3. `randomized`：通过随机 A/B 实验估计增量效果。
4. `causal_model`：使用贝叶斯分层模型等因果分析方法，并记录假设。

协议不强制某一种统计方法。只有随机实验或合理因果设计才能将结果描述为因果效果。

### 3.9 LessonRollback

坏 Lesson 必须能够限制、撤回和追踪原因。

```yaml
rollback_id: "rollback_01..."
lesson_id: "lesson_01..."
reason: "连续观察到负面效果，且与 lesson_09 冲突"
previous_status: "active"
new_status: "under_review"
affected_deliveries: ["delivery_01..."]
replacement_lesson_id: "lesson_09..."
evidence_refs: ["leval:leval_01..."]
```

### 3.10 TrainingCandidate

ORP 可以将经验转换为潜在训练资产，但不能把成功 Trace 自动视为高质量训练数据。

```yaml
candidate_id: "train_01..."
source_experience_ids: ["exp_01...", "exp_02..."]
format: "preference_pair" # sft_example | preference_pair | critique_revision | negative_example
validation:
  outcome_verified: true
  human_reviewed: true
  privacy_reviewed: true
  license_reviewed: true
status: "approved" # candidate | approved | rejected
artifact_ref: "artifact:training-candidate"
```

未经结果验证、隐私审查和许可审查的候选不得标记为 `approved`。

## 4. Lesson 防御规则

### 4.1 冲突检测

- 比较建议内容前，先比较 `scope`。
- 同范围内相互矛盾的 active Lesson 必须进入 `under_review`。
- 新 Lesson 替代旧 Lesson 时使用 `supersedes`，保留完整来源链。

### 4.2 自动降权与复审

- 负面结果只能触发降权或 `under_review`，不能仅凭固定次数自动永久拒绝。
- 降级决策必须引用 `LessonEvaluation`。
- 模型、框架或任务分布变化时，应重新验证 Lesson。

### 4.3 回滚

- 每次主动撤回必须创建 `LessonRollback`。
- 已注入策略文件或运行时配置的 Lesson 必须支持删除或恢复。
- 被 `rejected` 的 Lesson 默认不得继续交付。

## 5. 可信等级

ORP 不使用缺乏校准依据的单一 `overall_score`。每条重要结论使用以下等级：

| 等级 | 定义 |
|---|---|
| `asserted` | Agent 或其他主体提出，但没有外部证据 |
| `observed` | 被工具输出、环境事件或 trace 观察到 |
| `reproduced` | 在独立重跑中重复出现 |
| `externally_verified` | 被确定性规则、测试或外部系统验证 |
| `human_confirmed` | 被授权人工确认 |
| `regression_guarded` | 已形成持续运行的回归 Eval |

置信度可以作为附加字段，但不得替代可信等级。

## 6. 评估与反馈

每个反馈必须记录评价来源：

```yaml
feedback:
  target_ref: "claim:evt_2"
  source_type: "human" # human | deterministic | llm_judge | user | production_metric
  source_id: "reviewer-or-evaluator-version"
  verdict: "supported"
  explanation: "失败可由新增回归测试稳定复现"
  evidence_refs: ["eval:eval_01..."]
```

LLM-as-judge 的结果只能代表评价信号，不得自动升级为外部事实。

## 7. OpenTelemetry 映射

ORP 复用 OpenTelemetry trace/span，并添加以下逻辑对象：

| ORP 对象 | 推荐映射 |
|---|---|
| ExperienceRecord | 一个 Agent run trace 的派生对象 |
| TimelineEvent | span、span event 或引用 |
| Feedback | `gen_ai.evaluation.result` event 或外部评价记录 |
| EvidenceRef | span attribute、artifact URI 或内容哈希 |
| Lesson/Eval | 与 trace 关联的 ORP artifact |
| LessonDelivery | 与当前 Agent run 关联的交付与应用记录 |
| LessonEvaluation | evaluation event 或独立实验 artifact |

建议属性前缀：

```text
orp.experience.id
orp.event.kind
orp.evidence.level
orp.lesson.id
orp.lesson.status
orp.lesson.delivery.strategy
orp.lesson.delivery.applied
orp.lesson.evaluation.method
orp.eval.id
orp.schema.version
```

## 8. 隐私与安全

- 默认只保存必要数据，完整 Prompt、Completion 和工具输出必须显式启用。
- 支持字段级脱敏、内容哈希、保留期限和删除请求。
- Evidence 不得仅依赖 Agent 自己生成的文本。
- 从外部内容提取 Lesson 时，应标记潜在 Prompt Injection 来源。
- 共享数据前必须移除密钥、PII、仓库私有内容和客户数据。
- TrainingCandidate 在导出前必须完成隐私与许可审查。

## 9. 最小兼容要求

一个实现只有满足以下条件才能声明支持 `ORP Core v0.3`：

1. 可以创建和校验 `ExperienceRecord`。
2. 可以区分 observation、action、claim、feedback 与 outcome。
3. 每个 Lesson 都具有来源、状态、适用范围和验证等级。
4. 可以导入或引用 OpenTelemetry trace。
5. 默认提供脱敏策略。
6. 不将模型推理摘要描述为真实内部推理。
7. 可以记录 Lesson 的交付方式、采纳状态和应用证据。
8. 可以让有害或冲突 Lesson 进入复审并完成回滚。

## 10. 来源与设计依据

- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)：已有 GenAI 模型、Agent、事件与指标语义规范，ORP 应基于它扩展。
- [OpenTelemetry GenAI Agent Spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)：Agent 操作 span 的现有规范。
- [OpenTelemetry GenAI Evaluation Result Event](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-events/)：已有 `gen_ai.evaluation.result` 事件。
- [OpenTelemetry Handling Sensitive Data](https://opentelemetry.io/docs/security/handling-sensitive-data/)：遥测数据应遵循数据最小化原则。
- [OpenAI Reasoning Items Cookbook](https://developers.openai.com/cookbook/examples/responses_api/reasoning_items)：OpenAI API 不暴露原始 Chain-of-Thought，仅可提供摘要。
- [Anthropic: Reasoning Models Don't Always Say What They Think](https://www.anthropic.com/research/reasoning-models-dont-say-think)：模型表达出的推理不一定忠实反映实际原因。
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/)：MCP 可作为 Agent 主动查询 Lesson 的一种通用交付适配器。
- [MLflow Building Evaluation Datasets](https://mlflow.org/docs/latest/genai/datasets/)：区分带有 ground truth 的标注数据集与未标注数据集。
