---
inclusion: always
---

# Open Brain checkpointing

Same capture policy as other harnesses (Cursor, etc.) - not a Kiro-only silent mode.

Tools: `brain_search`, `brain_recent`, `brain_stats`, `brain_capture`, `brain_revise`, `brain_forget`.

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

## When to correct instead of capture

If a retrieved thought is **wrong, stale, or misleading**, do not capture a second thought that argues with it - search keeps returning both and the reader has to notice the contradiction.

- Wrong or outdated wording → `brain_revise` with the full corrected text. The old version is retired but stays recoverable.
- Should never have been stored, or no longer true at all → `brain_forget`. Soft by default; `hard: true` only for secrets or genuine junk.
- Still true, but only in a narrower situation than it reads → revise it to state that scope.

Always ask before revising or forgetting, and quote the thought you mean. Never guess an id - take it from `brain_search` / `brain_recent`.

## When NOT to capture

- Trivial reads/searches, mid-task steps, duplicates, things already in docs/code

## Never capture

Secrets, API keys, passwords, OTP codes, private keys, connection strings with credentials.
