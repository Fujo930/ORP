# Moss Agent + ORP Integration Guide

Moss Agent can integrate ORP in two ways:

## Option 1: Backend Python Integration

Moss Agent's backend is Python-based (PyInstaller, ~9MB).
Add ORP to the backend's dependencies:

```bash
cd moss-fork
pip install open-reflection-protocol
```

Then in the agent's chat logic:

```python
from orp import Experience
from orp.schema import TimelineEvent

# Before processing a user request, retrieve relevant lessons
# After processing, record the experience
with Experience(goal=user_message) as exp:
    result = agent.process(user_message)
    exp.set_outcome("success" if result.success else "failed")
```

## Option 2: Sidecar Process

Run ORP as a separate process that Moss Agent communicates with:

```bash
# Start ORP sidecar
orp mcp-server --transport stdio
```

Then Moss Agent invokes ORP's CLI for lesson retrieval/reporting:

```python
import subprocess

# Retrieve lessons before a task
result = subprocess.run(
    ["uv", "run", "orp", "lessons", "list", "--status", "active"],
    capture_output=True, text=True
)
```

## Option 3: Pre/Post Hooks in Moss Agent

Add hooks to Moss's agent lifecycle:

```python
# mossagent/chat.py — before LLM call
def on_task_start(goal: str):
    lessons = retrieve_orp_lessons(goal)
    if lessons:
        inject_into_context(lessons)

# mossagent/chat.py — after LLM call
def on_task_complete(goal: str, outcome: dict):
    record_orp_experience(goal, outcome)
```
