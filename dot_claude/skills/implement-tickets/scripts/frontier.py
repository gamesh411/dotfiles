#!/usr/bin/env python3
"""Print the implementable frontier of a local markdown ticket directory as JSON.

Tickets live at .scratch/<feature>/issues/<NN>-<slug>.md, one file per ticket.
See docs/agents/issue-tracker.md and the to-tickets local template.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DONE = {"done", "resolved", "skipped", "wontfix"}
OPEN_READY = {"ready-for-agent"}
IN_FLIGHT = {"claimed"}
HEADING_RE = re.compile(r"^#\s+(?:(\d{2}):\s*)?(.+?)\s*$", re.MULTILINE)
STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(\S+)", re.MULTILINE)
BLOCKED_RE = re.compile(r"^\*\*Blocked by:\*\*\s*(.+)$", re.MULTILINE)
ID_RE = re.compile(
    r"(\d{2})((?:\s+when it executes)?)",
    re.IGNORECASE,
)
ONLY_EXECUTE_RE = re.compile(r"only execute", re.IGNORECASE)
NONE_RE = re.compile(r"\bnone\b", re.IGNORECASE)
FILE_RE = re.compile(r"^(\d{2})-(.+)\.md$")

def kind_guess(body: str) -> str:
    lower = body.lower()
    if "instrumentation" in lower or "throwaway scratch" in lower:
        return "measure"
    if "decision record" in lower or "coverage matrix" in lower:
        return "scratch"
    return "source"


def parse_blockers(line: str) -> tuple[list[str], list[str], bool]:
    only_execute = bool(ONLY_EXECUTE_RE.search(line))
    if NONE_RE.search(line) and not re.search(r"\d{2}", line):
        return [], [], only_execute
    hard: list[str] = []
    soft: list[str] = []
    for match in ID_RE.finditer(line):
        ticket_id = match.group(1)
        if match.group(2).strip():
            soft.append(ticket_id)
        else:
            hard.append(ticket_id)
    return hard, soft, only_execute


def parse_ticket(path: Path) -> dict | None:
    file_match = FILE_RE.match(path.name)
    if not file_match:
        return None
    ticket_id, slug = file_match.group(1), file_match.group(2)
    text = path.read_text(encoding="utf-8")
    heading = HEADING_RE.search(text)
    title = heading.group(2).strip() if heading else slug
    status_match = STATUS_RE.search(text)
    status = status_match.group(1).strip().lower() if status_match else "unknown"
    blocked_match = BLOCKED_RE.search(text)
    blocked_line = blocked_match.group(1).strip() if blocked_match else "None"
    hard, soft, only_from_line = parse_blockers(blocked_line)
    what = text.split("**Blocked by:**", 1)[0]
    only_execute = only_from_line or bool(ONLY_EXECUTE_RE.search(what))
    hint = None
    if only_execute:
        hint_match = re.search(r"only execute[^\n.]*", blocked_line, re.IGNORECASE)
        if not hint_match:
            hint_match = re.search(r"only execute[^\n.]*", what, re.IGNORECASE)
        hint = hint_match.group(0).strip() if hint_match else "only execute if gate passes"
    return {
        "id": ticket_id,
        "slug": slug,
        "path": str(path),
        "title": title,
        "status": status,
        "blockers": hard,
        "soft_blockers": soft,
        "only_execute": only_execute,
        "only_execute_hint": hint,
        "kind_guess": kind_guess(text),
    }


def blockers_satisfied(ticket: dict, by_id: dict[str, dict]) -> bool:
    def is_done(tid: str) -> bool:
        other = by_id.get(tid)
        return bool(other) and other["status"] in DONE

    if not all(is_done(tid) for tid in ticket["blockers"]):
        return False
    for tid in ticket["soft_blockers"]:
        other = by_id.get(tid)
        if other is None:
            return False
        if other["status"] not in DONE and other["status"] not in OPEN_READY | IN_FLIGHT:
            return False
        if other["status"] not in DONE:
            return False
    return True


def classify(tickets: list[dict]) -> dict:
    by_id = {t["id"]: t for t in tickets}
    frontier = []
    gated = []
    in_flight = []
    remaining = []
    blocked = []
    done = []
    for ticket in tickets:
        if ticket["status"] in DONE:
            done.append(ticket["id"])
            continue
        remaining.append(ticket["id"])
        if ticket["status"] in IN_FLIGHT:
            in_flight.append(ticket["id"])
            continue
        if ticket["status"] not in OPEN_READY:
            blocked.append(ticket["id"])
            continue
        if not blockers_satisfied(ticket, by_id):
            blocked.append(ticket["id"])
            continue
        if ticket["only_execute"]:
            gated.append(ticket["id"])
        else:
            frontier.append(ticket["id"])
    return {
        "frontier": frontier,
        "gated_frontier": gated,
        "in_flight": in_flight,
        "blocked": blocked,
        "remaining": remaining,
        "done": done,
    }


def find_issue_dirs(repo: Path) -> list[Path]:
    scratch = repo / ".scratch"
    if not scratch.is_dir():
        return []
    found = []
    for issues in sorted(scratch.glob("*/issues")):
        if any(FILE_RE.match(p.name) for p in issues.glob("*.md")):
            found.append(issues)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        type=Path,
        help="Ticket directory (.scratch/<feature>/issues). Default: unique remaining feature under --repo.",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Repository root used to discover .scratch/*/issues when --dir is omitted.",
    )
    args = parser.parse_args()
    issue_dir = args.dir
    if issue_dir is None:
        dirs = find_issue_dirs(args.repo)
        with_remaining = []
        snapshots = []
        for candidate in dirs:
            tickets = [t for p in sorted(candidate.glob("*.md")) if (t := parse_ticket(p))]
            snap = classify(tickets)
            snapshots.append((candidate, tickets, snap))
            if snap["remaining"]:
                with_remaining.append((candidate, tickets, snap))
        if len(with_remaining) == 1:
            issue_dir, tickets, snap = with_remaining[0]
        elif len(with_remaining) > 1:
            names = [str(item[0]) for item in with_remaining]
            print(
                json.dumps(
                    {
                        "error": "multiple features have remaining tickets; pass --dir",
                        "candidates": names,
                    },
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 2
        elif snapshots:
            issue_dir, tickets, snap = snapshots[0]
        else:
            print(json.dumps({"error": "no .scratch/*/issues tickets found"}, indent=2))
            return 1
    else:
        tickets = [t for p in sorted(issue_dir.glob("*.md")) if (t := parse_ticket(p))]
        snap = classify(tickets)

    payload = {
        "dir": str(issue_dir),
        "tickets": tickets,
        **snap,
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
