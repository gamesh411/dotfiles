#!/usr/bin/env bash
# The SessionStart hooks in dot_claude/settings.json invoke these AXI CLIs,
# so a machine without them greets every Claude Code session with
# "command not found". Runs on every apply rather than run_onchange_ so a
# machine self-heals if the packages are ever removed; the command -v probe
# keeps the already-installed case instant.
# On Windows this runs under Git for Windows bash (see .chezmoi.toml.tmpl),
# where npm's sh shim and the extensionless CLI shims resolve like on Unix.
set -euo pipefail

clis=(gh-axi lavish-axi chrome-devtools-axi)

missing=()
for cli in "${clis[@]}"; do
  command -v "$cli" >/dev/null 2>&1 || missing+=("$cli")
done
[[ ${#missing[@]} -eq 0 ]] && exit 0

# Warn rather than fail: a box without Node should still get its dotfiles,
# and the Claude hook error will keep the gap visible until Node arrives.
if ! command -v npm >/dev/null 2>&1; then
  echo "install-axi-clis: npm not found; cannot install: ${missing[*]}" >&2
  echo "install-axi-clis: install Node.js, then re-run chezmoi apply" >&2
  exit 0
fi

echo "install-axi-clis: installing ${missing[*]}"
npm install -g "${missing[@]}"
