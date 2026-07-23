---
name: cross-version-testing
description: Handle CLI tool output format changes across versions in tests via normalization — strip version-specific artifacts before comparison.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [testing, cross-platform, normalization, CLI, comparators]
---

# Cross-Version Output Normalization in Tests

When a CLI tool (compiler, linter, static analyzer) changes its diagnostic
output format between versions, exact-string-match tests break. Don't fork
expected-output files per version. Add normalization functions that strip
version-specific artifacts from **both** actual and expected output before
asserting equality.

## Trigger

- You see a test failure where the only difference between actual and
  expected is formatting (backtick quoting, type annotations, ANSI codes,
  whitespace, etc.) and the formatting differs between tool versions.
- A CI matrix runs different tool versions per platform (e.g. Linux has
  infer v1.1.0, macOS has v1.3.0).

## Pattern

```python
def compare_outputs(actual: str, expected: str, normalizers: list) -> None:
    a, e = actual, expected
    for norm in normalizers:
        a, e = norm(a), norm(e)
    assert a == e
```

Apply normalizers to *both* sides so the expected-output file can use
whatever format is most readable and still match all versions.

## Example: Facebook Infer v1.1.0 → v1.3.0

See `references/infer-diagnostic-format.md` for the session-derived failure shape and macOS GitHub release install recipe.

infer changed diagnostic formatting in two ways:

| Aspect | v1.1.0 | v1.3.0 |
|--------|--------|--------|
| Identifier quoting | `` `&b` `` (backtick-quoted) | `&b` (plain) |
| Type annotation | none | `(type int)` / `(type int*)` |

### Normalizers

```python
def normalize_quotes(s: str) -> str:
    """Strip backtick quoting from infer diagnostics."""
    return s.replace('`', '')

def normalize_infer_type(s: str) -> str:
    """Strip '(type ...)' annotations from infer diagnostics."""
    return re.sub(r'\s*\(type\s+\w+(?:\s*\*)*\)', '', s)
```

Both applied to actual and expected before comparison — all versions
converge to the same canonical form:

```
v1.1.0:  "The value written to `&b` is never used."
  → normalize_quotes: "The value written to &b is never used."
  → normalize_infer_type: "The value written to &b is never used."

v1.3.0:  "The value written to &b (type int) is never used."
  → normalize_quotes: "The value written to &b (type int) is never used."
  → normalize_infer_type: "The value written to &b is never used."
```

## Pitfalls

- **Regex too narrow for multi-word types**: `r'\s*\(type\s+\w+(?:\s*\*)*\)'`
  handles `int` and `int*` but not `const char*` or `unsigned int`. If the
  tool starts emitting compound types, broaden to
  `r'\s*\(type\s+[^)]+\)'` — strip everything inside the parentheses.
  This is the recommended form for new code; the narrower regex was only
  appropriate when the tool was known to emit single-word types only.
- **Don't over-normalize**: keep normalizers narrow. Strip only formatting
  artifacts known to vary by version, not checker names, severity, file,
  line, column, or message semantics.

## Other Common Normalizers

| Artifact | Normalizer |
|----------|-----------|
| ANSI escape codes | `re.sub(r'\x1b\[[0-9;]*m', '', s)` |
| Unicode curly quotes | `s.replace('\u2018', "'").replace('\u2019', "'")` |
| Backslash-escaped quotes | `s.replace("\\'", "'")` |
| Backtick-quoted identifiers | `s.replace('`', '')` |
| Build logger name | `s.replace('Using intercept-build.', 'Using CodeChecker ld-logger.')` |
| Timestamps | `re.sub(r'\[\w+ \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]', '[]', s)` |
| Analyzer version warnings | Add to skip-prefixes list, not normalizer |

## When NOT to Use

- When the **semantic meaning** of the output changes (not just formatting)
- When normalization would mask real regressions
- When it's simpler to just update the expected output file (single-version CI)
