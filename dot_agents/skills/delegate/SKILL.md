---
name: delegate
description: Hand bounded work to worker agents (native subagents, or the Codex, Cursor and Claude CLIs) while you keep judgment. Use when a task splits into independent parts (per file, item, student, ticket), carries mechanical bulk (extraction, conversion, repetitive edits, sweeps), or wants a second-model review. Load it before spawning any subagent or worker.
---

# Delegate

This skill is the user's standing request to delegate: it counts as being asked to use subagents and the installed worker CLIs.
You are the **lead**: design, judgment and acceptance stay with you, and workers get bounded briefs.
Codex and Cursor workers spend their own quota pools rather than yours, so the saving holds even when you could do a part quickly yourself.
The user wants quality first and, second, every subscription used before it resets.
`~/.agents/DELEGATION.md` is the policy; `~/.agents/DELEGATION-CLI.md` holds the CLI recipes.

## 1. Cut the work

List the task's parts and mark each one lead or worker.
A part goes to a worker when it has a written deliverable and a cheap check: a test, a diff, a count, a schema.
Design calls, unclear requirements and anything judged against this conversation stay with the lead.
Batch tiny parts into one brief.

Done when every part is marked and every worker part names its check.

## 2. Route

Follow "Choose the worker" in `DELEGATION.md`: run `agent-capacity --json --task <tiny|routine|substantial|review|research|computer_use|aesthetic>` once per batch, reuse it for ten minutes, and use `routing.recommended` when available.
The recommendation already applies quality tiers first and spare capacity second.
Code work goes to Claude Opus or Fable; QA, review, research and the rest go to the other providers, and computer use to Codex (`--task computer_use`).
When `routing.preferred_unverified` is set, it is a better tier blocked only by missing quota data, often Claude's stale cache: use it unless a check shows it constrained.
When the recommendation is null, choose a bounded available worker manually: stay in the highest tier with a usable route, and within it prefer the pool with the largest `slack_percent`.
A native subagent spends the current host's own pool; use it when routing picks that provider or when the part needs this session's tools or context.
Unknown quota is uncertainty to report, not a prohibition on delegation.
Verify supported commands and response behavior instead of requiring a particular CLI version.
Name the model and a low or moderate effort on every dispatch, native spawns included.
For native Claude subagents use `opus` for code work and `fable` for aesthetic code work; `haiku` is only a fallback for search, lookup and extraction.
Prefer `opus` over `sonnet`.

Done when every worker part has a provider, model and effort.

## 3. Dispatch

Follow "Dispatch and accept" in `DELEGATION.md` for the brief, the `DELEGATED_WORKER` marker, sandboxing and file ownership.
Read each policy file once per session, and read `DELEGATION-CLI.md` only when dispatching a CLI worker.
Launch independent workers in parallel, at most four native subagents at a time, and keep working on lead parts meanwhile.

Done when every brief could be finished without a question back to you.

## 4. Accept

Inspect each result or diff and observe its check pass yourself.
Retry once with a sharper brief or a stronger model, or take the part back.

Done when every worker part is accepted on an observed check or finished by you.
Tell the user which parts went to which model and what was checked.
