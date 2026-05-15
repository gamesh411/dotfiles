---
name: coding-style
description: >
  Coding style rules. Apply to all code written or modified. Always active.
---

# Coding Style

## Comments

- Minimal. Only when WHY not obvious from code.
- Never explain HOW — code does that.
- ASCII only. No unicode, no emdashes, no fancy punctuation.
- Simple grammar. Short sentences. Avoid semicolons.
- Write like a programmer typed it, not generated it.

## Formatting

- Match project existing style. No reformatting untouched code.
- Only format lines part of current change.
- C++/LLVM projects: use clang-format.

## Code Quality

- Correct. Handle edge cases.
- Minimal. No unnecessary abstractions or dead code.
- Secure. Validate input, no injection, no UB.
- Understandable. Clear names, obvious flow.
- Maintainable. Easy to change later.
- Performant. No wasteful allocations or redundant work.