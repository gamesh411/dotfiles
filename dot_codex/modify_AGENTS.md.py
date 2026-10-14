#!/usr/bin/env python3
"""Manage the shared delegation section while retaining machine-local instructions."""
import re
import sys

START = "<!-- shared-delegation:start -->"
END = "<!-- shared-delegation:end -->"
POINTER = """<!-- shared-delegation:start -->
## Delegation

For tasks with separable routine work, model selection, or cross-CLI workers, read `~/.agents/DELEGATION.md` and follow the shared delegation policy. Keep design and final judgment with the capable lead; offload bounded work when it saves effort, after checking live capacity with `~/.local/bin/agent-capacity --json`. When the assignment starts with `DELEGATED_WORKER` or the environment has `AGENT_DELEGATION_DEPTH=1`, execute only that assignment without further delegation.
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
