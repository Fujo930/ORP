# ORP 参考实现架构 v0.3

> 目标：AI 在一天内完成完整 v0.1；用户通过一条命令让现有 Agent 获得经验学习能力。

## 1. 产品形态

ORP 不是新的 tracing 后端。它是运行在现有 trace 之上的本地经验编译器。

```text
Agent / Existing Trace
        |
        v
  Trace Adapters
        |
        v
 Experience Builder
        |
        +--> Evidence Verifier
        +--> Reflection Analyzer
        +--> Counterfactual Replayer
        |
        v
 Experience Compiler
   +----+----+------+
   |         |      |
 Lesson     Eval  Guardrail
   |         |      |
   +---- Delivery Router
             |
             v
          Agent Run
             |
             v
    Effect Evaluator + Rollback
```

## 2. 一条命令接入

零代码接入：

```bash
orp wrap -- python my_agent.py
```

自动记录已有 OpenTelemetry、标准输出、退出码、测试结果和 Git diff。

Python 接入：

```python
import orp

orp.autolog()
```

显式 API：

```python
from orp import Experience

with Experience(goal="修复登录错误") as exp:
    result = agent.run()
    exp.outcome(result)
```

## 3. 模块划分

```text
orp/
├── schema.py              # Pydantic 模型与 JSON Schema
├── capture.py             # 进程、工具、测试与 OTel 捕获
├── adapters/
│   ├── otel.py
│   ├── openai_agents.py
│   ├── langgraph.py
│   └── generic_json.py
├── experience.py          # 从 trace 构建 ExperienceRecord
├── evidence.py            # 哈希、引用、可信等级、脱敏
├── reflect.py             # 诊断、替代策略、局限性
├── replay.py              # 沙箱反事实回放
├── compiler.py            # 生成 Lesson / Eval / Guardrail
├── lessons.py             # 检索、冲突处理、过期与淘汰
├── delivery.py            # MCP/prompt/policy/runtime hook 交付
├── conflicts.py           # Lesson 作用域与冲突检测
├── effects.py             # 分级效果评估
├── rollback.py            # 降级、撤回与恢复
├── training.py            # 生成待审批 TrainingCandidate
├── mcp_server.py          # 推荐的 Lesson 查询适配器
├── storage.py             # SQLite + artifact directory
├── export.py              # ORP JSON / OTLP refs / eval files
├── cli.py
└── viewer.py              # 本地 HTML 报告
```

## 4. 核心流水线

### 4.1 捕获

优先捕获可观察数据：

- Agent、模型和工具 span。
- 命令、退出码、测试结果。
- 修改前后 Git diff。
- 用户反馈和人工确认。
- 可选的模型 reasoning summary。

reasoning summary 必须标记为 `claim`，不作为自动验证的事实来源。

### 4.2 Experience Builder

将异构 trace 统一为 `ExperienceRecord`：

```python
record = ExperienceBuilder().from_trace(trace)
record = Redactor().apply(record)
record = EvidenceLinker().link(record)
```

### 4.3 Reflection Analyzer

Analyzer 输出结构化候选，不直接修改 Agent：

```python
ReflectionCandidate(
    diagnosis="遗漏匿名用户路径",
    alternatives=["先创建回归测试"],
    limitations=["未检查其他公开端点"],
    evidence_refs=[...],
)
```

允许多个 Analyzer 并行：

- 执行 Agent 自评。
- Challenger Agent 质疑。
- 确定性规则检查。
- 人工反馈。

### 4.4 Experience Compiler

Compiler 把候选经验编译为可执行资产：

```text
Diagnosis -> Lesson candidate
Failure fixture -> Regression Eval
Repeated unsafe action -> Guardrail candidate
Alternative strategy -> Replay experiment
```

生成物默认处于 `candidate` 状态。只有通过测试、人工确认或后续效果验证后才能激活。

### 4.5 Counterfactual Replay

Replay 在隔离环境中重跑：

```bash
orp replay exp_01 --strategy alternative_1
```

比较：

- 任务成功率。
- 测试通过率。
- 工具调用数量。
- Token、时间和成本。
- 新增副作用。

无法实际回放时，只能输出 `predicted`，不得标记为已验证。

### 4.6 Lesson Retrieval

任务开始时检索少量相关 Lesson：

```python
lessons = store.retrieve(
    task=task,
    limit=3,
    status="active",
)
```

排序信号：

- 语义相关性。
- 适用范围匹配。
- 验证等级。
- 历史有效性。
- 最近使用结果。
- 冲突与过期状态。

### 4.7 Lesson Delivery

检索后的 Lesson 通过 Delivery Router 交付：

```python
delivery = router.deliver(
    lessons=lessons,
    strategy="mcp_tool",
    run=current_run,
)
```

交付策略：

- MCP Server：Agent 主动调用 `orp_retrieve_lessons` 和 `orp_report_outcome`。
- Prompt Context：自动加入系统提示词或任务上下文。
- Policy File：同步到 `AGENTS.md` 等规则文件，并保留可回滚区块。
- Runtime Hook：在高风险动作前注入。

