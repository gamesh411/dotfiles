---
name: cross-platform-ci-test-adaptation
description: Adapt Python test suites and CI for macOS and Windows.
version: 0.1.0
author: Hermes
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [CI, Testing, CrossPlatform, Multiprocessing, Spawn]
---

# Cross-Platform CI Test Adaptation

Make a Linux-only Python project's test suite and CI pass on macOS and
Windows. The dominant theme: `fork` is unsafe on macOS (Obj-C runtime
crashes under SIP) and unavailable on Windows, so switch to `spawn` and
handle the consequences — no inherited state, no inherited sockets, no
`LD_PRELOAD`, platform-specific tooling.

## When to Use

- Adding macOS or Windows CI jobs to a Linux-only Python project
- Tests fail on macOS/Windows due to `fork`-vs-`spawn` differences
- `compile_commands.json` uses `arguments` list format instead of `command` string
- Need to reorganize a multi-concern branch into reviewable commits
- Cherry-picking a macOS branch onto a Windows branch (or vice versa)

## Prerequisites

- `multiprocess` package (drop-in replacement for `multiprocessing` with better spawn support)
- `uv venv --python 3.10 venv_dev` for local testing on macOS (editable installs may fail)
- `make package` (not `pip install -e .`) on macOS — `.so` files may not build
- Homebrew: `llvm@14 gcc@13 cppcheck openldap bear`
- Infer: install from GitHub releases (no Homebrew formula)
- `run_local_tests.sh` script that mirrors the CI workflow

## How to Run

Invoke through the `terminal` tool:

```bash
# Rebuild after source changes (stale build artifacts cause test failures)
rm -rf tools/tu_collector/build && BUILD_UI_DIST=NO make package

# Run tests mirroring CI (macOS local)
./run_local_tests.sh analyzer   # analyzer suite only
./run_local_tests.sh web        # web suite only
./run_local_tests.sh            # both
```

## Quick Reference

```
# PATH ordering (CRITICAL): intercept-build wrapper BEFORE llvm@14/bin
export PATH="$(pwd)/build/intercept-build-wrapper:/opt/homebrew/opt/llvm@14/bin:/opt/homebrew/opt/gcc@13/bin:$PATH"
export SDKROOT=$(xcrun --show-sdk-path)
export MACOSX_DEPLOYMENT_TARGET=$(xcrun --show-sdk-version)
export BUILD_DIR=$(pwd)/build
export CC_TEST_API_WORKERS=1 CC_TEST_TASK_WORKERS=1

# Analyzer tests
cd analyzer && make test_unit test_functional

# Web tests
cd web && make test_matrix_sqlite
```

## Procedure

1. **Switch to spawn start method.** In the CLI entry point:
   ```python
   if sys.platform != "linux":
       import multiprocess
       multiprocess.set_start_method("spawn")
   ```
   Replace `from codechecker_common.compatibility.multiprocessing import ...`
   with direct `from multiprocess import ...` or
   `from concurrent.futures import ProcessPoolExecutor as Pool`.

2. **Handle spawn worker state.** Spawn workers don't inherit parent state:
   - Logging: set up explicitly in `init_worker` if `get_start_method() != 'fork'`
   - Shared dicts: pass via `initializer=` and `initargs=`
   - Queues: use `SyncManager().Queue()` instead of `multiprocess.Queue()`
   - Server sockets: use `DupFd` on macOS, `socket.share()/fromshare()` on Windows

3. **Support `arguments` format in `compile_commands.json`.** The `bear`
   intercept-build wrapper produces `arguments` (list), not `command` (string).
   Normalize in tu_collector:
   ```python
   cmd = build_action.get('command') or shlex.join(
       build_action.get('arguments') or [])
   ```

4. **Fix test assumptions.** Common patterns:
   - `/tmp` → `os.path.realpath('/tmp')` (macOS `/tmp` → `/private/tmp` symlink)
   - `os.path.abspath(os.sep)` instead of hardcoded `os.sep` root (Windows drive letters)
   - `os.pathsep` instead of hardcoded `:` for PATH separator
   - Skip `LD_PRELOAD`/`LD_LIBRARY_PATH` tests on non-Linux
   - Skip gcc tests when `g++` is an Apple clang shim
   - Skip `SIGHUP`/`SIGUSR1`/`setpgrp` on Windows (`hasattr(signal, 'SIGHUP')`)
   - Replace `shlex.split(' '.join(cmd))` with direct list `cmd` (Windows paths)
   - Replace fixed `time.sleep(N)` with polling for state transitions (spawn workers take ~42s to start on macOS)
   - Add `stdin=subprocess.DEVNULL` to prevent interactive prompt hangs on Windows

5. **CI worker count override.** Spawn workers are expensive (each re-imports
   full Python stack). Add env vars `CC_TEST_API_WORKERS`/`CC_TEST_TASK_WORKERS`
   that map to `--api-handler-processes`/`--task-worker-processes` server flags.

6. **Install script.** `set -euo pipefail` at top. macOS: `brew install` + bear
   intercept-build wrapper + Infer from GitHub releases + SDKROOT/MACOSX_DEPLOYMENT_TARGET.
   Windows: `choco install llvm cppcheck` + platform-conditional requirements.

7. **Commit organization.** Group logically for reviewability:
   - Feature commits (one per logical change, independently reviewable)
   - Test changes
   - CI changes
   Reorganize ONLY after all changes are verified locally.

## Pitfalls

- **intercept-build wrapper MUST come BEFORE llvm@14/bin on PATH.** LLVM's
  intercept-build uses `libear.dylib` which fails on macOS ARM64 with SIP
  (arm64 vs arm64e mismatch, exit code 250). Verify with `which intercept-build`.
- **`make package` not `pip install -e .`** on macOS — `ld_logger.so` is not
  built (Linux-only). Editable install fails.
- **`MACOSX_DEPLOYMENT_TARGET`** must match SDK version — gcc@13 defaults to
  older target, causing SARIF corruption (warning appended to stderr JSON stream).
- **`SDKROOT`** must be set for Homebrew llvm@14 — it doesn't know where the
  macOS SDK lives (`fatal error: 'ctype.h' file not found`).
- **`CC=/usr/bin/clang CXX=/usr/bin/clang++`** for pip C extensions — Homebrew
  llvm@14 can't link against macOS SDK's TBD libraries.
- **`local_shutdown_flag` in `_build_worker_server`** is a no-op placeholder
  needed to satisfy `CCSimpleHttpServer.__init__` — spawn workers detect
  shutdown via SIGINT, not the shared flag. Don't remove it without changing
  the constructor signature.
- **Cherry-pick conflicts in `web/tests/libtest/env.py`** — macOS removes a
  blank line, Windows adds a `CC_PASS_FILE` block. Keep both: no blank line
  + Windows block.
- **`PKG_ROOT` is hardcoded** to `REPO_ROOT/build/CodeChecker` in
  `web/tests/functional/__init__.py` — Makefile `CODECHECKER_CMD` and
  `CC_TEST_WORKSPACE_ROOT` must use `$(ROOT)/build` to match, not `$(BUILD_DIR)`.

## Verification

```bash
# Verify intercept-build wrapper is found first
which intercept-build  # should show .../build/intercept-build-wrapper/intercept-build

# Verify all 5 analyzers are detected
CodeChecker analyzers --analyzers clangsa,clang-tidy,cppcheck,gcc,infer --details

# Run full test suites
./run_local_tests.sh analyzer  # expect: 252 passed, 6 skipped
./run_local_tests.sh web       # expect: 319 passed, 8 skipped
```
