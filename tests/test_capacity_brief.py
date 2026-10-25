"""The hook's emitted context and worker silence are public output contracts."""
import os
from pathlib import Path
import runpy
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "dot_local/bin/executable_agent-capacity"


class CapacityBriefTest(unittest.TestCase):
    def test_unknown_quota_keeps_manual_delegation_available(self):
        brief = runpy.run_path(str(CLI))["brief_summary"]({
            "providers": [{"provider": name} for name in ("codex", "claude", "cursor")],
            "routing": {"candidates": [], "recommended": None},
        })
        for name in ("codex", "claude", "cursor"):
            self.assertIn(name + " unknown", brief)
        self.assertIn("manual selection; quota may be unknown", brief)
        self.assertEqual(len(brief.splitlines()), 1)

    def test_worker_hooks_exit_silently_before_starting_probes(self):
        for guard in ("AGENT_DELEGATION_DEPTH", "AGENT_CAPACITY_BRIEF"):
            with self.subTest(guard=guard):
                env = dict(os.environ, **{guard: "1", "PATH": ""})
                result = subprocess.run([sys.executable, str(CLI), "--brief"], env=env,
                                        capture_output=True, text=True, timeout=2)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
