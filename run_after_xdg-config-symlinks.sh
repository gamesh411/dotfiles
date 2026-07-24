#!/usr/bin/env bash
# When XDG_CONFIG_HOME is a machine-specific dir (e.g. ~/.config-ubuntu-24.04),
# point its chezmoi-managed entries at the canonical ~/.config / ~/.cursor paths.
set -euo pipefail

xdg="${XDG_CONFIG_HOME:-}"
[[ -n "$xdg" && "$xdg" != "$HOME/.config" && -d "$xdg" ]] || exit 0

link_dir() {
  local src="$1" dst="$2"
  [[ -e "$src" || -L "$src" ]] || return 0
  if [[ -L "$dst" && "$(readlink -f "$dst")" == "$(readlink -f "$src")" ]]; then
    return 0
  fi
  if [[ -e "$dst" || -L "$dst" ]]; then
    mv "$dst" "$dst.bak-before-xdg-link-$(date +%Y%m%d%H%M%S)"
  fi
  ln -s "$src" "$dst"
  echo "xdg-link: $dst -> $src"
}

# Chezmoi-managed under ~/.config
for name in nvim ghostty zellij; do
  link_dir "$HOME/.config/$name" "$xdg/$name"
done

# Cursor CLI follows XDG_CONFIG_HOME/cursor; chezmoi tracks ~/.cursor.
# Directory symlink so atomic writes (cli-config.json) stay on the managed tree.
link_dir "$HOME/.cursor" "$xdg/cursor"
