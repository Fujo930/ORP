# Open Reflection Protocol 路线图 v0.3

> 核心主张：Give your agent a mistake once. ORP helps it prove that it learned.

## 1. 项目目标

ORP 让 Agent 将一次运行自动转化为：

```text
Trace
  -> Experience
  -> Diagnosis candidates
  -> Lesson / Eval / Guardrail
  -> Delivery + Application Evidence
  -> Replay verification
  -> Effect Evaluation + Rollback
```

ORP 的长期价值不是保存更多日志，而是建立跨框架、可验证的 Agent 经验交换格式。

## 2. 差异化能力

| 能力 | 普通 tracing | ORP |
|---|---:|---:|
| 记录模型和工具调用 | 是 | 复用 |
| 区分事实与 Agent 声明 | 通常不强制 | 是 |
| 将失败生成回归 Eval | 部分平台支持 | 核心能力 |
| 生成可检索 Lesson | 部分平台支持 | 核心对象 |
| 反事实回放替代策略 | 少见 | 核心能力 |
| 追踪 Lesson 后续效果 | 少见 | 核心能力 |
| 证明 Lesson 已交付和应用 | 少见 | 核心能力 |
| 检测并撤回坏 Lesson | 少见 | 核心能力 |
| 导出经审批训练候选 | 部分平台支持 | 扩展能力 |
| 开放交换格式 | 有限 | 目标 |

## 3. Day 1：完整 v0.1

AI 在一天内完成可运行参考实现，不刻意缩小代码范围。

交付：

- `ORP Core v0.3` Schema 与 JSON Schema。
- OpenTelemetry、OpenAI Agents、LangGraph、Generic JSON adapter。
- SQLite 与 artifact store。
- 默认脱敏。
- `wrap / inspect / learn / replay / diff / report` CLI。
- Lesson、Eval、Guardrail 编译器。
- MCP Lesson Server 与通用 Delivery Router。
- Lesson 冲突检测、复审与回滚。
- TrainingCandidate 导出。
- Coding Agent pytest Eval 生成。
- 本地 HTML 报告。
- 完整示例与核心测试。

Day 1 成功标准：

```bash
orp wrap -- python examples/failing_coding_agent.py
orp learn latest
orp replay latest --all
```

最终输出至少包含一个 Experience、一个候选 Lesson 和一个可运行 Eval。

## 4. Day 2-7：证明它真的有用

不要优先写论文或推广协议。建立 30-100 个真实 Coding Agent 失败任务：

- 漏测边界条件。
- 修改错误文件。
- 未读取项目约定。
- 过早下结论。
- 重复执行无效工具。
- 修复局部问题但引入回归。

对每个失败运行：

1. 生成 Experience。
2. 生成 Lesson 与 Eval。
3. 通过 MCP、Prompt、Policy File 或 Runtime Hook 交付 Lesson。
4. 记录 Lesson 是否被 Agent 采纳和实际应用。
5. 比较有无 ORP 时的结果。

核心指标：

| 指标 | 定义 |
|---|---|
| Eval validity | 自动生成 Eval 中真正能复现问题的比例 |
| Lesson precision | 被应用的 Lesson 中产生正面影响的比例 |
| Delivery-to-application | 已交付 Lesson 中被实际应用的比例 |
| Repeat failure reduction | 相似错误重复发生率下降幅度 |
| Matched task success delta | 匹配相似任务后，使用 Lesson 的成功率增量 |
| Cost delta | Token、工具调用和时间变化 |

Go/No-Go：

- 若 Lesson 无法稳定改善结果，弱化“Agent 学习”叙事。
- 若 Eval 生成有效但 Lesson 效果弱，聚焦“失败转回归测试”。
- 若 replay 成本过高，仅用于高价值失败。
- 若无法证明 Lesson 被应用，不把结果变化归因于 Lesson。

## 5. Day 8-14：推广就绪

### 开发者体验

- 发布 PyPI 包与单文件 Demo。
- 提供 GitHub Action。
- 提供 MCP Lesson Server 配置示例。
- 支持导入 MLflow、LangSmith、Phoenix 或原始 OTLP trace。
- 生成可分享但默认脱敏的静态报告。

### 杀手级 Demo

演示同一 Agent：

1. 第一次遗漏匿名用户路径并失败。
2. ORP 自动生成回归 Eval 与 Lesson。
3. 第二个相似任务开始时通过 MCP 查询 Lesson。
4. ORP 记录 Agent 已采纳并创建了对应测试。
5. Agent 主动补充边界测试并成功。
6. 报告显示匹配基线、成功率、工具调用和成本差异。
7. 演示坏 Lesson 被检测、暂停交付并回滚。

