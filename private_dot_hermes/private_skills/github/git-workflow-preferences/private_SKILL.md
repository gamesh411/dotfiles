---
name: git-workflow-preferences
description: User's git workflow preferences — when to rebase, when to amend, how to handle intra-branch history.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [git, workflow, preferences, squash-merge, rebase]
---

# Git Workflow Preferences

## Squash-Merge Repos: Don't Over-Engineer Commit History

If the destination repo uses **squash-merge** (the default for most GitHub repos), all commits on the branch collapse into one at merge time. The final commit message is the PR title and description, not the individual branch commits.

**Rule:** Do NOT do interactive rebases, fixup squashing, or perfect intra-branch commit ordering. Fix code issues by amending the relevant commit directly (`git commit --amend --no-edit`) and force-pushing. Do not replay history to reorder changes across commits.

Only invest in clean commit history when the repo uses merge-commit or rebase-merge strategies.

## Logical Commit Grouping for Reviewability

Even in squash-merge repos, grouping commits logically makes the PR easier
to review. The user prefers this structure for multi-concern branches:

1. **Feature commits** — one per logical change, each independently
   reviewable (e.g. "remove compat shim + add spawn", "add arguments format
   support", "add server spawn worker support").
2. **Test changes** — cross-platform test adaptations, skip decorators,
   polling vs sleeping, normalization functions.
3. **CI changes** — install scripts, workflow YAML, matrix expansion.

This grouping should happen **after** all changes are verified locally,
not during development. Don't reorder commits prematurely while still
fixing bugs — get the code working first, then reorganize.

**Key principle:** The reorganization step is the last step, after:
1. All code and test changes are applied
2. Changes have been audited for necessity (no cosmetic or local-only edits)
3. Tests pass locally on the target platform
4. The diff is minimal and complete

Only then reorganize into logical commits. If you discover unnecessary
changes during the audit, revert them before committing — don't carry
dead weight into the reorganized history.

## How to Check

```bash
# Quick check: look at the PR's merge button text
gh pr view --json mergeStateStatus

# Or check the repo's settings
gh api repos/:owner/:repo --jq '.allow_squash_merge'
```
