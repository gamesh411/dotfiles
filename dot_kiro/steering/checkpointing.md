---
inclusion: always
---

# Open Brain checkpointing

Same capture policy as every other harness (Claude Code, Cursor) - not a Kiro-only mode.

Tools: `brain_search`, `brain_recent`, `brain_stats`, `brain_capture`, `brain_revise`, `brain_forget`.

## When to search

Search **before** you form a plan on an unfamiliar project, not after you get stuck.
A brain read once the assumptions are already made cannot change them, which is the whole point of having one.

1. `brain_search` for the current project / topic
2. `brain_recent` if search is thin

Search returns nothing when nothing is relevant, so an empty result is information rather than a failure.

## When to capture

**Capture without asking.** Do not offer, do not propose, do not interrupt the work to negotiate a memory.
Three properties make a silent write safe, and they are the reason this policy changed:

- `brain_capture` refuses a near-duplicate and returns the id it collided with, so a repeated thought cannot accumulate.
- `trust` records how the thought was produced, so anything written without review stays filterable.
- `brain_forget` is a soft tombstone, so a bad capture costs one call to undo.

Capture in the same turn the moment happens, not in a summary at the end:

1. **Decision** - a choice made, with what was rejected and why → `decision` / `tried`
2. **Dead end** - something tried and abandoned, and how it failed → `tried` / `insight`
3. **Durable fact** - a trap, a silent failure mode, an ordering constraint that cost effort to discover → `insight`
4. **Project context** - stack, conventions, constraints that are not written down anywhere → `project_context` / `constraint`
5. **Preference** the user states about how they want to work → `preference`

Prefer short, durable, outcome-level wording.
Type labels stay English; the body may be Hungarian.

Do not capture what the repository already records: file layout, what a function does, what a commit changed, anything in the project's own docs.
If a fresh agent could recover it by reading the code, it is not a memory.

Never pad.
Most sessions produce zero or one durable memory, and zero is a correct answer.

Always name the project in the capture body, and set `source` so the entry can be traced back to the session that produced it.

## Trust and validity

Set `trust` honestly: `vouched` only when the user approved this exact wording, `agent_inferred` when produced with no human in the loop, `agent_asserted` (the default) for everything else.
It is a filter, never a ranking signal, so an inflated tier hides a weak thought rather than promoting it.

If the thought was already true before this session, set `valid_from` to when it became true.
Leave it alone otherwise.

## When capture is refused

`brain_capture` refuses a thought near-identical to an existing one and returns the id it collided with.
Revise that thought instead of storing a second copy; only pass `force` when the two really are separate memories that happen to read alike.

A successful capture may also return `neighbours`.
Those are related, not duplicates; check whether one of them should have been revised before you move on.

## When to correct instead of capture

If a retrieved thought is **wrong, stale, or misleading**, do not capture a second thought that argues with it - search keeps returning both and the reader has to notice the contradiction.

- Wrong or outdated wording → `brain_revise` with the full corrected text. The old version is retired but stays recoverable.
- Should never have been stored, or no longer true at all → `brain_forget`. Soft by default; `hard: true` only for secrets or genuine junk.
- Still true, but only in a narrower situation than it reads → revise it to state that scope.

Capture is silent, but correction is not.
Always ask before revising or forgetting, and quote the thought you mean.
Adding a thought is additive and reversible; retiring one destroys the version that was there.
Never guess an id - take it from `brain_search` / `brain_recent`.

## When NOT to capture

Trivial reads and searches, mid-task steps, duplicates, anything already in the docs or the code.

## Never capture

Secrets, API keys, passwords, OTP codes, private keys, connection strings with credentials.
