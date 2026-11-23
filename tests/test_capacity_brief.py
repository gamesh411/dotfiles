"""The hook's emitted context and worker silence are public output contracts."""
import os
from pathlib import Path
import runpy
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "dot_local/bin/executable_agent-capacity"


def by_task(candidates, recommended=None, unverified=None):
    tasks = runpy.run_path(str(ROOT / "dot_local/lib/agent_capacity/routing.py"))["TASKS"]
    return {task: {"candidates": candidates, "recommended": (recommended or {}).get(task),
                   "preferred_unverified": (unverified or {}).get(task)} for task in tasks}


class CapacityBriefTest(unittest.TestCase):
    def test_unknown_quota_keeps_manual_delegation_available(self):
        brief = runpy.run_path(str(CLI))["brief_summary"]({
            "providers": [{"provider": name} for name in ("codex", "claude", "cursor")],
            "routing_by_task": by_task([]),
        })
        for name in ("codex", "claude", "cursor"):
            self.assertIn(name + " unknown", brief)
        self.assertIn("routine none automatic", brief)
        self.assertEqual(len(brief.splitlines()), 1)

    def test_known_exhausted_quota_is_not_reported_as_unknown(self):
        candidate = {"provider": "codex", "remaining_percent": 0, "eligible": False,
                     "windows": [{"remaining_percent": 0, "resets_at": "2026-10-26T01:10:00Z"}]}
        brief = runpy.run_path(str(CLI))["brief_summary"]({
            "providers": [{"provider": "codex"}],
            "routing_by_task": by_task([candidate]),
        })
        self.assertIn("codex 0% left until 2026-10-26 01:10Z (manual pick)", brief)
        self.assertIn("tiny none automatic", brief)
        self.assertNotIn("unknown", brief)

    def test_every_task_class_gets_its_own_suggestion(self):
        picks = {"routine": {"provider": "cursor", "model_id": "grok-4.7-medium-fast"},
                 "review": {"provider": "codex", "model_id": "gpt-6.2-sol"}}
        brief = runpy.run_path(str(CLI))["brief_summary"]({
            "providers": [{"provider": "codex"}, {"provider": "cursor"}],
            "routing_by_task": by_task([], picks),
        })
        self.assertIn("routine cursor/grok-4.7-medium-fast", brief)
        self.assertIn("review codex/gpt-6.2-sol", brief)
        self.assertIn("substantial none automatic", brief)
        self.assertIn("native subagent", brief)
        self.assertEqual(len(brief.splitlines()), 1)

    def test_unverified_higher_tier_route_leads_its_suggestion(self):
        brief = runpy.run_path(str(CLI))["brief_summary"]({
            "providers": [{"provider": "claude"}, {"provider": "cursor"}],
            "routing_by_task": by_task([], {"routine": {"provider": "cursor", "model_id": "grok-4.7-medium-fast"}},
                                       {"routine": {"provider": "claude", "model_id": "opus"}}),
        })
        self.assertIn("routine claude/opus (quota unverified), else cursor/grok-4.7-medium-fast", brief)

    def test_provider_eligible_for_any_class_is_not_a_manual_pick(self):
        window = [{"remaining_percent": 80, "resets_at": "2026-10-26T01:10:00Z"}]
        def astra(eligible):
            return {"provider": "codex", "remaining_percent": 80, "eligible": eligible, "windows": window}
        routes = by_task([astra(False)])
        routes["aesthetic"]["candidates"] = [astra(True)]
        brief = runpy.run_path(str(CLI))["brief_summary"]({"providers": [{"provider": "codex"}], "routing_by_task": routes})
        self.assertNotIn("manual pick", brief)

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
