#!/usr/bin/env python3
"""Reuse Open Brain recall; detach Codex mining within SessionEnd's 3s limit."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    repo = Path.home() / "projects/ai-brain"
    node = shutil.which("node")
    tsx = repo / "node_modules/tsx/dist/cli.mjs"
    if not node or not tsx.is_file():
        return
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        return
    mode = sys.argv[1]
    if mode == "recall":
        subprocess.run(
            [node, str(tsx), str(repo / "hooks/session-start-recall.ts")],
            input=json.dumps(payload).encode(), stderr=subprocess.DEVNULL, timeout=12,
        )
    elif mode == "mine" and isinstance(payload.get("transcript_path"), str):
        log_dir = Path.home() / ".config/open-brain"
        log_dir.mkdir(parents=True, exist_ok=True)
        # Use a temporary file for stdin so the parent cannot block on a pipe.
        import tempfile
        with tempfile.TemporaryFile() as source, (log_dir / "codex-tail.log").open("ab") as log:
            source.write(json.dumps(payload).encode())
            source.seek(0)
            options = {"start_new_session": True} if os.name != "nt" else {
                "creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            }
            subprocess.Popen(
                [node, str(tsx), str(Path(__file__).with_name("mine-codex.mjs"))],
                stdin=source, stdout=log, stderr=log, close_fds=True, **options,
            )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        pass  # A missing dependency or malformed payload must not break a session.
