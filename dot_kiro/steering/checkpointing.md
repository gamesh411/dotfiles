---
inclusion: always
---

# Auto-Checkpointing

Write observations to cavemem silently. Never ask permission.

## When to Write

1. Decision made -- user picks approach A over B
2. Task completed -- meaningful unit of work finishes
3. Bug found + fixed -- what broke, why, how
4. New project context -- stack, conventions, constraints
5. User preference expressed
6. Session end -- checkpoint current state

## When NOT to Write

- Trivial reads/searches, mid-task steps, duplicates, things already in docs/code

## Format

```
[category] brief summary

key details in 1-3 lines max
```

Categories: `decision`, `completed`, `bugfix`, `context`, `preference`, `state`

## On Session Start

If uncertain about prior work:
1. `search` cavemem for recent work related to current project
2. `list_sessions` if search returns nothing

## Budget

2-5 observations per substantial session. Quality over quantity.