### 推广语

主宣传语：

> Turn every agent failure into a regression test and a measured lesson.

辅助说明：

> ORP is an open experience layer for AI agents, built on OpenTelemetry.

避免早期使用：

- “完整记录 AI 思维”
- “自动验证真实推理”
- “MCP for self”
- “保证 Agent 不再犯错”

## 6. Day 15-30：形成开放规范

只有真实实验通过后，发布：

- `ORP Core Profile`
- `ORP Experience Profile`
- `ORP Lesson Profile`
- `ORP Lesson Delivery Profile`
- `ORP Lesson Evaluation Profile`
- `ORP Eval Exchange Profile`
- `ORP Training Candidate Profile`
- Adapter conformance tests
- 匿名基准结果

社区治理目标是先兼容现有生态，再讨论独立基金会或标准组织。

## 7. 90 天方向

### P0：经验有效性

- Lesson 冲突检测。
- Lesson 过期与自动淘汰。
- MCP、Prompt、Policy File 与 Runtime Hook 交付。
- Lesson 应用证据。
- 坏 Lesson 自动进入复审并支持回滚。
- 匹配基线与 A/B 实验。
- 多 Agent Challenger。
- 跨版本 Agent 行为差异。
- 失败聚类与高价值问题发现。

### P1：跨领域

- Research Agent：将错误引用转化为 citation eval。
- Customer Support Agent：将政策误用转化为规则 Eval。
- Browser Agent：将错误操作路径转化为 trajectory Eval。

### P2：生态与训练候选

- OpenTelemetry Collector processor。
- MLflow、LangSmith、Phoenix 双向导入导出。
- 经审批的 SFT、偏好对、批评修正和负面示例候选导出。
- 公共 Lesson 包，但必须具有来源、验证等级和适用范围。

## 8. 风险与应对

| 风险 | 判断 | 应对 |
|---|---|---|
| 与 tracing/eval 平台重叠 | 高 | 基于 OTel，专注经验编译与效果追踪 |
| Agent 自述不忠实 | 高 | 将其标记为 claim，不视为事实 |
| 自动生成 Eval 无效 | 高 | 必须执行验证，支持人工审批 |
| Lesson 让 Agent 学错 | 高 | 作用域、冲突检测、under_review、效果评估与回滚 |
| 将相关性误当作 Lesson 效果 | 高 | 分级评估；优先匹配基线与随机实验 |
| 训练候选污染模型 | 高 | 结果、人工、隐私与许可四重审批 |
| 遥测泄露敏感数据 | 高 | 默认最小化采集、脱敏、本地优先 |
| Replay 成本过高 | 中 | 采样，只回放高价值失败 |
| 开发者不愿接入 | 中 | `orp wrap -- ...` 零代码入口 |
| 协议无人采用 | 高 | 先让工具产生独立价值，再发布规范 |

## 9. 成功标准

不要以 Stars、下载量或论文引用作为早期主要成功指标。优先证明：

1. 自动生成的回归 Eval 有效。
2. Lesson 能降低相似错误重复率。
3. 能证明 Lesson 已被交付并实际应用。
4. 坏 Lesson 可以被发现、限制和回滚。
5. 开发者可以在十分钟内接入。
6. 数据默认安全，能够解释每条 Lesson 从哪里来。
7. 能与现有 OTel 与 Agent tracing 系统协作。

## 10. 来源与设计依据

- [OpenAI Agent Improvement Loop](https://developers.openai.com/cookbook/examples/agents_sdk/agent_improvement_loop)：展示 trace、人工/模型反馈、Eval 与验证门禁组成的 Agent 改善循环。
- [OpenAI Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)：使用 traces、graders、datasets 和 evaluation runs 评估 Agent workflow。
- [LangSmith Evaluation Concepts](https://docs.langchain.com/langsmith/evaluation-concepts)：区分离线评估与生产在线评估。
- [MLflow Evaluating Production Traces](https://mlflow.org/docs/latest/genai/eval-monitor/running-evaluation/traces/)：支持为 trace 添加 ground truth 与人工反馈。
- [OpenTelemetry Handling Sensitive Data](https://opentelemetry.io/docs/security/handling-sensitive-data/)：强调遥测数据最小化。
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/)：支持通过通用工具接口让 Agent 主动查询 Lesson。
- [MLflow Building Evaluation Datasets](https://mlflow.org/docs/latest/genai/datasets/)：训练与评估资产需要区分标签、ground truth 和验证状态。
