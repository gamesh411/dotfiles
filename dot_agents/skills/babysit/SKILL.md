---
name: babysit
description: "Watch an open PR when the user asks: fix failing CI, handle straightforward review comments, and drive it to a mergeable state."
---

# Babysit a PR

Use when the user explicitly asks to keep an open PR green or shepherd it to merge readiness. Opening a PR alone does not start monitoring. A subagent that opens a PR returns its status to the parent unless monitoring was assigned.

## Tools and scope

Use the host's preferred GitHub tool. Prefer `gh-axi` where the host provides it, then an available connector, with `gh` as a fallback. Inspect the selected tool's help or schema instead of assuming command parity. The examples below use `gh` syntax.

Inspect the PR's actual base branch, current head commit, draft status, and review policy. Work against that base rather than assuming `main`. Follow repository instructions for builds, tests, commits, and pushes. Attach the PR to the current chat when the host supports PR attachments.

## Steps

1. Fetch PR state, checks, conversations, and inline review threads. For example:

   ```bash
   gh pr view <number> --json number,title,state,baseRefName,headRefName,headRefOid,isDraft,mergeable,reviewDecision,statusCheckRollup,mergeStateStatus,comments,reviews
   ```

   `comments` and `reviews` do not contain every inline review thread. Fetch review threads and their resolution status through an appropriate API or connector too. Record the head commit so later checks can be tied to the code actually reviewed.

2. Triage in priority order:

   - Merge conflicts: merge or rebase the actual base branch according to repository policy. Inspect branch ownership before considering a history rewrite.
   - Failed checks: read the failing run's logs, diagnose the cause, fix it, run the relevant checks, commit, and push within the user's authorized scope.
   - Review feedback: make mechanical changes you agree with. Defer design choices that require the user. When this skill is explicitly invoked, brief replies to the relevant PR review threads are part of addressing the review. Otherwise obtain explicit messaging authorization before posting. Resolve a thread only after the change has been verified.

3. Recheck after each push. Confirm the checks belong to the latest head commit. Batch related changes to avoid unnecessary CI runs.

4. Pace monitoring through tools the current host provides:

   - Active CI: use bounded waits or a check watcher while preserving the ability to report meaningful progress.
   - Later follow-up: use the host's scheduler when the user requested ongoing monitoring. In Codex, use a thread heartbeat. In Claude Code, an installed loop facility may be used. Do not assume a named loop skill exists.
   - Awaiting review: 20 to 30 minute checks are usually enough. For an idle PR, use hourly checks. Stay quiet while nothing actionable changes.
   - Without a scheduler, monitor during the current run and state that later monitoring is unavailable.

5. Stop and report when the PR is ready, closed, or merged. Readiness means required checks pass for the latest head, the branch merges cleanly, actionable review threads are resolved, and the repository's review requirements are satisfied. After three unsuccessful fix cycles, report the unresolved cause and next step. Ask the user only when the next action requires an unprovided design decision or permission.

## Hard rules

- Do not rewrite history on a shared branch without authorization. Prefer a normal merge when repository policy allows it.
- Change test expectations only when they were wrong or the intended behavior changed.
- Keep hooks and required checks enabled.
- Mark a draft ready only within the user's requested scope and after readiness checks pass.
- Merge only when the user separately authorized merging and all required conditions hold.

## Report

Summarize fixes, relevant commit SHAs, deferred feedback, latest-head checks, and any remaining blocker. Use `code-review` when a change needs a broader review, and `unslop` for prose. If posting was authorized by an explicit invocation of this skill, name and link this SKILL.md in the final response.

## Provenance

Independently authored workflow informed by Cursor's public `/babysit` behavior. It is not a port of Cursor's implementation.
