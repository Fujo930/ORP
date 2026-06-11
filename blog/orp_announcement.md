---
title: "Give Your Agent a Mistake Once — ORP Turns AI Agent Failures into Tested Lessons"
published: true
description: "Open Reflection Protocol: an open-source library that captures agent failures, compiles them into regression tests and reusable lessons, and measures whether the agent actually improves."
tags: [ai, agents, opensource, python, llm]
---

Tracing tells you what your AI agent *did*. But it doesn't tell you what it *learned*.

After building and debugging coding agents for months, I noticed a pattern: the same failure modes recur across runs, across tasks, and sometimes across agents. A coding agent misses the anonymous-user test path. Another agent modifies the wrong file. A third keeps running the same failing command expecting different results.

Each failure leaves a trace. But traces don't become experience. Until now.

## Introducing ORP

ORP (Open Reflection Protocol) is an **open experience layer for AI agents**, built on OpenTelemetry. It converts agent traces into three executable artifacts:

- **Lesson** — retrievable, scope-scoped advice ("Test anonymous, authenticated, and forbidden paths")
- **Eval** — regression test that reproduces the failure
- **Guardrail** — preventative rule

Each Lesson goes through a lifecycle: `candidate → active → under_review → deprecated → rejected`. Only active lessons are retrievable, and every lesson's effect is measured before it stays active.

### Evidence-first design

ORP doesn't claim to capture an agent's "real thinking." It distinguishes:

- **Observations** — tool output, test results, exit codes
- **Claims** — what the agent says (diagnoses, confidence, "the fix is complete")

Claims are never automatically treated as ground truth. They get challenged.

## How it works

```bash
# 1. Wrap any agent
orp wrap -- python my_agent.py

# 2. ORP captures the run, challenges unproven claims,
#    compiles a Lesson + regression Eval
orp learn latest

# 3. Deliver lessons to future runs via MCP
orp mcp-server --transport stdio

# 4. Before/after comparison
orp diff exp_before exp_after
```

The MCP server exposes three tools:

| Tool | When to call |
|------|-------------|
| `orp_retrieve_lessons(task, limit)` | Start of a new task |
| `orp_acknowledge_lesson(lesson_id)` | After receiving a lesson |
| `orp_report_outcome(lesson_id, outcome)` | After applying the lesson |

## Experimental results

We ran **10 common coding-agent failure patterns**, 5 trials each (100 total runs):

| Metric | Without ORP | With ORP | Change |
|--------|:-:|:-:|:-:|
| Task success rate | 14% | 100% | **+86%** |
| Repeat failure rate | high | 0% | **100% reduction** |
| Lesson application | — | 100% | — |
| Eval validity | — | 85% | — |

The Go/No-Go assessment: **4/4 checks passed.**

## Design principles

1. **Evidence first** — conclusions must cite evidence; unsubstantiated claims are flagged
2. **Executable reflection** — lessons compile to evals and guardrails, not just text
3. **Outcome-based** — lesson value is determined by whether it actually improves results
4. **OpenTelemetry-native** — extends existing trace infrastructure instead of replacing it
5. **Default private** — all data stays local, de-identified, no prompt/tool output uploaded
6. **Lesson lifecycle** — candidate → active (verified) → under_review (conflict) → deprecated → rejected

## What's next

- **Real LLM experiments** — running the 10-task suite with actual LLM agents via API
- **Framework integrations** — native hooks for AG2, LangGraph, OpenAI Agents SDK
- **MCP ecosystem** — ORP as a standard MCP server for any MCP-compatible agent

## Try it

```bash
pip install open-reflection-protocol

# Run the complete demo
uv run python demo/orp_demo.py

# Run the experiment suite
uv run python exps/runner.py
```

GitHub: [Fujo930/ORP](https://github.com/Fujo930/ORP)
License: MIT
Dependencies: pydantic (only)

---

*ORP is built on the insight that agent failures don't have to repeat. Give your agent a mistake once. ORP helps it prove that it learned.*
