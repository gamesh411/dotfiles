#!/usr/bin/env bash
# The SessionStart hooks in dot_claude/modify_settings.json.py and
# dot_codex/hooks.json.tmpl invoke gh-axi and chrome-devtools-axi,
# so a machine without them greets every Claude Code session with
# "command not found". Runs on every apply rather than run_onchange_ so a
# machine self-heals if the packages are ever removed; the command -v probe
# keeps the already-installed case instant.
# On Windows this runs under Git for Windows bash (see .chezmoi.toml.tmpl),
# where npm's sh shim and the extensionless CLI shims resolve like on Unix.
#
# Cursor Agent has no AXI SessionStart support (lavish-axi setup hooks
# targets Claude Code, Codex, OpenCode, Copilot CLI). Cursor's own
# sessionStart additional_context is also racey, so discovery is the
# bundled SKILL.md, symlinked into ~/.cursor/skills from the npm package.
set -euo pipefail

clis=(gh-axi lavish-axi chrome-devtools-axi)

# cli -> skill directory name inside <pkg>/skills/
skill_name() {
  case "$1" in
    lavish-axi) echo lavish ;;
    *) echo "$1" ;;
  esac
}

missing=()
for cli in "${clis[@]}"; do
  command -v "$cli" >/dev/null 2>&1 || missing+=("$cli")
done

if [[ ${#missing[@]} -gt 0 ]]; then
  # Warn rather than fail: a box without Node should still get its dotfiles,
  # and the Claude hook error will keep the gap visible until Node arrives.
  if ! command -v npm >/dev/null 2>&1; then
    echo "install-axi-clis: npm not found; cannot install: ${missing[*]}" >&2
    echo "install-axi-clis: install Node.js, then re-run chezmoi apply" >&2
    exit 0
  fi
  echo "install-axi-clis: installing ${missing[*]}"
  npm install -g "${missing[@]}"
fi

# Package root of a globally installed AXI CLI. Shims land at either
# <pkg>/dist/cli.mjs (lavish-axi) or <pkg>/dist/bin/<cli>.js (gh-axi,
# chrome-devtools-axi), so walk up until package.json and skills/ coexist.
axi_pkg_dir() {
  local cli="$1"
  local bin real dir
  bin="$(command -v "$cli" 2>/dev/null)" || return 1
  if real="$(readlink -f "$bin" 2>/dev/null)" && [[ -n "$real" ]]; then
    :
  else
    real="$bin"
  fi
  dir="$(dirname "$real")"
  while [[ -n "$dir" && "$dir" != / ]]; do
    if [[ -f "$dir/package.json" && -d "$dir/skills" ]]; then
      echo "$dir"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  return 1
}

# Link the bundled skill into a harness skills dir. Skip (do not clobber) a
# non-symlink that a human already put there.
link_skill() {
  local dest_dir="$1" src="$2" name="$3"
  local dst="$dest_dir/$name"
  mkdir -p "$dest_dir"
  if [[ -L "$dst" ]]; then
    [[ "$(readlink "$dst")" == "$src" ]] && return 0
    rm "$dst"
  elif [[ -e "$dst" ]]; then
    echo "install-axi-clis: $dst exists and is not a symlink; leaving it" >&2
    return 0
  fi
  ln -s "$src" "$dst"
  echo "install-axi-clis: $dst -> $src"
}

for cli in "${clis[@]}"; do
  command -v "$cli" >/dev/null 2>&1 || continue
  pkg="$(axi_pkg_dir "$cli")" || {
    echo "install-axi-clis: could not resolve package dir for $cli" >&2
    continue
  }
  name="$(skill_name "$cli")"
  src="$pkg/skills/$name"
  if [[ ! -d "$src" ]]; then
    echo "install-axi-clis: missing bundled skill $src" >&2
    continue
  fi
  link_skill "$HOME/.cursor/skills" "$src" "$name"
done
