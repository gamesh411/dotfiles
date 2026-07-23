---
name: cross-platform-test-adaptation
description: "Adapt a Linux-only test suite to run on macOS and Windows — spawn vs fork, build logger wrappers, symlink resolution, SDK env vars, polling vs sleeping, compile_commands.json format variants."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [testing, cross-platform, macos, ci, test-suite, spawn, intercept-build]
    related_skills: [cross-version-testing, test-driven-development]
---

# Cross-Platform Test Adaptation

Adapt tests that pass on Linux to also run on macOS (and Windows) without
forking the test suite. The goal: one test suite, platform-aware guards,
minimal conditional logic.

## Trigger

- CI matrix expanded to include macOS/Windows and tests fail there
- Tests assume Linux-specific paths (/tmp), env vars (LD_PRELOAD), or
  process models (fork)
- Build tools (intercept-build, gcc) behave differently or are named
  differently on non-Linux platforms

## Key Problem Areas and Fixes

### 1. Multiprocessing: fork → spawn

**Problem:** macOS defaults to `spawn` (since Python 3.8+). Spawned workers
don't inherit parent state — globals, logging config, open file descriptors,
bound sockets are all lost. Fork is also unsafe on macOS due to the Obj-C
runtime.

**Fix:**
- Use `multiprocess` package (not stdlib `multiprocessing`) — it handles
  pickling issues with closures and lambdas that break under spawn.
- Set start method explicitly in the CLI entry point:
  ```python
  if sys.platform != "linux":
      import multiprocess
      multiprocess.set_start_method("spawn")
  ```
- Workers need explicit initialization for state that was inherited under fork:
  ```python
  def init_worker(shared_state, log_level=None):
      GlobalState.dict = shared_state
      if log_level:  # Only under spawn; fork already has logging
          setup_logger(log_level)
  ```
- Guard logging setup: `if multiprocess.get_start_method() != 'fork':`
  to avoid re-running it for forked workers on Linux.

**Pitfall:** `multiprocess.Pool` and `concurrent.futures.ProcessPoolExecutor`
have different constructors (`processes=` vs `max_workers=`) and different
semantics. If aliasing `Pool`, ensure all call sites only use `.map()` — the
shared interface. Don't alias if you need `.apply_async()` or `.submit()`.

### 2. Server Process Reconstruction Under Spawn

**Problem:** A server that forks workers passes the live server object via
inheritance. Under spawn, workers receive picklable args and must reconstruct
the server from scratch.

**Fix:**
- Build a serializable config dict (connection strings, paths, ports)
- Pass a duplicated socket file descriptor via `multiprocess.reduction.DupFd`
- Worker entry point reconstructs: DB connection → session manager →
  HTTP server with pre-bound socket
- Use `HTTPServer.__init__(..., bind_and_activate=False)` then swap
  `self.socket` to the transferred fd

**Pitfall:** `os.getcwd()` is called during spawn process creation. If the
parent's cwd was deleted (common in test suites using temp dirs), the worker
crashes. Chdir to a known-valid workspace before spawning.

**Pitfall:** Creating a `Value('B', False)` shutdown flag inside the spawned
worker is dead code if the worker detects shutdown via SIGINT. Don't create
shared-memory primitives that nobody writes to — document the shutdown
mechanism or remove the unused flag.

### 3. Build Logger: intercept-build Wrapper

**Problem:** LLVM's `intercept-build` is broken on macOS ARM64 (libear.dylib
architecture mismatch with SIP). CodeChecker's `ld-logger` only builds on
Linux. Without a build logger, `CodeChecker log` can't capture compilation
commands.

**Fix:** Create a bear-based wrapper:
```bash
WRAPPER_DIR="$(pwd)/build/intercept-build-wrapper"
mkdir -p "$WRAPPER_DIR"
cat > "$WRAPPER_DIR/intercept-build" << 'EOF'
#!/bin/bash
CDB=""
CMD=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --cdb) CDB="$2"; shift 2 ;;
        --help) echo "intercept-build wrapper using bear"; exit 0 ;;
        *) CMD+=("$1"); shift ;;
    esac
done
[[ -z "$CDB" ]] && CDB="compile_commands.json"
exec bear --output "$CDB" -- "${CMD[@]}"
EOF
chmod +x "$WRAPPER_DIR/intercept-build"
echo "$WRAPPER_DIR" >> "$GITHUB_PATH"
```

Bear provides `intercept-c++` and `intercept-cc` symlinks that CodeChecker
looks for. The wrapper translates the `--cdb` flag to bear's `--output`.

