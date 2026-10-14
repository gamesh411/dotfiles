#!/usr/bin/env python3
"""Merge tracked Cursor CLI prefs into ~/.cursor/cli-config.json without dropping auth/caches.

The .py extension is what picks the interpreter on Windows, which has no shebang
support; chezmoi strips it from the target name on every platform.
"""
import json
import os
import sys
from pathlib import Path

# Windows defaults stdout to the ANSI codepage and translates "\n" into "\r\n";
# Cursor writes this file as UTF-8 with LF. See modify_private_dot_claude.json.py.
sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8", newline="\n")

PRESERVE = {
    "authInfo",
    "privacyCache",
    "serverConfigCache",
    "autoReviewAvailabilityCache",
}

# CHEZMOI_SOURCE_FILE is relative to CHEZMOI_SOURCE_DIR (script runs from /tmp).
source_file = Path(os.environ["CHEZMOI_SOURCE_DIR"]) / os.environ["CHEZMOI_SOURCE_FILE"]
desired_path = source_file.with_name("_cli-config.desired.json")
desired = json.loads(desired_path.read_text(encoding="utf-8"))

raw = sys.stdin.read()
current = json.loads(raw) if raw.strip() else {}
preserved = {k: current[k] for k in PRESERVE if k in current}

merged = {**current, **desired, **preserved}

# Permission grants accrue per machine as tools get approved interactively, so a
# wholesale replace would revoke them on every apply. Union instead: the desired
# list is the floor, not the ceiling. Removing a grant means editing the target.
allow = dict.fromkeys(
    current.get("permissions", {}).get("allow", [])
    + desired.get("permissions", {}).get("allow", [])
)
merged["permissions"] = {**desired.get("permissions", {}), "allow": list(allow)}

json.dump(merged, sys.stdout, indent=2, ensure_ascii=False)
sys.stdout.write("\n")
