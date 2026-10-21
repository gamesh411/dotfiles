---
name: delegate
description: Hand bounded work to worker agents (native subagents, or the Codex, Cursor and Claude CLIs) while you keep judgment. Use when a task splits into independent parts (per file, item, student, ticket), carries mechanical bulk (extraction, conversion, repetitive edits, sweeps), or wants a second-model review.
---

# Delegate

This skill is the user's standing request to delegate: it counts as being asked to use subagents and the installed worker CLIs.
You are the **lead**: design, judgment and acceptance stay with you, and workers get bounded briefs.
Codex and Cursor workers spend their own quota pools rather than yours, so the saving holds even when you could do a part quickly yourself.
`~/.agents/DELEGATION.md` is the policy; `~/.agents/DELEGATION-CLI.md` holds the CLI recipes.

## 1. Cut the work

List the task's parts and mark each one lead or worker.
A part goes to a worker when it has a written deliverable and a cheap check: a test, a diff, a count, a schema.
Design calls, unclear requirements and anything judged against this conversation stay with the lead.
Batch tiny parts into one brief.

Done when every part is marked and every worker part names its check.

## 2. Route

Follow "Choose the worker" in `DELEGATION.md`: run `agent-capacity --json --task <tiny|routine|substantial>` and take `routing.recommended`, or the routing table when it is null.
Name the model and a low or moderate effort on every dispatch, native spawns included.

Done when every worker part has a provider, model and effort.

## 3. Dispatch

Follow "Dispatch and accept" in `DELEGATION.md` for the brief, the `DELEGATED_WORKER` marker, sandboxing and file ownership.
Launch independent workers in parallel and keep working on lead parts meanwhile.

Done when every brief could be finished without a question back to you.

## 4. Accept

Inspect each result or diff and observe its check pass yourself.
Retry once with a sharper brief or a stronger model, or take the part back.

Done when every worker part is accepted on an observed check or finished by you.
Tell the user which parts went to which model and what was checked.
