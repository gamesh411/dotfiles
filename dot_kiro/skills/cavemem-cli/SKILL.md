---
name: cavemem-cli
description: >
  Persistent cross-session memory via cavemem CLI. Use when agent needs to recall
  past work, search memory, or store observations. Wraps cavemem CLI commands via
  shell since MCP is unavailable. Triggers on: "remember this", "what did I do last
  time", "search memory", "recall", "cavemem", or when context from past sessions
  would help current task.
---

# cavemem-cli — memory without MCP

MCP disabled. Use `cavemem` CLI via shell tool instead.

## SEARCH MEMORY

```bash
cavemem search "query here" --limit 5
```

Returns: id, score, snippet, session_id, timestamp. Use when user asks about past work or you need context from prior sessions.

## STORE OBSERVATION

Write observation via hook stdin:

```bash
echo '{"content":"<observation text>"}' | cavemem hook run user-prompt-submit --ide kiro
```

Use to persist important decisions, bugs found, architecture choices.

## LIST SESSIONS

```bash
cavemem search "" --limit 20
```

Or check status:

```bash
cavemem status
```

## EXPORT / BROWSE

```bash
cavemem export /tmp/mem.jsonl   # dump all
cavemem viewer                   # web UI at localhost:37777
```

## WHEN TO USE

- User asks "what did we do before" / "remember when" → search
- Important decision made → store observation
- Starting new session on existing project → search project name
- Bug found → store for backprop reference

## RULES

- Always use shell tool to invoke cavemem commands
- Quote search queries properly
- Keep stored observations caveman-compressed
- Never store secrets or private content
