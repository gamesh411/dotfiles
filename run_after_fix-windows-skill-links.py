#!/usr/bin/env python3
"""Repair Windows file symlinks that point at skill directories.

A link created before its target exists can have the file reparse-point type.
Windows lets callers open SKILL.md through it, but directory discovery skips it.
"""
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    home = Path.home()
    for relative in (".agents/skills", ".claude/skills", ".kiro/skills"):
        directory = home / relative
        if not directory.is_dir():
            continue
        for link in directory.iterdir():
            if not link.is_symlink() or link.is_dir():
                continue
            target = os.readlink(link)
            resolved = link.parent / target
            if not resolved.is_dir() or not (resolved / "SKILL.md").is_file():
                continue
            link.unlink()
            try:
                os.symlink(target, link, target_is_directory=True)
            except OSError:
                os.symlink(target, link, target_is_directory=False)
                raise
            print(f"Repaired directory symlink: {link}")
