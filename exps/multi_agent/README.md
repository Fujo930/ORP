# Multi-Agent Experiments: Findings

## What We Built

A cross-agent experiment framework where two agents modify a payment processing system:

| Component | Location | Purpose |
|-----------|----------|---------|
| Payment workspace | `workspace/` | 3-file Python project: payment.py, validator.py, test_payment.py |
| Experiment runner | `run_experiment.py` | Isolated copies per agent, ORP pipeline, result comparison |

## Design

The experiment simulates a common real-world mistake: Agent A adds a new payment method to payment.py but forgets to update validator.py. ORP captures this failure and generates a Lesson. Agent B, guided by the Lesson, updates both files correctly.

## Key Finding: Modern LLMs Don't Make Obvious Mistakes

Across all real-agent tests (7+ tasks, 15+ delegate_task calls using DeepSeek V4 Flash), the model consistently:

- Reads ALL relevant files before making changes
- Identifies cross-file dependencies and updates them
- Handles edge cases proactively
- Self-corrects by running tests

This means the controlled experiment (simulated agent) always shows both agents succeeding because the simulation model is too simple. And real-agent experiments show the model is too competent to make the expected mistakes.

## What This Means for ORP

ORP's value is NOT about making LLMs smarter in a single session. The model already handles individual tasks well. ORP's actual value:

1. **Cross-session persistence**: A Lesson from Session A is available in Session B (new conversation, new context)
2. **Cross-agent knowledge sharing**: Agent A's experience becomes Agent B's advantage
3. **Measurable improvement tracking**: Without ORP, there's no way to quantify whether the agent is getting better over time
4. **Regression testing infrastructure**: ORP generates runnable evals that persist

These four capabilities are what make ORP valuable, and they only show up in multi-session, multi-agent scenarios - not in single-turn coding tests.

## Running the Demo

```bash
uv run python exps/multi_agent/run_experiment.py
```

Currently shows both agents succeeding (the simulated agent model is deterministic). To see cross-agent learning with real LLM behavior, run each agent as a separate `delegate_task` call.
