# Open Reflection Protocol (ORP)

> Turn agent failures into regression tests, reusable lessons, and measurable improvements.

**Tracing tells you what your agent did. ORP turns what happened into a tested lesson.**

---

## Demo: 30 Seconds

A coding agent fixes an auth bug but misses the anonymous user path. Tests fail at 34/35.

```bash
# 1. Wrap your agent with ORP
orp wrap -- python my_agent.py

# 2. ORP captures the failure, challenges unproven claims,
#    and compiles a Lesson + regression Eval
orp learn latest

# 3. Same agent retrieves the Lesson via MCP, applies it
#    -> All 35 tests pass this time
orp mcp-server

# 4. Before/after comparison
orp diff exp_before exp_after
```

**Before:**
```
Task success:  FAILED   (34/35 tests)
Claims:        1 unproven
```

**After:**
```
Task success:  PASSED   (35/35 tests)
Claims:        0 unproven
```

That's the loop. One mistake, one lesson, one measurable improvement.

---

## What ORP Does

ORP is an **open experience layer for AI agents**, built on OpenTelemetry. It converts agent traces into three executable artifacts:

| Artifact | What | Example |
|----------|------|---------|
| **Lesson** | Retrievable, scope-scoped experience | "Test anonymous, authenticated, and forbidden paths" |
| **Eval** | Regression test reproducing the failure | `pytest tests/test_anonymous_access.py` |
| **Guardrail** | Preventative rule | "Before modifying auth, run full test suite" |

Each Lesson goes through a lifecycle:

```
candidate -> active -> under_review -> deprecated -> rejected
               |
         (only active lessons
          are retrievable)
```

---

## Key Concepts

- **Evidence-first**: ORP distinguishes observed facts (tool output, test results) from agent claims (diagnoses, confidence statements). Claims are never automatically treated as ground truth.
- **Executable experience**: Lessons compile to runnable evals and guardrails, not just text.
- **Outcome-based value**: Lesson quality is determined by whether it actually improves results, measured through effect evaluation.
- **Built on OpenTelemetry**: ORP extends existing trace infrastructure instead of replacing it.
- **Default private**: All data stays local, de-identified by default, no prompt/tool output uploaded.

---

## Install

From source:

```bash
git clone https://github.com/Fujo930/ORP.git
cd ORP
uv sync
```

Then run commands with `uv run`, for example:

```bash
uv run orp --help
```

Requires Python 3.10+.

---

## Quick Start

### 1. Wrap any agent command

```bash
orp wrap -- python my_agent.py --run-task
```

ORP automatically captures stdout, exit codes, test results, git diff, and OpenTelemetry spans.

### 2. Learn from the run

```bash
orp learn latest
```

This generates:
- A **diagnosis** of what went wrong
- **Challenged claims** (unsupported agent statements)
- A **Lesson** candidate
- A **regression Eval**

### 3. View results

```bash
orp inspect latest
orp report --open          # HTML report
orp diff exp_before exp_after
```

### 4. Deliver lessons to future runs

```bash
# Start the MCP Lesson server
orp mcp-server --transport stdio

# Compatible agents can now use these MCP tools:
#   orp_retrieve_lessons(task, limit=3)
#   orp_acknowledge_lesson(lesson_id)
#   orp_report_outcome(lesson_id, outcome, evidence_refs)
```

---

## Run the Demo

```bash
git clone https://github.com/Fujo930/ORP.git
cd ORP
uv run python demo/orp_demo.py
```

Output:

```
Run 1: Agent misses anonymous user path -> FAILED
ORP analyzes the failure -> challenges 1 unproven claim
ORP compiles Lesson + Eval
MCP delivers Lesson to Agent
Run 2: Agent applies Lesson -> PASSED

Before: 34/35 tests, 1 unproven claim
After:  35/35 tests, 0 unproven claims
```

---

## CLI Reference

```text
orp wrap -- python agent.py    Wrap an agent process with ORP
orp inspect [id]               Inspect an experience (default: latest)
orp learn [id]                 Generate lessons from an experience
orp replay <id>                Counterfactual replay
orp lessons list               List lessons
orp lessons validate <id>      Validate lesson integrity
orp lessons conflicts          Auto-detect conflicting lessons
orp lessons rollback <id>      Rollback a lesson
orp lessons deliver <id>       Deliver a lesson
orp effects evaluate <id>      Evaluate lesson effect
orp training candidates        List training candidates
orp training export            Export approved training data
orp mcp-server                 Start MCP lesson server
orp report --open              Generate HTML report
orp diff <id1> <id2>           Compare two experiences
orp export [id]                Export as JSON
```

---

## Architecture

```text
Agent / Existing Trace
        |
        v
  Trace Adapters (OTel / OpenAI / LangGraph / Generic JSON)
        |
        v
 Experience Builder -> Evidence Verifier
                    -> Reflection Analyzer  (diagnosis + challenger)
                    -> Counterfactual Replayer
        |
        v
 Experience Compiler
   +----+----+------+
   |         |      |
 Lesson    Eval   Guardrail
   |         |      |
   +---- Delivery Router (MCP Server / Prompt / Policy / Runtime Hook)
             |
             v
    Effect Evaluator + Rollback
```

---

## For Contributors

Tests (58 total):

```bash
uv run pytest -q
# 58 passed in 0.66s
```

Key design documents in this repo:

| File | What |
|------|------|
| `ROADMAP.md` | Project roadmap and strategy |
| `SPEC.md` | Protocol specification v0.3 |
| `ARCHITECTURE.md` | Implementation architecture |
| `demo/orp_demo.py` | Standalone demo |

---

## License

MIT
