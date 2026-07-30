# Global Guidelines

Shared rules live with the Cursor rule files so every harness reads the same source.

@~/.cursor/rules/general-guidelines.mdc

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
