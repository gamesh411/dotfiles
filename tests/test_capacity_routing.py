"""New catalog version numbers do not require an eligibility allowlist update."""
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("capacity_routing", ROOT / "dot_local/lib/agent_capacity/routing.py")
assert SPEC is not None and SPEC.loader is not None
routing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(routing)
NOW = datetime(2026, 10, 25, tzinfo=timezone.utc)


def report(model, used=10, fresh=True):
    observed = NOW if fresh else NOW - timedelta(hours=1)
    return {"providers": [{
        "provider": "cursor", "status": "ok", "checked_at": NOW.isoformat(),
        "auth": {"status": "authenticated"},
        "models": {"status": "ok", "entries": [{"id": model}], "observed_at": NOW.isoformat()},
        "quota": {"status": "ok", "observed_at": observed.isoformat(),
                  "usage_account_matches_cli": True, "source": "native usage fixture",
                  "windows": [{"name": "cursor_models", "scope": "cursor_models", "status": "known",
                               "used_percent": used, "remaining_percent": 100 - used,
                               "resets_at": (NOW + timedelta(days=1)).isoformat()}]},
    }]}


class CapacityRoutingTest(unittest.TestCase):
    def test_future_catalog_versions_are_candidates_and_can_be_recommended(self):
        for model in ("cursor-grok-4.8-medium-fast", "cursor-grok-5.0-medium-fast", "grok-99.12-medium-fast"):
            with self.subTest(model=model), patch.object(routing, "_now", return_value=NOW):
                result = routing.recommendations(report(model), "routine")
                self.assertEqual(result["recommended"]["model_id"], model)
                self.assertEqual(result["recommended"]["reasoning_effort"], "medium")

    def test_future_version_still_needs_fresh_available_capacity(self):
        cases: tuple[tuple[dict, str], ...] = (({"used": 100}, "quota_exhausted"), ({"fresh": False}, "quota_stale"))
        for kwargs, reason in cases:
            with self.subTest(kwargs=kwargs), patch.object(routing, "_now", return_value=NOW):
                result = routing.recommendations(report("cursor-grok-99.12-medium-fast", **kwargs), "routine")
                self.assertIsNone(result["recommended"])
                self.assertIn(reason, result["candidates"][0]["reasons"])


def provider(name, models, used=10):
    window = {"status": "known", "used_percent": used, "remaining_percent": 100 - used,
              "resets_at": (NOW + timedelta(days=1)).isoformat()}
    quota: dict = {"status": "ok", "observed_at": NOW.isoformat(), "source": "fixture"}
    if name == "codex":
        quota["buckets"] = [{"limit_id": "codex", "primary": {**window, "resets_at_utc": window["resets_at"]}}]
    elif name == "cursor":
        quota.update(usage_account_matches_cli=True, windows=[{**window, "name": "cursor_models", "scope": "cursor_models"}])
    else:
        quota.update(usage_account_matches_cli=True, windows=[{**window, "name": "seven_day", "scope": "all_models"}])
    return {"provider": name, "status": "ok", "checked_at": NOW.isoformat(), "auth": {"status": "authenticated"},
            "models": {"status": "ok", "entries": [{"id": m} for m in models], "observed_at": NOW.isoformat()},
            "quota": quota}


ALL = [("codex", ["gpt-6-luna", "gpt-6.1-terra", "gpt-6.2-sol", "gpt-6.2-astra"]),
       ("cursor", ["cursor-grok-4.6-medium-fast"]),
       ("claude", ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-1"])]


class TaskPreferenceTest(unittest.TestCase):
    def recommend(self, task, constrained=()):
        rows = [provider(name, models, used=95 if name in constrained else 10) for name, models in ALL]
        with patch.object(routing, "_now", return_value=NOW):
            chosen = routing.recommendations({"providers": rows}, task)["recommended"]
        return chosen["provider"], chosen["family"]

    def test_each_task_class_gets_its_preferred_route(self):
        expected = {"tiny": ("codex", "luna"), "routine": ("codex", "terra"),
                    "substantial": ("claude", "opus"), "review": ("codex", "sol"),
                    "aesthetic": ("claude", "fable")}
        self.assertEqual(set(expected), set(routing.TASKS))
        for task, route in expected.items():
            with self.subTest(task=task):
                self.assertEqual(self.recommend(task), route)

    def test_backups_take_over_when_the_preferred_pool_is_constrained(self):
        self.assertEqual(self.recommend("substantial", constrained=("claude",)), ("cursor", "grok_fast"))
        self.assertEqual(self.recommend("aesthetic", constrained=("claude",)), ("codex", "astra"))
        self.assertEqual(self.recommend("review", constrained=("codex",)), ("claude", "opus"))
        self.assertEqual(self.recommend("tiny", constrained=("codex",)), ("claude", "haiku"))

    def test_opus_precedes_sonnet_wherever_both_are_ranked(self):
        for task, order in routing.ORDERS.items():
            if ("claude", "sonnet") in order:
                with self.subTest(task=task):
                    self.assertLess(order.index(("claude", "opus")), order.index(("claude", "sonnet")))

    def test_unknown_task_is_rejected(self):
        with self.assertRaises(ValueError):
            routing.recommendations({"providers": []}, "huge")


if __name__ == "__main__":
    unittest.main()
