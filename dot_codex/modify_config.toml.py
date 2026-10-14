#!/usr/bin/env python3
"""Seed shared MCP connections while preserving Codex's machine-local settings."""
import json
import sys
import tomllib
from pathlib import Path

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8", newline="\n")
raw = sys.stdin.read()
current = tomllib.loads(raw)
servers = current.get("mcp_servers", {})
repo = Path.home() / "projects/ai-brain"
blocks = []
if "open-brain" not in servers:
    blocks.append(
        '[mcp_servers.open-brain]\n'
        'command = "node"\n'
        f'args = {json.dumps([(repo / "node_modules/tsx/dist/cli.mjs").as_posix(), (repo / "mcp/src/index.ts").as_posix()])}\n'
        f'cwd = {json.dumps(repo.as_posix())}\n'
        'startup_timeout_sec = 30\n'
        '[mcp_servers.open-brain.env]\n'
        'OPEN_BRAIN_CLIENT = "codex"\n'
    )
if "exa" not in servers:
    blocks.append('[mcp_servers.exa]\nurl = "https://mcp.exa.ai/mcp"\n')
if blocks:
    raw = raw.rstrip() + "\n\n" + "\n".join(blocks)
tomllib.loads(raw)
sys.stdout.write(raw)
