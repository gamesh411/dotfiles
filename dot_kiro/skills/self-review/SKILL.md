---
name: self-review
description: >
  Critical self-review of a commit before submission. Project-agnostic
  checklist for correctness, edge cases, tests, and commit hygiene.
  Triggers on "review this commit", "self-review", "critically review".
---

# self-review

Review the current commit as an adversarial reviewer. Read the project's
style conventions (coding-style.md, .clang-format, etc.) before judging style.

## Checklist

### Correctness
- Can any cast or type assertion crash? What guarantees the type?
- Can any pointer deref crash? Is null handled or provably impossible?
- Are there type mismatches in arithmetic?
- Does the fix handle ALL callers/paths, not just the triggering one?
- Off-by-one in index/size/boundary computations?

### Edge Cases
- Empty/zero-size inputs?
- Symbolic or unknown values (if applicable)?
- Multi-element declarations or compound statements?
- Static/global vs local lifetime differences?
- Fallback behavior for unexpected types or regions?

### Comments
- Every comment explains WHY, not HOW?
- No comments restating what the code does?
- Named booleans for complex conditions instead of inline comments?

### Tests
- Positive test (bug IS caught)?
- Negative test (no false positive)?
- Boundary test (edge of the fixed range)?
- Tests placed in existing file if one fits?
- Expectations exact, not over-matching?

### Commit Hygiene
- One logical change per commit?
- Message states problem + root cause, not the diff?
- Referenced commit hashes verified?

## Output

List issues by severity:
- **Crash risk**: assertion failures, null derefs
- **Semantic bug**: wrong behavior in some case
- **Style**: non-idiomatic but correct
- **Nit**: cosmetic

Verdict: ship / fix N issues first.
