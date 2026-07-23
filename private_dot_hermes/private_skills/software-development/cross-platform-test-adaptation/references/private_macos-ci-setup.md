# macOS CI Dependency Install Script Reference

Concrete reference for adapting a Linux CI pipeline to macOS, derived from
the CodeChecker project. Covers tool installation, env var setup, and
platform-specific gotchas.

## CI Script Robustness

All CI install scripts must start with `set -euo pipefail`:
```bash
#!/bin/bash
set -euo pipefail
```
Without this, a `brew install` or `curl | tar` failure is silently
swallowed and downstream steps fail with confusing errors.

## Tool Installation

### Homebrew Tools

```bash
brew install llvm@14 gcc@13 cppcheck openldap bear
```

- `llvm@14` — provides `clang` (ClangSA analyzer) and `clang-tidy` (clang-tidy analyzer) binaries. CodeChecker's `get_binary_in_path(['clang', 'clang++'], ...)` finds whichever `clang` is first on PATH. Without this, macOS would fall back to Apple's built-in clang which may lack analyzer features.
- `gcc@13` — GCC analyzer (Homebrew's gcc, not Apple's clang shim)
- `cppcheck` — cppcheck analyzer
- `openldap` — headers for python-ldap C extension
- `bear` — build logger (replaces broken intercept-build). On macOS, `ldlogger.so` is not built (Linux-only). CodeChecker's `check_ldlogger()` returns `False`, then `check_intercept()` finds the `intercept-build` wrapper (see below) which calls `bear`. Without bear, `CodeChecker log` has no build logger.

### PATH Setup

```bash
echo "$(brew --prefix llvm@14)/bin" >> "$GITHUB_PATH"
echo "$(brew --prefix gcc@13)/bin" >> "$GITHUB_PATH"
```

### GCC Symlinks

Homebrew installs `gcc-13`/`g++-13`, not `gcc`/`g++`:

```bash
GCC_BIN="$(brew --prefix gcc@13)/bin"
ln -sf "$GCC_BIN/g++-13" "$GCC_BIN/g++"
ln -sf "$GCC_BIN/gcc-13" "$GCC_BIN/gcc"
```

### Facebook Infer (GitHub Releases)

No Homebrew formula on macOS. Install from GitHub releases:

```bash
INFER_VERSION=1.3.0
ARCH=$(uname -m)
curl -sSL "https://github.com/facebook/infer/releases/download/v${INFER_VERSION}/infer-osx-${ARCH}-v${INFER_VERSION}.tar.xz" \
  | sudo tar -C /opt -xJ
sudo ln -sf "/opt/infer-osx-${ARCH}-v${INFER_VERSION}/bin/infer" /usr/local/bin/infer
infer --version
```

Infer v1.3.0 adds backtick-quoting and type annotations to diagnostics
that older versions (v1.1.0) don't produce. See `cross-version-testing`
skill for normalization patterns.

## Environment Variables

Set these in `$GITHUB_ENV` (only in CI context):

```bash
if [ -n "$GITHUB_ENV" ]; then
  echo "SDKROOT=$(xcrun --show-sdk-path)" >> "$GITHUB_ENV"
  echo "ARCHFLAGS=-arch $(uname -m)" >> "$GITHUB_ENV"
  echo "MACOSX_DEPLOYMENT_TARGET=$(xcrun --show-sdk-version)" >> "$GITHUB_ENV"
  echo "CC=/usr/bin/clang" >> "$GITHUB_ENV"
  echo "CXX=/usr/bin/clang++" >> "$GITHUB_ENV"
fi
```

### Why Each Variable

**SDKROOT:** Homebrew's llvm@14 doesn't know where the macOS SDK lives.
Without this, `#include_next <ctype.h>` fails with "file not found".

**ARCHFLAGS:** clang@14 can't build universal2 against the current SDK.
Restrict to host arch.

**MACOSX_DEPLOYMENT_TARGET:** gcc@13 defaults to an older deployment target.
The Xcode assembler prints `clang: warning: overriding deployment version`
to stderr. When using `-fdiagnostics-format=sarif-stderr`, this warning
corrupts the SARIF JSON output. Pinning to SDK version silences it.

