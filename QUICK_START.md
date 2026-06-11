# ORP 快速上手

> 用一次失败，生成一条可验证经验和一个回归测试。

## 安装

```bash
pip install open-reflection-protocol
```

## 零代码运行

使用 ORP 包裹现有 Agent：

```bash
orp wrap -- python my_agent.py
```

运行结束后：

```bash
orp inspect latest
orp learn latest
orp report --open
```

`orp learn latest` 会尝试：

- 从 trace 提取可观察事实。
- 区分工具证据与 Agent 声明。
- 找出未经证明的结论。
- 生成候选 Lesson。
- 将失败编译为可执行 Eval。
- 在可用时回放替代策略。
- 检查新 Lesson 与现有 Lesson 的冲突。

## Coding Agent 示例

```bash
orp wrap -- python examples/failing_coding_agent.py
orp learn latest
```

预期输出：

```text
Experience: exp_01...
Outcome: failed

Evidence:
  observed  pytest exited with code 1
  observed  anonymous-user test failed

Claims challenged:
  unsupported  "The authentication fix is complete"

Artifacts generated:
  candidate lesson  Test anonymous, authenticated, and forbidden paths
  runnable eval      .orp/evals/test_anonymous_access.py

Replay:
  improved  alternative strategy passed the generated eval
```

运行全部生成的 Eval：

```bash
orp eval run --all
```

## Python 接入

```python
import orp

orp.autolog()

result = agent.run("修复匿名用户访问错误")
```

显式记录客观结果：

```python
from orp import Experience

with Experience(goal="修复匿名用户访问错误") as exp:
    result = agent.run()
    exp.outcome(
        status="failed",
        signals={"pytest_exit_code": 1},
    )
```

## 检索已验证 Lesson

```python
from orp import LessonStore

lessons = LessonStore().retrieve(
    task="修改认证控制器",
    status="active",
    limit=3,
)
```

Lesson 只有在通过外部验证后才会变成 `active`。未经验证的模型建议保持 `candidate`。

## 将 Lesson 交付给 Agent

推荐使用 MCP Server，让兼容 Agent 主动查询：

```bash
orp mcp-server --transport stdio
```

MCP 工具：

```text
orp_retrieve_lessons(task, limit=3, scope={...})
orp_acknowledge_lesson(lesson_id)
orp_report_outcome(lesson_id, outcome, evidence_refs)
```

ORP 会区分：

```text
retrieved -> delivered -> acknowledged -> applied -> outcome
```

也可以使用其他交付策略：

```bash
orp lessons deliver lesson_01 --strategy prompt-context
orp lessons deliver lesson_01 --strategy policy-file --target AGENTS.md
```

## 检测与撤回坏 Lesson

```bash
orp lessons conflicts
orp effects evaluate lesson_01 --method matched-baseline
orp lessons rollback lesson_01
```

发生冲突或出现负面效果时，Lesson 会先进入 `under_review`，暂停默认交付，而不是立即永久删除。

## 导出训练候选

ORP 不会把成功 Trace 直接当作训练数据。先查看候选及其审批状态：

```bash
orp training candidates
orp training export --approved-only
```

只有完成结果验证、人工审查、隐私审查和许可审查的候选才允许导出。

## 比较两个 Agent 版本

```bash
orp diff exp_before exp_after
```

示例：

```text
Task success:       failed -> passed
Generated evals:    0 -> 1
Unsupported claims: 3 -> 1
Tool calls:         18 -> 13
Elapsed time:       92s -> 71s
```

## 数据安全

ORP 默认：

- 本地保存。
- 对常见密钥和 PII 脱敏。
- 不保存完整原始 Chain-of-Thought。
- 对大型工具输出只保存摘要和哈希。

检查待导出的内容：

```bash
orp export latest --dry-run
```

## 设计依据

- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [OpenAI Agents SDK Observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability)
- [OpenAI Reasoning Items Cookbook](https://developers.openai.com/cookbook/examples/responses_api/reasoning_items)
- [OpenTelemetry Handling Sensitive Data](https://opentelemetry.io/docs/security/handling-sensitive-data/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/)
- [MLflow Building Evaluation Datasets](https://mlflow.org/docs/latest/genai/datasets/)
