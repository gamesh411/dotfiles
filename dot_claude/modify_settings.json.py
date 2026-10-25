#!/usr/bin/env python3
"""Assert tracked Claude Code settings without reverting what the app writes.

settings.json is not a config file the user only edits by hand: /model,
/effort, the plugin manager, and the notification toggles all rewrite it in
place. Managing it as a plain file meant every `chezmoi apply` silently rolled
back whatever the user had just changed, which is how a hooks change ended up
blocked on unrelated drift.

So the split is by who owns the key:
  - `hooks` is policy. Claude Code never writes it, so it is asserted outright
    and a hand-edit is drift worth reverting.
  - Everything else is either session state or a preference the user changes
    from inside the app, so it is only seeded when absent.

The .py extension is what picks the interpreter on Windows, which has no shebang
support; chezmoi strips it from the target name on every platform.
"""
import json
import os
import sys

# Windows defaults stdout to the ANSI codepage and translates "\n" into "\r\n";
# Claude Code writes this file as UTF-8 with LF. See modify_private_dot_claude.json.py.
sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8", newline="\n")

REPO = os.path.expanduser("~/projects/ai-brain").replace("\\", "/")


def hook_command(script):
    """Build the command Claude Code runs for an Open Brain hook.

    On Windows hooks run through cmd.exe, which cannot execute a .sh file, so
    the command has to name Git Bash explicitly. Same reasoning as the
    interpreter mappings in .chezmoi.toml.tmpl: the scripts want Git for
    Windows' bash, not whichever bash-alike is first on PATH.
    """
    path = f"{REPO}/hooks/{script}"
    if sys.platform != "win32":
        return path
    bash = next(
        (
            candidate
            for candidate in (
                "C:/Program Files/Git/bin/bash.exe",
                "C:/Program Files (x86)/Git/bin/bash.exe",
            )
            if os.path.exists(candidate)
        ),
        "bash",
    )
    return f'"{bash}" "{path}"'


# Open Brain's two hooks. Recall runs on genuine session starts only: after a
# compact the summary already carries the context, and re-injecting it there
# would pay for the same memories twice in one session.
OPEN_BRAIN_HOOKS = {
    "SessionStart": [
        {
            "matcher": "startup|resume|clear",
            "hooks": [
                {
                    "type": "command",
                    "command": hook_command("session-start-recall.sh"),
                    "timeout": 15,
                }
            ],
        }
    ],
    "SessionEnd": [
        {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": hook_command("session-end-mine.sh"),
                    "timeout": 10,
                }
            ],
        }
    ],
}

# Agent-ergonomic wrappers that announce themselves at session start.
AXI_HOOKS = [
    {
        "matcher": "",
        "hooks": [{"type": "command", "command": name, "timeout": 10}],
    }
    for name in ("gh-axi", "chrome-devtools-axi")
]

# lavish-axi's self-announcement is ~10 KB of usage text plus every session it
# has ever opened, re-read on each turn of every session. Only an agent about
# to build a review artifact needs that, so the others get a one-line pointer.
LAVISH_HOOK = {
    "matcher": "",
    "hooks": [
        {
            "type": "command",
            "command": "echo lavish-axi: HTML review artifacts for the user. Run lavish-axi --help before first use.",
            "timeout": 10,
        }
    ],
}

# Live worker headroom, so the lead sees spare capacity before planning.
# Skipped on compaction like recall: the numbers are already in the summary.
CAPACITY_HOOK = {
    "matcher": "startup|resume|clear",
    "hooks": [{"type": "command", "command": "agent-capacity --brief --timeout 8", "timeout": 15}],
}

HOOKS = {
    "SessionStart": AXI_HOOKS + [LAVISH_HOOK, CAPACITY_HOOK] + OPEN_BRAIN_HOOKS["SessionStart"],
    "SessionEnd": OPEN_BRAIN_HOOKS["SessionEnd"],
}

# Seeded on a fresh machine, never re-asserted: the user changes these from
# inside Claude Code and their live value is the correct one.
DEFAULTS = {
    "model": "claude-fable-5[1m]",
    "effortLevel": "high",
    "theme": "auto",
    "terminalProgressBarEnabled": True,
    "agentPushNotifEnabled": True,
}

raw = sys.stdin.read()
current = json.loads(raw) if raw.strip() else {}

current["hooks"] = HOOKS
for key, value in DEFAULTS.items():
    current.setdefault(key, value)

json.dump(current, sys.stdout, indent=2, ensure_ascii=False)
sys.stdout.write("\n")
