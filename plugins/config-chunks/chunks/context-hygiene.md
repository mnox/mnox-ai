---
name: context-hygiene
version: 0.1.0
owner: config-chunks
order: 10
summary: Keep the main thread a coordination layer; delegate discovery to sub-agents and protect the context budget.
---

## Context Hygiene

A clean, light context window is the foundation of every other capability. The
main thread is a **coordination layer, not a research layer.**

- **Delegate discovery to sub-agents.** Searching, exploring, reading-for-
  discovery, tracing callers, and summarizing modules belong in sub-agents that
  return a distilled conclusion — not in the main thread. Keep the main context
  holding only the user's messages, concise sub-agent summaries, and your direct
  edits. Never bloat it with raw file dumps or exploratory grep output.
- **Estimate context cost before executing** any non-trivial task, and say so
  when it's large. A task that will read twenty files is a delegation, not an
  inline action.
- **At high utilization, pause and strategize** instead of blindly pushing past a
  safe budget. Checkpoint the plan to a file, phase the remaining work, or write
  a handoff so a fresh session can continue. A task finished in an exhausted
  context is finished badly: the model loses earlier constraints and contradicts
  itself.

Treat context as a finite, precious resource. The discipline is not optional
tidiness — it is what keeps reasoning sharp deep into a long task.
