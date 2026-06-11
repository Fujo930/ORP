# ORP 实验计划：10 个真实失败任务

> 目标：验证 ORP 能否降低 AI Agent 的重复失败率
> 指标：Eval validity, Lesson application rate, Repeat failure reduction

---

## 实验方法论

### 基线

对每个任务类型，先让 Agent 在没有 ORP 的情况下运行 5 次，记录：
- 初始成功率
- 重复错误模式
- 典型 token/工具调用成本

### 实验组

让 Agent 在 ORP 的 Lesson 检索 + 注入下运行 5 次，记录：
- 成功率变化
- Lesson 是否被检索、确认、应用
- Lesson 应用后结果是否改善
- 自动生成的 Eval 是否能复现原问题

### 指标定义

| 指标 | 定义 | 计算方式 |
|------|------|---------|
| Eval validity | 自动生成 Eval 真正能复现问题的比例 | `valid_evals / total_evals` |
| Lesson precision | 被应用的 Lesson 中产生正面影响的比例 | `positive_effects / applied_lessons` |
| Delivery-to-application | 已交付 Lesson 中被实际应用的比例 | `applied / delivered` |
| Repeat failure reduction | 相似错误重复发生率下降幅度 | `1 - (exp_group_repeat_rate / control_group_repeat_rate)` |
| Task success delta | 使用 Lesson 前后的成功率变化 | `success_rate_with - success_rate_without` |
| Cost delta | Token/工具调用/时间变化 | `cost_with - cost_without` |

---

## 任务 #1：遗漏边界条件

**场景：** Agent 修复认证逻辑，忘记测试匿名用户路径。

**控制组：**
- Agent 直接修改 → 34/35 测试通过
- 重复失败率：高（约 80% 的情况下再次遗漏）

**实验组：**
- ORP 从首次失败生成 Lesson："测试匿名/已登录/管理员三类路径"
- 再次运行时 Agent 检索到 Lesson 并应用
- 预期：35/35 通过，重复失败率 < 20%

**验证方法：** 运行 10 次，记录每次是否遗漏。

| 运行 | 使用 ORP | 测试通过率 | Lesson 检索 | Lesson 应用 | 重复失败 |
|------|----------|-----------|------------|------------|---------|
| 1 | 否 | 34/35 | — | — | — |
| 2 | 否 | 34/35 | — | — | 是 |
| 3 | 否 | 33/35 | — | — | 是 |
| 4 | 是 | 35/35 | 是 | 是 | 否 |
| 5 | 是 | 35/35 | 是 | 是 | 否 |
| 6 | 是 | 34/35 | 是 | 否 | 是 |
| ... | | | | | |

---

## 任务 #2：修改错误文件

**场景：** Agent 需要修复 UserController.java，但错误修改了 AdminController.java。

**控制组：** Agent 选择错误文件 → 修复不生效 → 测试失败。

**实验组：** Lesson "在修改前确认文件功能与问题描述匹配" 被检索。

**验证方法：** 观察 Agent 是否在修改前执行 `grep` 或文件检查。

---

## 任务 #3：未读取项目约定

**场景：** Agent 使用 tabs 缩进，但项目规范要求 spaces。

**控制组：** Agent 引入风格不一致 → lint 失败。

**实验组：** Lesson "检查项目配置文件（.editorconfig, ruff.toml）" 被应用。

**验证方法：** lint 是否通过。

---

## 任务 #4：过早下结论

**场景：** Agent 看到一个错误日志就立刻下结论，没有查看全栈跟踪。

**控制组：** Agent 错误归因 → 修复不完整。

**实验组：** Lesson "查看完整堆栈跟踪后再下结论" 被应用。

**验证方法：** 观察时间线中是否有完整的 `observation` 事件链。

---

## 任务 #5：重复执行无效工具

**场景：** Agent 反复运行同一个失败命令，期待不同结果。

**控制组：** Agent 循环 5+ 次 `pytest` 不修改代码。

**实验组：** Guardrail "相同工具连续 3 次返回失败 → 停止并重新评估"。

**验证方法：** Guardrail 触发次数。

---

## 任务 #6：修复局部问题但引入回归

**场景：** Agent 修复 A 功能，但破坏了 B 功能。

**控制组：** Agent 只运行 A 的测试 → 通过 → 提交 → B 被破坏。

**实验组：** Lesson "修改后运行完整测试套件" 被应用。

**验证方法：** 回归数。

---

## 任务 #7：API 参数错误

**场景：** Agent 调用 API 时使用了错误的参数名。

**控制组：** API 返回 400 → Agent 重试 3 次 → 最终手动调试。

**实验组：** Lesson "调用新 API 前先查询文档" 被应用。

**验证方法：** API 调用成功率。

---

## 任务 #8：忽略异步错误

**场景：** Agent 在 try/except 中漏掉了 `asyncio.TimeoutError`。

**控制组：** 异步任务静默失败 → Agent 误以为成功。

**实验组：** Eval：检查异常捕获覆盖范围。

**验证方法：** Eval 能否检测到缺失的异常类型。

---

## 任务 #9：凭猜测选择依赖版本

**场景：** Agent 安装包时指定版本号，选择了不兼容的版本。

**控制组：** 依赖冲突 → 运行时崩溃。

**实验组：** Lesson "使用 pip install 时不指定版本，让 pip 解析依赖"。

**验证方法：** 安装成功率。

---

## 任务 #10：忘记处理空值

**场景：** Agent 从数据库查询后直接使用结果，未检查 None。

**控制组：** `AttributeError: 'NoneType' object has no attribute 'X'`。

**实验组：** Lesson "数据库查询后始终检查 None" 被应用。

**验证方法：** 由 Eval 生成的空值检查测试是否通过。

---

## 结果汇总表

| # | 任务 | Eval validity | Lesson precision | Delivery→Application | Repeat reduction | Success delta |
|---|------|-------------|----------------|--------------------|-----------------|-------------|
| 1 | 遗漏边界条件 | | | | | |
| 2 | 修改错误文件 | | | | | |
| 3 | 未读取项目约定 | | | | | |
| 4 | 过早下结论 | | | | | |
| 5 | 重复无效工具 | | | | | |
| 6 | 引入回归 | | | | | |
| 7 | API 参数错误 | | | | | |
| 8 | 忽略异步错误 | | | | | |
| 9 | 依赖版本失误 | | | | | |
| 10 | 空值处理遗漏 | | | | | |
| | **平均** | | | | | |

---

## Go/No-Go 标准

| 条件 | 通过标准 | 判定 |
|------|---------|------|
| Eval validity | > 60% 自动生成的 Eval 有效 | □ |
| Lesson precision | > 50% 应用的 Lesson 带来正面效果 | □ |
| Repeat failure reduction | > 30% 下降 | □ |
| Delivery-to-application | > 40% 被应用的 Lesson 被实际采纳 | □ |

如果三项以上不达标：
- 弱化"Agent 学习"叙事
- 聚焦"失败 → 回归测试"能力
- 改善 Lesson 检索和注入机制
