---
inclusion: always
---

# Open Brain checkpointing

Same capture policy as other harnesses (Cursor, etc.) - not a Kiro-only silent mode.

## When to search

If uncertain about prior work on the current project/topic:

1. `brain_search` for the current project / topic
2. `brain_recent` if search is thin

## When to capture

- **Interactive sessions:** after a clear decision, preference, constraint, or "what we tried" outcome, **offer** `brain_capture` (do not silently spam). Prefer short, durable, outcome-level wording (English type labels; body may be Hungarian).
- **Fully autonomous unattended runs** (no human in the loop, e.g. gnhf): you may checkpoint without offering. Budget ~2–5 durable captures per substantial run; quality over quantity.

Typical durable moments (interactive or unattended):

1. Decision made - user picks approach A over B → `decision` / `tried`
2. Task completed - meaningful unit of work finishes → `insight` or `project_context`
3. Bug found + fixed - what broke, why, how → `tried` / `insight`
4. New project context - stack, conventions, constraints → `project_context` / `constraint`
5. User preference expressed → `preference`
6. Session/run end - short state summary if something durable changed

Always include **project context** in the capture body, and set `source` / provenance so bot-created entries can later be identified and tied to the project or session that produced them.

## When NOT to capture

- Trivial reads/searches, mid-task steps, duplicates, things already in docs/code

## Never capture

Secrets, API keys, passwords, OTP codes, private keys, connection strings with credentials.
