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

## CSA Checker Patterns

### Path Notes (NoteTag)

Emit context on diagnostic paths so users understand the report without
reading surrounding code.

```cpp
const NoteTag *Note = C.getNoteTag(
    [Region](PathSensitiveBugReport &BR, llvm::raw_ostream &OS) {
      if (BR.getBugType().getCategory() != "My checker category")
        return;
      if (!BR.isInteresting(Region))
        return;
      std::string Name = Region->getDescriptiveName();
      if (Name.empty())
        OS << "Fallback message";
      else
        OS << "Action on " << Name << " here";
    });
C.addTransition(State, Note);
```

The callback is only invoked on reports where `Region` is interesting.
Always filter by category AND interestingness to avoid noise on unrelated
bug paths. Mark regions interesting in `reportBug` with
`Report->markInteresting(Region)`.

### Checker Options

Define in `Checkers.td`:
```
def MyChecker : Checker<"MyChecker">,
  HelpText<"...">,
  CheckerOptions<[
    CmdLineOption<Boolean, "OptionName", "Description", "false", Released>
  ]>;
```

Read in registration:
```cpp
void ento::registerMyChecker(CheckerManager &Mgr) {
  auto *Chk = Mgr.registerChecker<MyChecker>();
  Chk->Option = Mgr.getAnalyzerOptions().getCheckerBooleanOption(
      Mgr.getCurrentCheckerName(), "OptionName");
}
```

### GDM (Global Data Map) for Custom State

```cpp
REGISTER_MAP_WITH_PROGRAMSTATE(MyMap, const MemRegion *, MyState)
REGISTER_SET_WITH_PROGRAMSTATE(MySet, const MemRegion *)
REGISTER_LIST_WITH_PROGRAMSTATE(MyList, const MemRegion *)
```

ImmutableList is a stack (prepend-only). Remove requires rebuild:
```cpp
ImmutableList<T> NewList = Factory.getEmptyList();
for (auto I : OldList)
  if (I != ToRemove)
    NewList = Factory.add(I, NewList);
```

### Bug Reports

```cpp
ExplodedNode *N = C.generateErrorNode();
if (!N) return;
auto Report = std::make_unique<PathSensitiveBugReport>(*BT, Msg, N);
Report->addRange(Expr->getSourceRange());
Report->markInteresting(Region);  // enables NoteTag filtering
C.emitReport(std::move(Report));
```

### Coverage Instrumentation

See `/Users/efulop/.kiro/notes/csa-checker-coverage-method.md`.
Key: compile single .o with `-fprofile-instr-generate -fcoverage-mapping`,
swap into build, relink dylib+binary with `-fprofile-instr-generate`.

### Test Conventions

- Multi-line RUN with backslash continuation
- Separate test files per feature (e.g. `pthreadlock-notes.c`)
- `-analyzer-output text` for path note tests
- `expected-warning` + `expected-note` on same or `@-1` lines
- System headers via `Inputs/system-header-simulator-*.h`

### Common Pitfalls

- `checkRegionChanges` can invalidate LockMap regions but not
  ImmutableList entries, causing duplicates in ordered collections.
- `wasInlined` bailout prevents modeling of wrapper functions. Remove
  it and handle inlined semantics explicitly.
- Correlated conditions across branches cause infeasible paths. The
  analyzer assumes branch conditions independently, so
  `if (cond) lock()` followed by `if (flag_set_inside_cond) unlock()`
  can explore the impossible path where lock was skipped but unlock runs.
