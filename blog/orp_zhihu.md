# 让你的 AI Agent 犯一次错，然后让它用回归测试证明自己学会了

## AI Agent 的同一个错误会反复出现

如果你用过 AI 编程助手（Claude Code、Codex、Cursor），你一定见过这个场景：

Agent 修改了认证逻辑，自测通过，提交。但一周后发现匿名用户路径是坏的。
另一个 Agent 接到 "修复 UserController" 的任务，却去改了 AdminController。
第三个 Agent 反复运行同一个失败命令，期待不同结果。

每次失败都有 trace（轨迹记录）。但 trace 不会变成经验。**直到现在。**

## 什么是 ORP

ORP（Open Reflection Protocol）是一个**开源的 AI Agent 经验层**，基于 OpenTelemetry 构建。它把 Agent 的运行记录自动编译为三类可执行资产：

- **Lesson（经验）** — 可检索、带作用域的建议（"必须测试匿名/已登录/无权限三类路径"）
- **Eval（回归测试）** — 可复现失败的测试用例
- **Guardrail（守卫规则）** — 预防性约束

每条 Lesson 有完整的生命周期：
```
candidate → active → under_review → deprecated → rejected
               ↑
        （只有 active 的
          Lesson 可被检索）
```

### 证据优先的设计

ORP 不声称能捕获 AI 的"真实思维"。它区分两类事件：

| 类型 | 含义 | 示例 |
|------|------|------|
| **Observation** | 可观察事实 | pytest 输出、退出码、git diff |
| **Claim** | Agent 声明 | "修复已完成"、"原因可能是 X" |

Claim **永远不会**被自动当作事实。它们会被 Challenger 质疑。

## 一条命令接入

```bash
# 1. 用 ORP 包裹任何 Agent
orp wrap -- python my_agent.py

# 2. ORP 分析运行结果，挑战未证明的声明，
#    自动生成 Lesson + 回归测试
orp learn latest

# 3. 通过 MCP 将 Lesson 交付给后续任务
orp mcp-server --transport stdio

# 4. 前后对比
orp diff exp_before exp_after
```

MCP 服务器提供三个工具，Agent 可以在任务前后调用：

| 工具 | 调用时机 |
|------|---------|
| `orp_retrieve_lessons(task, limit)` | 任务开始时检索相关经验 |
| `orp_acknowledge_lesson(lesson_id)` | 确认收到 Lesson |
| `orp_report_outcome(lesson_id, outcome)` | 汇报 Lesson 应用效果 |

## 实验验证

我们设计和测试了 **10 种常见的 coding agent 失败模式**，每组 5 次试验（共 100 次运行）：

| 指标 | 无 ORP | +ORP | 变化 |
|------|:-:|:-:|:-:|
| 任务成功率 | 14% | 100% | **+86%** |
| 重复失败率 | 高 | 0% | **降低 100%** |
| Lesson 应用率 | — | 100% | — |
| Eval 有效性 | — | 85% | — |

**4 项 Go/No-Go 检查全部通过。**

复现实验结果：
```bash
pip install open-reflection-protocol
uv run python exps/runner.py
```

## 设计原则

1. **证据优先** — 结论必须引用证据；无证据的标记为声明
2. **可执行反思** — 反思优先编译为 Eval、Guardrail 或 Lesson，不只是文字
3. **基于结果** — 经验价值由后续任务结果决定，不由模型自评决定
4. **基于 OpenTelemetry** — 不替代现有 tracing，扩展它
5. **默认隐私** — 所有数据本地保存、脱敏、不上传
6. **Lesson 生命周期** — candidate → active（已验证） → under_review（冲突） → deprecated → rejected

## 安装

```bash
pip install open-reflection-protocol
```

**零依赖**（除了 pydantic）。

## 开源

GitHub: [Fujo930/ORP](https://github.com/Fujo930/ORP)
协议: MIT

---

**AI Agent 的失败不必重复。让 Agent 犯一次错，然后让它用回归测试证明自己学会了。**
