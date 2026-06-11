# ORP 发布文章大纲

## 推荐标题

**Give Your Agent a Mistake Once: Introducing ORP**

副标题：

> Turn agent failures into regression tests, reusable lessons, and measurable improvements.

## 核心叙事

Agent tracing 已经能告诉我们发生了什么，但它通常不会自动回答五个问题：

1. 这次失败应该形成什么经验？
2. 如何证明这个经验是正确的？
3. Agent 使用这条经验后，是否真的变好了？
4. Lesson 是否真的进入 Agent 上下文并被应用？
5. 如果 Lesson 有害，系统能否停止交付并回滚？

ORP 是建立在 OpenTelemetry trace 之上的开放经验层。它将运行记录编译为 Lesson、Eval 和 Guardrail，并持续追踪这些经验是否有效。

## 文章结构

### 1. 一个会重复犯错的 Coding Agent

- Agent 修改认证逻辑。
- 测试看似通过，但遗漏匿名用户路径。
- 一周后，相似错误再次出现。
- 团队拥有完整 trace，却没有形成可执行经验。

### 2. Trace 不是经验

Trace 是事实来源，但不能自动成为 Lesson。

```text
Trace: Agent 做过什么
Experience: 这次运行发生了什么、哪些是事实、哪些是声明
Lesson: 下次在什么条件下应该采取什么行动
Delivery: Lesson 如何进入 Agent，以及是否被应用
Eval: 如何证明 Lesson 有效
Rollback: Lesson 有害时如何撤回
```

### 3. ORP 如何工作

```bash
orp wrap -- python coding_agent.py
orp learn latest
```

展示：

- 工具输出被标记为 observation。
- Agent 的“已经修复”被标记为 claim。
- Challenger 发现该声明缺少匿名用户测试。
- ORP 生成回归 Eval 与候选 Lesson。
- Replay 证明替代策略更好。
- Agent 通过 MCP 查询 Lesson，ORP 记录它是否真正应用。

### 4. 为什么不记录“真实思维”

- 部分模型 API 不公开原始 Chain-of-Thought，只提供摘要。
- 模型表达出的推理可能不是行为的真实原因。
- 因此 ORP 只将推理摘要作为声明，最终依赖外部证据和结果。

### 5. 为什么基于 OpenTelemetry

- 不重新发明 tracing。
- 兼容已有 Agent、模型、工具调用和 evaluation event。
- 用户可以继续选择自己的存储、观察和评估平台。

### 6. Lesson 必须被交付、验证，也必须能撤回

- 单次失败生成的 Lesson 只是 candidate。
- 通过测试或人工确认后才 active。
- MCP 是推荐交付方式，但也支持 Prompt、Policy File 和 Runtime Hook。
- ORP 区分 retrieved、delivered、acknowledged 和 applied。
- 冲突或后续效果差时进入 under_review，并可回滚。
- 防止 Agent 将错误总结永久写入记忆。

### 7. 不把相关性误当作效果

- 简单成功次数不能证明 Lesson 有效。
- 先使用描述统计，再比较匹配任务基线。
- 有条件时运行 A/B 实验或明确假设的因果分析。

### 8. 经验可以成为训练候选，但不是自动成为训练数据

- 成功 Trace 可能只是偶然成功。
- ORP 可以生成 SFT、偏好对、批评修正和负面示例候选。
- 只有结果、人工、隐私与许可审查通过后才能导出。

### 9. 一天完成代码，之后验证价值

- AI 可以在一天内构建参考实现。
- 真正问题不是代码量，而是自动生成的 Eval 是否有效、Lesson 是否降低重复失败。
- 发布公开实验结果，而不是只展示 Schema。

### 10. Call to Action

```bash
pip install open-reflection-protocol
orp wrap -- python your_agent.py
orp learn latest
```

邀请社区提供：

- 真实但已脱敏的 Agent 失败案例。
- Adapter。
- Eval runner。
- Lesson 效果验证方法。
- MCP 与其他 Delivery Adapter。

## 短文案

### Hacker News

```text
Show HN: ORP turns agent failures into regression tests and reusable lessons
```

### X / Twitter

```text
Tracing tells you what your agent did.
ORP turns what happened into a tested lesson.

orp wrap -- python your_agent.py
orp learn latest
```

### 中文

```text
让 Agent 犯一次错，然后要求它用回归测试证明自己真的学会了。

ORP：建立在 OpenTelemetry 之上的开放 Agent 经验层。
```

## 来源

- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [OpenAI Agent Improvement Loop](https://developers.openai.com/cookbook/examples/agents_sdk/agent_improvement_loop)
- [OpenAI Reasoning Items Cookbook](https://developers.openai.com/cookbook/examples/responses_api/reasoning_items)
- [Anthropic: Reasoning Models Don't Always Say What They Think](https://www.anthropic.com/research/reasoning-models-dont-say-think)
- [MLflow GenAI Tracing](https://mlflow.org/docs/latest/genai/tracing/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/)
- [MLflow Building Evaluation Datasets](https://mlflow.org/docs/latest/genai/datasets/)
