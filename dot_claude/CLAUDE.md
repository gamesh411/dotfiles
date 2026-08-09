# Global Guidelines

## General Guidelines

These apply to every agent session.

### Punctuation

Never use the em dash "-".
Use a plain dash "-" instead.

### Commit messages

When writing commit messages, never auto-add your agent name as co-author.
Strive to be terse and human-like in phrasing.

### File management

Never manually modify `CHANGELOG.md` files or any files that are marked as auto-generated.

### Sentence-per-line documents

When writing or substantially editing long prose documents where a source line break is not necessarily a line break in the rendered output (Markdown, LaTeX, and similar), put each full sentence on its own line.
Preserve normal document structure, but avoid wrapping multiple sentences onto one physical line.
This keeps version-control diffs easier to read.

### Project formatting

If the project has specific formatting requirements, meet them before committing.

### Comments

Prefer comments that explain why, not how.
If the code already describes everything it needs to describe, do not add a comment.

### Technical decisions

When making technical decisions, do not give much weight to development cost.
Prefer quality, simplicity, robustness, scalability, and long-term maintainability.

### Bug fixing

When doing bug fixes, always start by reproducing the bug in an E2E setting as closely aligned with how an end user would experience it.
This makes sure you find the real problem so your fix will actually solve it.

### UI/UX quality

When end-to-end testing a product, be picky about the UI you see and be obsessed with pixel perfection.
If something clearly looks off, even if it is not directly related to what you are doing, try to get it fixed along the way.

### Engineering excellence

Apply that same high standard to engineering excellence: lint, test failures, and test flakiness.
If you see one, even if it is not caused by what you are working on right now, still get it fixed.

## Open Brain

You have MCP tools: `brain_search`, `brain_recent`, `brain_stats`, `brain_capture`, `brain_revise`, `brain_forget`.

### When to search

Search **before** you form a plan on an unfamiliar project, not after you get stuck.
A brain read once the assumptions are already made cannot change them, which is the whole point of having one.

Call `brain_search` before any non-trivial answer that depends on **this user's** preferences, constraints, past decisions, people, or project context (add `thought_type` / person / topic filters when helpful).
Search returns nothing when nothing is relevant, so an empty result is information rather than a failure.

Skip search for pure general knowledge, one-off trivia, or when the user already pasted full context.

### When to capture

**Capture without asking.** Do not offer, do not propose, do not interrupt the work to negotiate a memory.
Three properties make a silent write safe, and they are the reason this policy changed:

- `brain_capture` refuses a near-duplicate and returns the id it collided with, so a repeated thought cannot accumulate.
- `trust` records how the thought was produced, so anything written without review stays filterable.
- `brain_forget` is a soft tombstone, so a bad capture costs one call to undo.

Capture in the same turn the moment happens, not in a summary at the end:

1. **Decision** - a choice made, with what was rejected and why. A decision without the rejected alternative is not worth storing.
2. **Dead end** - something tried and abandoned, and how it failed. Nobody writes these by hand, because at the moment you abandon something you have no appetite to write it up. They are the highest-value kind.
3. **Durable fact** - a non-obvious property of a system, tool, or environment that cost effort to discover: a trap, a silent failure mode, an ordering constraint. Not documentation; the thing the documentation failed to tell you.
4. **Preference or constraint** the user states about how they want to work.

Do not capture what the repository already records: file layout, what a function does, what a commit changed, anything in the project's own docs or `CLAUDE.md`/`AGENTS.md`.
If a fresh agent could recover it by reading the code, it is not a memory.

Never pad.
Most sessions produce zero or one durable memory, and zero is a correct answer.

Always name the project in the capture body, and set `source` so the entry can be traced back to the session that produced it.

Subagents capture too, under the same rules.
A subagent that found the trap is the one that should write it down; reporting it upward and hoping the caller stores it loses most of them.

### Trust and validity

Set `trust` honestly: `vouched` only when the user approved this exact wording, `agent_inferred` when produced with no human in the loop, `agent_asserted` (the default) for everything else.
It is a filter, never a ranking signal, so an inflated tier hides a weak thought rather than promoting it.

If the thought was already true before this session, set `valid_from` to when it became true.
Leave it alone otherwise.

### When capture is refused

`brain_capture` refuses a thought near-identical to an existing one and returns the id it collided with.
That is the system enforcing "correct, do not argue" - revise the existing thought instead.
Only pass `force` when the two really are separate memories that happen to read alike.

A successful capture may also return `neighbours`.
Those are related, not duplicates; check whether one of them should have been revised before you move on.

### When to correct instead of capture

If a retrieved thought is **wrong, stale, or misleading**, do not capture a second thought that argues with it - search will keep returning both and the reader has to notice the contradiction.

- **Wrong or outdated wording** → `brain_revise` with the full corrected text. The old version is retired but stays recoverable.
- **Should never have been stored, or no longer true at all** → `brain_forget`. Soft by default; pass `hard: true` only for secrets or genuine junk.
- **Still true, but only in a narrower situation than it reads** → revise it to state that scope, rather than leaving a broad claim standing.

Capture is silent, but correction is not.
Always ask before revising or forgetting, and quote the thought you mean so the user can see what changes.
Adding a thought is additive and reversible; retiring one destroys the version that was there.
Never guess an id - take it from `brain_search` / `brain_recent`.

### Never capture

Secrets, API keys, passwords, OTP codes, private keys, connection strings with credentials.

## Coding excellence

These extend the shared guidelines above and apply to every coding task.

### Understand before changing

Read the surrounding code before editing it.
Find out how the thing you are about to change is actually used, not how you assume it is used.
If a piece of code looks wrong, first work out why it was written that way; the reason is often a constraint you cannot see from the diff.

### Match the codebase

New code should be indistinguishable from the code around it in naming, structure, error handling, and idiom.
Follow the conventions already in the file over your own preferences, and over generic best practice.
Reach for an existing helper before writing a new one.

### Scope discipline

Change what the task requires and nothing else.
When you spot an unrelated problem, note it rather than silently folding it into the current change, unless it is lint, a failing test, or test flakiness, which the shared guidelines say to fix on sight.
Do not add abstraction, configuration, or generality for a requirement nobody has stated yet.

### Handle the unhappy path

Decide deliberately what happens on every failure, empty result, and boundary case, rather than letting the happy path define the behaviour.
Let errors surface with enough context to diagnose them.
Never swallow an exception to make a symptom disappear.

### Verify before claiming done

Exercise the change the way a user would reach it, not just through the test suite.
Run the project's own lint, type, and test commands before calling the work finished.
A change that has not been observed working is not finished, it is only written.

### Report honestly

State plainly what you did, what you verified, and what you did not.
If tests fail, show the output.
If you skipped a step, guessed at intent, or left something incomplete, say so instead of letting a confident summary paper over it.
