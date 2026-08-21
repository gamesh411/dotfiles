#!/usr/bin/env python3
"""Assert tracked MCP servers in ~/.claude.json without dropping session state.

Claude Code has no settings.json key for MCP servers - user-scope definitions
live only in ~/.claude.json, alongside mutable state (startup counts, per-project
history, onboarding flags). So this merges rather than replaces, mirroring
modify_cli-config.json.py for Cursor.

The .py extension is what picks the interpreter on Windows, which has no shebang
support; chezmoi strips it from the target name on every platform.
"""
import json
import os
import sys

# Windows defaults stdout to the ANSI codepage and translates "\n" into "\r\n".
# Claude Code writes this file as UTF-8 with LF, so without this every apply
# would rewrite all ~900 lines and chezmoi would report drift forever.
sys.stdout.reconfigure(encoding="utf-8", newline="\n")

# Expanded here rather than left as a literal "~": these args are passed
# straight to execve with no shell, so a tilde would resolve to a path like
# $CWD/~/projects and the server would fail to start on every platform.
DESIRED_MCP_SERVERS = {
    "open-brain": {
        # Claude Code writes this key itself; omitting it leaves permanent drift.
        "type": "stdio",
        "command": "npx",
        "args": [
            "tsx",
            os.path.normpath(os.path.expanduser("~/projects/ai-brain/mcp/src/index.ts")),
        ],
        "env": {"OPEN_BRAIN_CLIENT": "claude"},
    },
}

raw = sys.stdin.read()
current = json.loads(raw) if raw.strip() else {}

current["mcpServers"] = {**current.get("mcpServers", {}), **DESIRED_MCP_SERVERS}

# No trailing newline: Claude Code writes this file without one, so emitting it
# here would leave chezmoi permanently reporting drift.
json.dump(current, sys.stdout, indent=2, ensure_ascii=False)
