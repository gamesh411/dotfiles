---
name: llvm-dev
description: >
  LLVM/Clang project reference. Paths, build commands, test invocation,
  key APIs. Triggers when working in llvm-project or mentioning clang,
  LLVM, static analyzer, lit tests.
---

# llvm-dev — project reference

## Paths

- Source: `/Users/efulop/llvm-project`
- Build: `/Users/efulop/llvm-project/llvm/out/build/relwithdebug`
- Checkers: `clang/lib/StaticAnalyzer/Checkers/`
- Core: `clang/lib/StaticAnalyzer/Core/`
- Tests: `clang/test/Analysis/`
- Checker registration: `clang/include/clang/StaticAnalyzer/Checkers/Checkers.td`

## Build

```sh
cd /Users/efulop/llvm-project/llvm/out/build/relwithdebug
ninja -j$(sysctl -n hw.ncpu) clang
```

## Test

```sh
bin/llvm-lit -v /path/to/test.c              # single test
bin/llvm-lit -j$(sysctl -n hw.ncpu) /dir/    # directory
```

## Analyze Directly

```sh
bin/clang -cc1 -analyze -setup-static-analyzer \
  -analyzer-checker=<name> /path/to/file.c
```

Add `-analyzer-checker=debug.ExprInspection` for `clang_analyzer_dump()`,
`clang_analyzer_eval()`, `clang_analyzer_printState()`.

## Remotes

- `origin`: `github.com:gamesh411/llvm-project.git`
- `upstream`: `github.com:llvm/llvm-project.git`

## Key APIs (Static Analyzer)

- `SVal`, `NonLoc`, `Loc` — symbolic values
- `MemRegion`, `VarRegion`, `ElementRegion` — memory regions
- `ElementRegion::getIndex()` — returns `NonLoc` by construction
- `ProgramState::getSVal()`, `getLValue()` — state queries
- `SValBuilder::evalBinOp()` — arithmetic with type promotion
- `SValBuilder::evalBinOpNN()` — NonLoc-only, can return UnknownVal

## Known Broken Tests (pre-existing)

- `Analysis/func-mapping-test.cpp`
- `Analysis/analyzeOneFunction.cpp`
- `Analysis/ctu/import-type-decl-definition.c`
