---
name: coding-discipline
description: >
  Code writing principles and style rules. Use when writing, modifying, or
  reviewing code. Covers simplicity, surgical changes, goal-driven execution,
  comment style, and formatting.
---

# Coding Discipline

## Principles

### Think Before Coding
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them.
- If a simpler approach exists, say so. Push back when warranted.

### Simplicity First
- Minimum code that solves the problem. Nothing speculative.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- If you write 200 lines and it could be 50, rewrite it.

### Surgical Changes
- Touch only what you must. Clean up only your own mess.
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken. Match existing style.
- Remove imports/variables YOUR changes made unused. Don't remove pre-existing dead code.
- The test: every changed line traces directly to the user's request.

### Goal-Driven Execution
- Transform tasks into verifiable goals before implementing.
- "Fix the bug" -> reproduce first, then fix, then verify.
- For multi-step tasks, state a brief plan with verification for each step.

## Style

### Comments
- Minimal. Only when WHY not obvious from code.
- Never explain HOW. ASCII only. No emdashes. Short sentences.

### Formatting
- Match project existing style. No reformatting untouched code.
- Only format lines part of current change.
- C++/LLVM projects: use clang-format.

### Code Quality
- Correct. Handle edge cases.
- Secure. Validate input, no injection, no UB.
- Minimal. No unnecessary abstractions or dead code.
- Understandable. Clear names, obvious flow.
- Performant. No wasteful allocations or redundant work.
