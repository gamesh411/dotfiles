#!/usr/bin/env bash
# The agentic workflow section in dot_claude/CLAUDE.md leans on treehouse
# (pooled git worktrees for parallel agents) and no-mistakes (pre-push
# validation gate), so a machine without them cannot follow the documented
# loop. Runs on every apply rather than run_onchange_ so a machine self-heals
# if the binaries are ever removed; the command -v probe keeps the
# already-installed case instant. Same pattern as run_after_install-axi-clis.sh.
#
# We resolve versions and pull release assets directly instead of piping the
# upstream install.sh scripts, because those hit api.github.com/.../releases/latest
# which returns 403 once the 60/hour unauthenticated rate limit is spent. The
# /releases/latest web URL redirects to /releases/tag/<ver>, so the tag falls
# out of the effective URL with no API call and no rate limit.
set -euo pipefail

tools=(treehouse no-mistakes)
owner="kunchenguid"

missing=()
for t in "${tools[@]}"; do
  command -v "$t" >/dev/null 2>&1 || missing+=("$t")
done
[[ ${#missing[@]} -eq 0 ]] && exit 0

# Resolve the latest release tag for a repo without the rate-limited JSON API.
# Falls back to the API (authenticated when GITHUB_TOKEN/GH_TOKEN is set) only
# if the redirect ever stops carrying the tag.
latest_tag() {
  local repo="$1" ver
  ver="$(curl -fsSL -o /dev/null -w '%{url_effective}' \
    "https://github.com/$repo/releases/latest" 2>/dev/null \
    | sed -n 's#.*/releases/tag/\([^/]*\)$#\1#p')"
  if [[ -z "$ver" ]]; then
    local auth=()
    local token="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
    [[ -n "$token" ]] && auth=(-H "Authorization: Bearer $token")
    ver="$(curl -fsSL "${auth[@]}" \
      "https://api.github.com/repos/$repo/releases/latest" \
      | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
  fi
  [[ -n "$ver" ]] && printf '%s\n' "$ver"
}

os="$(uname -s)"
case "$os" in
  Darwin) plat_os="darwin"; ext="tar.gz"; bin_suffix="" ;;
  Linux)  plat_os="linux";  ext="tar.gz"; bin_suffix="" ;;
  MINGW*|MSYS*) plat_os="windows"; ext="zip"; bin_suffix=".exe" ;;
  *)
    echo "install-agentic-tools: unsupported OS $os; missing: ${missing[*]}" >&2
    exit 0
    ;;
esac

case "$(uname -m)" in
  x86_64|amd64) arch="amd64" ;;
  arm64|aarch64) arch="arm64" ;;
  *)
    echo "install-agentic-tools: unsupported arch $(uname -m); missing: ${missing[*]}" >&2
    exit 0
    ;;
esac

# ~/.local/bin when it is on PATH (no sudo), else /usr/local/bin.
if printf '%s' "$PATH" | tr ':' '\n' | grep -qx "$HOME/.local/bin"; then
  dest="$HOME/.local/bin"
else
  dest="/usr/local/bin"
fi
mkdir -p "$dest" 2>/dev/null || true

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

for t in "${missing[@]}"; do
  repo="$owner/$t"
  ver="$(latest_tag "$repo")" || true
  if [[ -z "${ver:-}" ]]; then
    echo "install-agentic-tools: could not resolve latest release for $t" >&2
    continue
  fi

  file="$t-$ver-$plat_os-$arch.$ext"
  base="https://github.com/$repo/releases/download/$ver"
  curl -fsSL -o "$tmp/$file" "$base/$file"
  curl -fsSL -o "$tmp/$t-checksums.txt" "$base/checksums.txt"
  (cd "$tmp" && grep "$file" "$t-checksums.txt" | sha256sum -c - >/dev/null)

  bin="$t$bin_suffix"
  if [[ "$ext" == "zip" ]]; then
    unzip -o -q "$tmp/$file" -d "$tmp/$t-x"
  else
    mkdir -p "$tmp/$t-x"
    tar xzf "$tmp/$file" -C "$tmp/$t-x"
  fi
  found="$(find "$tmp/$t-x" -name "$bin" -type f | head -n 1)"
  if [[ -z "$found" ]]; then
    echo "install-agentic-tools: $bin not found in $file" >&2
    continue
  fi

  if [[ -w "$dest" ]]; then
    mv "$found" "$dest/$bin"
  else
    echo "install-agentic-tools: installing to $dest (requires sudo)..."
    sudo mv "$found" "$dest/$bin"
  fi
  chmod +x "$dest/$bin" 2>/dev/null || true
  echo "install-agentic-tools: installed $t $ver to $dest"
done