**Pitfall: PATH ordering.** The wrapper directory MUST come before
`llvm@14/bin` on PATH. Homebrew's `llvm@14/bin` also contains an
`intercept-build` (from LLVM's scan-build-py) that uses `libear.dylib` —
broken on macOS ARM64 with SIP (`arm64` vs `arm64e` architecture mismatch).
If the LLVM `intercept-build` is found first, all `CodeChecker log` commands
fail silently with exit code 250. In CI, `$GITHUB_PATH` entries are prepended
in order (last entry = first on PATH), so put the wrapper dir last. Locally,
prepend it explicitly:
```bash
export PATH="$(pwd)/build/intercept-build-wrapper:$PATH"  # wrapper FIRST
```
Verify: `which intercept-build` should show the wrapper, not `llvm@14/bin`.

### 4. compile_commands.json: `command` vs `arguments`

**Problem:** The JSON compilation database spec allows either `"command"`
(shell-escaped string) or `"arguments"` (list). Linux tools typically
produce `command`; bear on macOS produces `arguments`. Code that does
`entry['command']` crashes with KeyError.

**Fix:**
```python
cmd = build_action.get('command') or shlex.join(
    build_action.get('arguments') or [])
```
Or normalize upfront:
```python
for entry in compilation_database:
    if 'command' not in entry and 'arguments' in entry:
        entry['command'] = shlex.join(entry['arguments'])
```

### 5. Path Symlinks: /tmp → /private/tmp

**Problem:** macOS resolves `/tmp` to `/private/tmp`. Tests that hardcode
`/tmp` in both the compilation database and the expected output fail because
`os.path.realpath('/tmp/a.cpp')` returns `/private/tmp/a.cpp`.

**Fix:** Use `os.path.realpath('/tmp')` when constructing test fixtures and
when asserting expected paths:
```python
self.assertEqual(build_action.source,
                 os.path.realpath('/tmp/a.cpp'))
```

### 6. Compiler Naming and Symlinks

**Problem:** Homebrew's gcc installs as `gcc-13`/`g++-13`, not `gcc`/`g++`.
Tests and tools that call `gcc` or `g++` by bare name fail.

**Fix:** Create symlinks in the CI setup:
```bash
GCC_BIN="$(brew --prefix gcc@13)/bin"
ln -sf "$GCC_BIN/g++-13" "$GCC_BIN/g++"
ln -sf "$GCC_BIN/gcc-13" "$GCC_BIN/gcc"
```

Also: Apple's `g++` is a clang shim. Tests that need real GCC must skip or
detect:
```python
@unittest.skipIf(
    not shutil.which('g++') or
    'clang' in os.popen('g++ --version 2>&1').read().lower(),
    "gcc analyzer requires real g++, not Apple clang shim")
```

### 7. macOS SDK Environment Variables

Homebrew's standalone clang doesn't know where the macOS SDK lives. Three
env vars are needed:

| Variable | Why |
|----------|-----|
| `SDKROOT=$(xcrun --show-sdk-path)` | clang can't find `<ctype.h>` etc. without it |
| `ARCHFLAGS=-arch $(uname -m)` | Prevents universal2 build attempts that fail |
| `MACOSX_DEPLOYMENT_TARGET=$(xcrun --show-sdk-version)` | gcc's assembler prints deployment-version warnings to stderr, corrupting SARIF output |
| `CC=/usr/bin/clang` | pip C extensions (python-ldap) need Apple clang, not Homebrew clang@14 |

### 8. Timing-Dependent Tests: Sleep → Poll

**Problem:** Tests that `time.sleep(N)` then assert a state are flaky on
slower platforms (spawn workers take ~42s to import before processing tasks).

**Fix:** Replace sleep-then-check with poll loops:
```python
def _poll_status(self, client, token, status_name, timeout=120):
    expected = Status._NAMES_TO_VALUES[status_name]
    for _ in range(timeout):
        info = client.get_status(token)
        if info and info.status == expected:
            return info
        time.sleep(1)
    self.fail(f"Did not reach {status_name} within {timeout}s")
```

Use platform-aware timeouts:
```python
_POLL_TIMEOUT = 120 if sys.platform == "darwin" else 30
```

### 9. Server Startup Detection

**Problem:** Tests wait for a log line to confirm server started. On macOS
with spawn, the server takes longer and may not produce the expected log
line in time.

**Fix:** Add an HTTP fallback after the log check:
```python
if port and n > 3:
    try:
        urllib.request.urlopen(f"http://localhost:{port}/", timeout=1)
    except urllib.error.HTTPError:
        return  # Any HTTP response means server is ready
    except (ConnectionRefusedError, OSError):
        pass
```

### 10. Platform-Specific Test Skips

Use targeted skip decorators, not `if` guards inside test bodies:

```python
@unittest.skipIf(sys.platform == "darwin",
                 "LD_PRELOAD not applicable on macOS")
def test_ld_preload(self): ...

@unittest.skipIf(sys.platform == "win32",
                 "Unix shell quoting not applicable on Windows")
def test_shell_quoting(self): ...

@unittest.skipIf(sys.platform == "darwin",
                 "gcc -m32 not available on macOS")
def test_mixed_architecture(self): ...
```

### 11. OAuth/HTTP Mock Servers

- Bind to `127.0.0.1` (not `0.0.0.0`) for security and cross-platform
  reliability
- Use `sys.executable` instead of `"python3"` to ensure the right interpreter
- Poll for readiness via socket connection instead of `sleep(5)`:
  ```python
  for i in range(30):
      try:
          s = socket.create_connection(("127.0.0.1", port), timeout=1)
          s.close()
          break
      except (ConnectionRefusedError, OSError):
          sleep(1)
  ```
- Kill stale instances before starting: `pkill -f oauth_server.py`
- Log to a file for debugging startup failures

### 12. Git Template Path

Tests that `git init` with `--template /usr/share/git-core/templates` fail
on macOS where this path doesn't exist. Use a platform-aware template path
or omit the `--template` flag.

### 13. cwd Restoration in Tests

Tests that `os.chdir()` to a temp directory must restore cwd in a `finally`
block — a failing assertion must not leave later tests running from the
wrong directory:
```python
old_pwd = os.getcwd()
os.chdir(proj_dir)
try:
    # test body
finally:
    os.chdir(old_pwd)
```

## Task Test Simplification: Avoid Cascading Count Changes

When converting sleep-based task tests to poll-based tests, the simplest
approach is to use a **single task** with polling for each state transition:

```python
# GOOD: single task, poll for RUNNING then COMPLETED
task_token = client.createDummyTask(5, False)  # long enough to observe RUNNING
info = poll_status(client, task_token, "RUNNING")
# ... assert RUNNING properties ...
info = poll_status(client, task_token, "COMPLETED")
# ... assert COMPLETED properties ...
```

**Anti-pattern:** Creating a long task, cancelling it, then creating a
separate short task for COMPLETED checks. This introduces an extra CANCELLED
task that cascades count assertions across all downstream tests
(test_task_4, test_task_5, etc. assert accumulated task counts). Each
extra task means updating 6–10 assertions in dependent tests, increasing
diff size and review burden for no benefit.

**Rule:** If a test suite has ordinal tests that assert accumulated state
(task counts, history), modifying one test's task count requires updating
every downstream assertion. Avoid this by keeping the task count unchanged.

**Task timeout sweet spot:** Use a task duration of ~5 seconds. This is long
enough to reliably observe RUNNING (the poll loop will catch it during those
5s even if the worker took 42s to start under spawn), and short enough that
the test completes quickly on both Linux (~6s) and macOS (~47s). A 600s
task is overkill — it only makes sense if the test explicitly cancels it.
A 1–2s task is too short: the poll loop might miss the RUNNING window
entirely on slow platforms.

## Critical Review of Cross-Platform Branches

When reviewing a branch that adds cross-platform test support, check:

### A. Accidental removals and misleading comments

1. **Removed documentation:** Docstrings, comments, and .output file format
   docs are often accidentally stripped during refactoring. Verify no
   documentation was removed that isn't directly related to the platform fix.

2. **Misleading comments:** Comments that say "available via Homebrew" when
   the tool is actually installed from GitHub releases. Check that comments
   match the actual install mechanism.

### B. Dead code and side effects in production changes

3. **Dead code in spawn worker reconstruction:** `local_shutdown_flag =
   Value('B', False)` created in a spawned worker but never set by anyone
   (the worker uses SIGINT instead) is dead code. Remove it or document why
   it exists.

4. **Global side effects:** `os.chdir()` in a function that persists after
   the function returns. Use save/restore or a context manager.

### C. Makefile and build path issues

5. **Hardcoded paths in Makefiles:** `$(BUILD_DIR)` changed to `$(ROOT)/build`
   breaks `BUILD_DIR` overrides. The root cause is usually that the parent
   Makefile defaults `BUILD_DIR ?= $(CURRENT_DIR)/build` (relative to the
   subdirectory), while `make package` builds to repo-root/build. Fix the
   root cause (default `BUILD_DIR` in the parent Makefile to `$(ROOT)/build`)
   instead of hardcoding in each consumer.

   **Investigation technique:** Check if Python code already hardcodes the
   correct path. In CodeChecker, `PKG_ROOT = os.path.join(REPO_ROOT, 'build',
   'CodeChecker')` in `__init__.py` is always repo-root/build, regardless of
   what `BUILD_DIR` the Makefile uses. The Makefile variables are only used
   for workspace paths and shutdown commands, so the mismatch is latent on
   Linux (where `BUILD_DIR` is passed via `make test_web`) but breaks on
   macOS CI (where `make -C web test_matrix_sqlite` doesn't pass it).

### D. CI script robustness

6. **Missing `set -euo pipefail`** in CI install scripts — a `brew install`
   failure is silently swallowed.

### E. Per-file necessity audit

7. **Unnecessary changes:** Every changed line should be justified. If
   removing a change doesn't break tests, it shouldn't be in the branch.
   Common unnecessary changes: blank lines added, local-only convenience
   edits (e.g. `uv venv` in a Makefile that expects `python3 -m venv`).

   **Audit methodology:** For each changed file, ask: "Does reverting this
   change break the tests?" If no, revert it. Check:
   - Cosmetic-only changes (blank lines, reformatting) → revert
   - Local convenience edits (different venv tool, different Python version)
     → revert, these are environment-specific
   - Comments that restate what the code does → remove (user prefers
     why-comments, not what-comments)
   - Uncommitted local changes that shouldn't land (oauth_server HOSTNAME
     reverted to 0.0.0.0, Makefile switched to uv) → `git checkout -- <file>`

## Commit Reorganization for Cross-Platform Branches

After verification passes, reorganize commits into a reviewable structure:

1. **Feature commits** (one per logical change, each reviewable independently):
   - multiprocessing shim removal + spawn start method
   - compile_commands.json `arguments` format support
   - server spawn worker reconstruction
   - CI worker count env var feature

2. **Test changes** (cross-platform test adaptations):
   - symlink resolution, platform skips, polling vs sleeping
   - normalization functions for tool version differences

3. **CI changes** (install scripts, workflow YAML):
   - install-deps-macos.sh
   - test.yml matrix expansion

Each commit should be self-contained and pass tests at its commit point
when feasible. The user's repo squash-merges, so intra-branch history is
not critical, but logical grouping makes review easier.

## CI Workflow Patterns

### Matrix Instead of Separate Jobs

```yaml
strategy:
  matrix:
    os: [ubuntu-24.04, macos-latest]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    continue-on-error: ${{ matrix.os == 'macos-latest' }}
    steps:
      - name: Install dependencies (Linux)
        if: runner.os == 'Linux'
        run: sh .github/workflows/install-deps.sh
      - name: Install dependencies (macOS)
        if: runner.os == 'macOS'
        run: sh .github/workflows/install-deps-macos.sh
```

Use `continue-on-error` for non-Linux platforms — flakiness from timing or
tool version differences shouldn't block the PR.

When a job needs platform-specific env vars (e.g. reduced worker counts on
macOS), either set them conditionally in a matrix job or keep a separate job.
The web-macos job in CodeChecker uses `CC_TEST_API_WORKERS=1` and
`CC_TEST_TASK_WORKERS=1` because each spawn process takes ~42s to start and
GitHub Actions macOS runners have only 3 CPUs — spawning 6 worker processes
(3 API + 3 task) is heavy. The env var feature was added to the test lib's
`serv_cmd()` to allow CI to constrain this.

### Shell Scripts: Always Use `set -euo pipefail`

CI dependency install scripts must fail fast:
```bash
#!/bin/bash
set -euo pipefail
```

Without this, a `brew install` or `curl | tar` failure is silently
swallowed and downstream steps fail with confusing errors.

### Infer Installation on macOS

Facebook Infer has no Homebrew formula on macOS GitHub runners. Install
from GitHub releases:
```bash
INFER_VERSION=1.3.0
ARCH=$(uname -m)
curl -sSL "https://github.com/facebook/infer/releases/download/v${INFER_VERSION}/infer-osx-${ARCH}-v${INFER_VERSION}.tar.xz" \
  | sudo tar -C /opt -xJ
sudo ln -sf "/opt/infer-osx-${ARCH}-v${INFER_VERSION}/bin/infer" /usr/local/bin/infer
infer --version
```

Do NOT claim Infer is installed "via Homebrew" in test comments — it is
installed from GitHub releases. All 5 analyzers (clangsa, clang-tidy,
cppcheck, gcc, infer) are expected on both Linux and macOS.

## Verification

After adapting tests:
1. Run the full suite locally on macOS: `make test_unit test_functional`
2. Run with worker count restrictions to catch spawn issues:
   `CC_TEST_API_WORKERS=1 CC_TEST_TASK_WORKERS=1 make test`
3. Verify all skips are platform-specific, not masking real failures
4. Check that Linux CI still passes (don't break Linux to fix macOS)
5. Audit every changed file: if removing the change doesn't break tests,
   it shouldn't be in the branch

## See Also

- `cross-version-testing` — normalizing tool output across versions
- `references/macos-ci-setup.md` — concrete CI install script reference
  with exact commands for Homebrew tools, Infer from GitHub releases, env
  vars, intercept-build wrapper, and local test script pattern
