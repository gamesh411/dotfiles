#!/usr/bin/env python3
"""Manage the shared delegation section while retaining machine-local instructions."""
import re
import sys

START = "<!-- shared-delegation:start -->"
END = "<!-- shared-delegation:end -->"
POINTER = """<!-- shared-delegation:start -->
## Delegation

**Delegate** bounded work: the user's standing request is that you use subagents and the installed Codex, Cursor and Claude CLIs, so it counts as being asked.
Codex and Cursor workers draw on separate subscription quota, so delegating saves the lead's budget; uniform, repetitive parts are the best candidates, batched into one brief.
Use the `delegate` skill, or `~/.agents/DELEGATION.md` where skills are unavailable, when a task splits into independent parts, carries mechanical bulk, or wants a second-model review; design, judgment and final acceptance stay with you.
A session whose assignment starts with `DELEGATED_WORKER`, or that runs with `AGENT_DELEGATION_DEPTH=1`, is a worker: complete that assignment yourself and return the result.
<!-- shared-delegation:end -->
"""


def merge(current):
    if START in current or END in current:
        if current.count(START) != 1 or current.count(END) != 1:
            raise ValueError("Expected exactly one managed delegation section")
        pattern = r"(?ms)^" + re.escape(START) + r"\n.*?^" + re.escape(END) + r"[ \t]*(?:\n|$)"
        updated, count = re.subn(pattern, lambda _: POINTER, current)
        if count != 1:
            raise ValueError("Malformed managed delegation section")
        return updated
    separator = "\n\n" if current and not current.endswith("\n") else "\n" if current else ""
    return current + separator + POINTER


if __name__ == "__main__":
    # Windows defaults stdin to the ANSI codepage. The target is UTF-8.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stdout.write(merge(sys.stdin.read()))