每次交付都必须记录 `delivered / acknowledged / applied`，并尽可能引用应用证据。

MCP Server 示例：

```bash
orp mcp-server --transport stdio
```

提供工具：

```text
orp_retrieve_lessons(task, limit, scope)
orp_acknowledge_lesson(lesson_id)
orp_report_outcome(lesson_id, outcome, evidence_refs)
```

### 4.8 Conflict Defender

激活 Lesson 前执行：

1. 作用域匹配。
2. 与 active Lesson 的语义冲突检测。
3. 检查是否替代旧 Lesson。
4. 检查模型、框架和任务分布是否发生变化。

冲突 Lesson 默认进入 `under_review`，而不是让 Agent 同时接收矛盾指令。

### 4.9 Effect Evaluator

每次 Lesson 被展示和应用后记录真实结果：

```text
retrieved -> delivered -> acknowledged -> applied -> outcome
```

效果计算分三层：

- 描述统计：用于低样本量阶段，不声称因果关系。
- 匹配基线：控制任务类型、难度、Agent 和模型版本。
- 随机/因果实验：A/B 测试或记录完整假设的贝叶斯分层模型。

无效、过期或造成负面影响的 Lesson 自动降权并进入复审；回滚必须留下审计记录。

### 4.10 Training Candidate Pipeline

经验证的 Experience 可以生成待审批候选：

```text
Successful verified trace -> SFT candidate
Failed trace + verified alternative -> preference-pair candidate
Successful challenge -> critique/revision candidate
Guardrail trigger -> negative-example candidate
```

只有结果、隐私、许可和人工审查全部通过后才能导出为 approved candidate。

## 5. 存储

默认本地目录：

```text
.orp/
├── orp.db
├── artifacts/
├── evals/
├── reports/
└── config.toml
```

SQLite 保存索引和结构化记录；大内容保存为 artifact，并由 SHA-256 引用。可以选择只保存哈希和摘要。

## 6. CLI

```bash
orp wrap -- python agent.py
orp inspect latest
orp learn latest
orp replay latest --all
orp lessons list
orp lessons validate lesson_01
orp lessons conflicts
orp lessons rollback lesson_01
orp mcp-server --transport stdio
orp eval run --all
orp effects evaluate lesson_01 --method matched-baseline
orp training candidates
orp training export --approved-only
orp diff exp_before exp_after
orp report --open
orp export latest --format json
```

其中 `orp learn` 执行：

1. 构建 Experience。
2. 生成候选诊断。
3. 挑战未经证明的声明。
4. 生成 Lesson、Eval 与 Guardrail 候选。
5. 尝试回放验证。
6. 输出本地报告。

## 7. 一天实现计划

### 上午：完整骨架

- Schema、SQLite、artifact store。
- Generic JSON 与 OpenTelemetry 导入。
- `wrap`、`inspect`、`learn`、`report` CLI。
- 规则验证、脱敏和 HTML 报告。

### 下午：差异化能力

- Challenger 分析。
- Lesson/Eval/Guardrail 编译器。
- MCP Lesson Server 与 Delivery Router。
- 冲突检测、复审和回滚。
- 描述统计与匹配基线效果分析。
- TrainingCandidate 导出。
- Coding Agent 的 pytest 回归测试生成。
- Replay 与 before/after diff。
- OpenAI Agents 与 LangGraph adapter。
- 示例、测试和文档。

AI 可以在一天内生成并测试该参考实现。一天后的关键任务不是继续堆代码，而是用真实任务判断哪些能力有效。

## 8. 非目标

- 不训练基础模型；只导出经过审批的训练候选。
- 不保证模型自述推理忠实。
- 不自行替代 OpenTelemetry、MLflow、LangSmith 或其他后端。
- 不把 LLM judge 分数当作确定事实。
- 不自动把未经验证的 Lesson 注入生产 Agent。

## 9. 来源与设计依据

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)：OTel 是供应商中立的遥测采集与导出框架。
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)：提供 GenAI 模型与 Agent 的语义约定。
- [OpenAI Agents SDK Observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability)：OpenAI Agents SDK 已内置模型调用、工具调用、handoff 与 guardrail tracing。
- [MLflow GenAI Tracing](https://mlflow.org/docs/latest/genai/tracing/)：展示了兼容 OpenTelemetry 的 tracing、反馈、评估和数据集工作流。
- [LangSmith Complex Agent Evaluation](https://docs.langchain.com/langsmith/evaluate-complex-agent)：区分最终响应、trajectory 与单步评估。
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/)：MCP 可作为 Agent 主动检索和回报 Lesson 使用结果的推荐适配器。
- [MLflow Building Evaluation Datasets](https://mlflow.org/docs/latest/genai/datasets/)：训练与评估数据资产需要明确标签、ground truth 与来源。
