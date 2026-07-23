---
name: clang-tidy-dev
description: >
  Clang-tidy check development reference. Paths, build commands, test patterns,
  key APIs, conventions. Triggers when working on clang-tidy checks, mentioning
  clang-tidy matchers, or developing new checks.
---

# clang-tidy-dev — check development reference

## Paths

- Checks: `clang-tools-extra/clang-tidy/<module>/`
- Utils: `clang-tools-extra/clang-tidy/utils/`
- Tests: `clang-tools-extra/test/clang-tidy/checkers/<module>/`
- Test input headers: `clang-tools-extra/test/clang-tidy/checkers/Inputs/Headers/std/`
- Docs: `clang-tools-extra/docs/clang-tidy/checks/<module>/`
- Check list: `clang-tools-extra/docs/clang-tidy/checks/list.rst`
- Release notes: `clang-tools-extra/docs/ReleaseNotes.rst`
- Module registration: `clang-tools-extra/clang-tidy/<module>/<Module>TidyModule.cpp`

## Build

```sh
cd /Users/efulop/llvm-project/llvm/out/build/relwithdebug
ninja -j$(sysctl -n hw.ncpu) clang-tidy                    # full binary
ninja -j$(sysctl -n hw.ncpu) clangTidyPerformanceModule    # single module (faster)
```

## Test

```sh
python3 bin/llvm-lit -v /path/to/test.cpp                  # single test
python3 bin/llvm-lit /path/to/checkers/<module>/            # module tests
python3 bin/llvm-lit /path/to/test/clang-tidy/ -j$(sysctl -n hw.ncpu)  # all
```

## Manual check invocation

```sh
bin/clang-tidy --checks='-*,<check-name>' file.cpp -- -std=c++17 \
  -nostdinc++ -isystem <path-to-test-input-headers>
```

## Key Utils

- `utils/TypeTraits.h`: `isExpensiveToCopy`, `hasNonTrivialMoveConstructor`, `hasNonTrivialMoveAssignment`, `isTriviallyDestructible`
- `utils/Matchers.h`: `isExpensiveToCopy` (AST_MATCHER), `isReferenceToConst`, `matchesAnyListedRegexName` (regex matching for NamedDecl)
- `utils/OptionsUtils.h`: `parseStringList` (splits on `;`), `serializeStringList`
- `utils/DeclRefExprUtils.h`: `isOnlyUsedAsConst`, `constReferenceDeclRefExprs`

## Matcher Patterns

```cpp
// Match method by name on a class matching regex list
auto M = cxxMemberCallExpr(callee(cxxMethodDecl(
    hasName("method"), ofClass(matchers::matchesAnyListedRegexName(Types)))));

// Match argument passed to const T& parameter
callExpr(forEachArgumentWithParam(
    ignoringImplicit(expr().bind("arg")),
    parmVarDecl(hasType(lValueReferenceType(pointee(isConstQualified()))))))

// Match binding to const T& variable
varDecl(hasType(lValueReferenceType(pointee(isConstQualified()))),
        hasInitializer(ignoringImplicit(expr().bind("init"))))

// Match const member call on expression
cxxMemberCallExpr(on(ignoringImplicit(expr().bind("obj"))),
                  callee(cxxMethodDecl(isConst())))
```

## Judgment (portable)

- Be **conservative on false positives** — noisy checks hurt adoption more than a missed finding.
- Provide **fix-its only when the fix is unambiguous**; suppress fix-its in macros when unsure.
- Prefer specific AST matchers over broad ones that match unintended code.

## Conventions

- Use `static` functions, not anonymous namespaces (llvm-prefer-static-over-anonymous-namespace)
- Option defaults: explicit literal strings for regex lists (e.g., `"::std::optional;::absl::optional"`)
- No regex metacharacters in defaults — users opt in to wildcards
- `list.rst`: add `"Yes"` after check entry if it provides fixits
- RST docs: double backticks for code (` ``value_or`` `), single backtick for option values (`` `false` ``)
- Test suffixes: `-check-suffixes=A,B` checks both `CHECK-MESSAGES-A` and `CHECK-MESSAGES-B`
- Suppress fixits in macros: `if (Loc.isMacroID()) return std::nullopt;`
- `HasSideEffects(Ctx)` with default `IncludePossibleEffects=true` treats `CXXBindTemporaryExpr` as side effect
- `IgnoreImplicit()` strips `ImplicitCastExpr` and `FullExpr` but NOT `MaterializeTemporaryExpr` or `CXXBindTemporaryExpr`
- `constexpr` implies `const` on member functions in C++11 — avoid in test mocks with non-const overloads
- Test mock headers need include guards; `type_traits` was missing one

## Diagnostic Patterns

```cpp
// Scoped diag to allow follow-up note
{
  auto Diag = diag(Loc, "message %0") << Arg;
  if (fixit)
    Diag << *fixit;
}
// Note must be emitted after Diag is destroyed
diag(NoteLoc, "note text", DiagnosticIDs::Note);
```

## Option Patterns

```cpp
// Constructor: parse regex list with default
OptionalTypes(utils::options::parseStringList(
    Options.get("OptionalTypes", "::std::optional;::absl::optional")))

// storeOptions
Options.store(Opts, "OptionalTypes",
              utils::options::serializeStringList(OptionalTypes));

// Use in matcher
matchers::matchesAnyListedRegexName(OptionalTypes)
```
