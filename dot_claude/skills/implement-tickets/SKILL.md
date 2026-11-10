---
name: implement-tickets
description: Drain a local markdown ticket tracker by running /implement on each remaining ticket in dependency order.
disable-model-invocation: true
---

Drain `.scratch/<feature>/issues/` by dispatching one `/implement` worker per ticket. You are the coordinator: you own the DAG, claims, waves, and git. Workers own a single ticket.

If `docs/agents/issue-tracker.md` is missing, stop and tell the user to run `/setup-matt-pocock-skills`.

## 1. Snapshot the frontier

Run the script. Completion: JSON printed, no `error` key.

```sh
python3 ~/.claude/skills/implement-tickets/scripts/frontier.py --repo <repo-root>
```

Pass `--dir .scratch/<feature>/issues` when more than one feature still has remaining tickets.

Read every ticket the snapshot names as `frontier`, `gated_frontier`, or `in_flight`. Do not read the rest yet.

## 2. Claim, then dispatch a wave

A **wave** is the largest set of tickets you can run at once without two workers editing the same worktree files.

**Pick.** `frontier` tickets are takeable. A `gated_frontier` ticket is takeable only after you read its blocker's `## Verdict` / `## Answer` and the gate passes (the hint is `only_execute_hint`). If the gate fails, do not dispatch: set that ticket's `**Status:** skipped` yourself, record the reason, and re-run the script. Soft blockers (`NN when it executes`) count as satisfied when NN is `done` or `skipped`.

**Claim.** Before any worker starts, set each picked ticket to `**Status:** claimed` and save.

**Lock.** At most one `source` or `measure` worker on the shared worktree. Any number of `scratch` workers may join that wave: they only touch `.scratch/` (and the decision log). Two `source` tickets wait for separate waves. Isolated git worktrees may lift the source lock; do not bother unless two source tickets are actually in the same frontier.

**Dispatch.** One subagent per claimed ticket, in the same turn when they share a wave. Each prompt:

1. Paste [WORKER.md](WORKER.md) in full.
2. Name the ticket path, the spec path, the repo root, and the llvm build dir if this is llvm-project (`llvm/out/build/relwithdebug`).
3. Quote the ticket body.
4. Point at skills the worker must read (`implement`, `tdd`, `code-review`, tracker, spec, `llvm-dev` when relevant).

Completion: every claimed ticket in the wave has a `WORKER_RESULT` (or a worker failure you then mark blocked).

## 3. Land the wave

For each result, in ticket-number order:

1. Re-read the ticket file. Status must match the result (`done` / `skipped` / `claimed`+blocker).
2. `git diff` the `files` list. A `measure` worker must leave **no** tracked source diff; instrumentation that remains is a failed ticket, send it back.
3. Commit only if `commit_request` is not `none` and the diff is the ticket's work. Coordinator commits; workers never do. Follow the repo's commit-message style. Do not commit secrets, `llvm/out/`, or unrelated untracked files.
4. Append one row to `.scratch/<feature>/decisions.tsv` with `~/.claude/skills/show-me-your-work/scripts/log.sh` (phase = ticket id).

Then re-run the script. Completion: snapshot reflects this wave (picked ids are `done` or `skipped`, no stale `claimed` unless blocked).

## 4. Repeat until drained

Loop steps 2-3 until `remaining` is empty.

Stop early and tell the user if `remaining` is non-empty and both `frontier` and `gated_frontier` are empty: something is claimed, mis-labelled, or blocked on a ticket that is not `done`/`skipped`.

## Tracker conventions

Local files, one ticket per `NN-slug.md`. `**Status:**` and `**Blocked by:**` near the top, numbers like `01`. Done = `done` / `resolved` / `skipped` / `wontfix`. Takeable = `ready-for-agent` with hard blockers done. Comments append under `## Comments`.
