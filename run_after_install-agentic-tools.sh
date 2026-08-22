#!/usr/bin/env bash
# The agentic workflow section in dot_claude/CLAUDE.md leans on treehouse
# (pooled git worktrees for parallel agents) and no-mistakes (pre-push
# validation gate), so a machine without them cannot follow the documented
# loop. Runs on every apply rather than run_onchange_ so a machine self-heals
# if the binaries are ever removed; the command -v probe keeps the
# already-installed case instant. Same pattern as run_after_install-axi-clis.sh.
set -euo pipefail

tools=(treehouse no-mistakes)

missing=()
for t in "${tools[@]}"; do
  command -v "$t" >/dev/null 2>&1 || missing+=("$t")
done
[[ ${#missing[@]} -eq 0 ]] && exit 0

os="$(uname -s)"
case "$os" in
  Darwin|Linux)
    # Official installers pick ~/.local/bin when it is on PATH, else /usr/local/bin.
    for t in "${missing[@]}"; do
      case "$t" in
        treehouse) curl -fsSL https://kunchenguid.github.io/treehouse/install.sh | sh ;;
        no-mistakes) curl -fsSL https://raw.githubusercontent.com/kunchenguid/no-mistakes/main/docs/install.sh | sh ;;
      esac
    done
    ;;
  MINGW*|MSYS*)
    # The official installers refuse a non-darwin/linux uname, so pull the
    # windows-amd64 release assets directly. ~/.local/bin is on the Windows
    # user PATH (one-time setup, 2026-08-22).
    dest="$HOME/.local/bin"
    mkdir -p "$dest"
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    for t in "${missing[@]}"; do
      ver="$(curl -fsSL "https://api.github.com/repos/kunchenguid/$t/releases/latest" \
        | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
      if [[ -z "$ver" ]]; then
        echo "install-agentic-tools: could not resolve latest release for $t" >&2
        continue
      fi
      file="$t-$ver-windows-amd64.zip"
      curl -fsSL -o "$tmp/$file" "https://github.com/kunchenguid/$t/releases/download/$ver/$file"
      curl -fsSL -o "$tmp/$t-checksums.txt" "https://github.com/kunchenguid/$t/releases/download/$ver/checksums.txt"
      (cd "$tmp" && grep "$file" "$t-checksums.txt" | sha256sum -c - >/dev/null)
      unzip -o -q "$tmp/$file" -d "$tmp/$t-x"
      find "$tmp/$t-x" -name "$t.exe" -exec mv {} "$dest/" \;
      echo "install-agentic-tools: installed $t $ver to $dest"
    done
    ;;
  *)
    echo "install-agentic-tools: unsupported OS $os; missing: ${missing[*]}" >&2
    ;;
esac