**CC/CXX:** pip C extensions (e.g. python-ldap) need Apple's clang to link
against macOS SDK TBD libraries. Homebrew's clang@14 can't link them
(`ld: library ldap_r not found`). CodeChecker selects analyzer binaries
independently of $CC, so this doesn't affect which compiler is analyzed.

## intercept-build Wrapper

LLVM's intercept-build is broken on macOS ARM64 (libear.dylib arch mismatch
with SIP). Bear provides equivalent functionality:

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

**PATH ordering pitfall:** `$GITHUB_PATH` entries are prepended in order —
the last entry ends up first on PATH. The wrapper dir must be appended AFTER
`llvm@14/bin` so it takes precedence. If `llvm@14/bin/intercept-build` is
found first, it uses `libear.dylib` which fails with SIP:
```
dyld: terminating because inserted dylib '.../libear.dylib' could not be
loaded: (mach-o file, but is an incompatible architecture
(have 'arm64', need 'arm64e'))
```
Locally, prepend the wrapper dir explicitly:
`export PATH="$(pwd)/build/intercept-build-wrapper:...rest..."`

## Web Test Worker Configuration

macOS spawn workers are slower to start. Restrict worker counts in CI:

```yaml
env:
  CC_TEST_API_WORKERS: "1"
  CC_TEST_TASK_WORKERS: "1"
```

### Investigating Whether Reduced Worker Counts Are Needed

When deciding whether to constrain worker counts on macOS CI:

1. **Trace the default:** `get_worker_processes()` in `session_manager.py`
   defaults to `cpu_count()`. On GitHub Actions macOS runners, `cpu_count()`
   returns 3.
2. **Calculate spawn cost:** Each spawned worker re-imports the full Python
   stack (~42s on macOS). With default workers (3 API + 3 task = 6 processes),
   that's 6 simultaneous spawn events on a 3-CPU runner.
3. **Check test sensitivity:** Look for tests that create `4 * cpu_count()`
   tasks (e.g. test_task_6_dropping creates 12 tasks on a 3-CPU runner). With
   1 task worker, tasks queue and are handled sequentially; with 3, they run
   in parallel. The test handles both paths (DROPPED for queued, SHUTDOWN for
   running), so correctness isn't affected — but resource pressure is.
4. **Decision:** If tests pass locally with `CC_TEST_*_WORKERS=1` but are
   flaky without, keep the env vars. The feature is a legitimate CI knob,
   not a workaround — it allows constraining resource usage on any platform.

## Auth Requirements (python-ldap)

Web tests that use authentication require python-ldap, which needs openldap
headers (installed via brew) and Apple clang for linking (set via CC env var):

```bash
pip3 install -r web/requirements_py/auth/requirements.txt
```

## Local Test Script Pattern

Mirror the CI workflow locally with a script that:

1. Activates the dev virtualenv
2. Sets up PATH — **intercept-build wrapper MUST come before llvm@14/bin**
   (LLVM's intercept-build uses broken libear.dylib on macOS ARM64):
   ```bash
   export PATH="$(pwd)/build/intercept-build-wrapper:/opt/homebrew/opt/llvm@14/bin:/opt/homebrew/opt/gcc@13/bin:$PATH"
   ```
   Verify: `which intercept-build` must show the wrapper, not llvm@14/bin.
   If it shows llvm@14/bin, `CodeChecker log` will fail with exit code 250
   and a `dyld: terminating because inserted dylib ... could not be loaded`
   error (arm64 vs arm64e SIP mismatch).
3. Creates gcc/g++ symlinks
4. Creates intercept-build wrapper
5. Sets SDKROOT and MACOSX_DEPLOYMENT_TARGET
6. Runs `make pip_dev_deps` + auth requirements + `BUILD_UI_DIST=NO make package`
7. Runs test targets matching CI:
   - Analyzer: `make test_unit test_functional`
   - Web: `CC_TEST_API_WORKERS=1 CC_TEST_TASK_WORKERS=1 make test_matrix_sqlite`
   - For web tests run directly (not via root Makefile), also set
     `BUILD_DIR=$(pwd)/build` (the web Makefile defaults to `web/build`
     which doesn't exist; the package is at repo-root/build)

Use `make package` (not `pip install -e .[dev]`) on macOS — the editable
install fails because ld_logger.so is not built (Linux only).
