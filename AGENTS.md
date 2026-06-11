# ORP Integration for AI Coding Agents

This project uses ORP (Open Reflection Protocol) to capture agent failures,
compile them into lessons, and prevent repeat mistakes.

## Before starting any task

Check if ORP has relevant lessons:

```json
// MCP tool: orp_retrieve_lessons(task, limit=3)
// Returns active lessons with recommendations
```

## After completing a task

Report the outcome so ORP can track lesson effectiveness:

```json
// MCP tool: orp_report_outcome(lesson_id, outcome, evidence_refs)
// outcome: "success" | "failed" | "improved" | "worse"
```

## MCP Server

ORP provides an MCP server at:
```
orp mcp-server --transport stdio
```

### Available MCP tools

| Tool | When to call |
|------|-------------|
| `orp_retrieve_lessons(task, limit=3)` | Start of any task |
| `orp_acknowledge_lesson(lesson_id)` | After reading a lesson |
| `orp_report_outcome(lesson_id, outcome, evidence_refs)` | After task completion |

## Error prevention patterns

1. Test anonymous, authenticated, and forbidden paths when modifying auth
2. Verify file matches bug description before editing
3. Check project config (.editorconfig, linter) before coding
4. Read full stack trace before diagnosing
5. Stop after 3 repeated failures and reassess strategy
6. Run full test suite after every change
7. Query API docs before using unfamiliar parameters
8. Always handle async errors (TimeoutError, CancelledError)
9. Let pip resolver choose dependency versions unless explicitly required
10. Always check for None after database queries
