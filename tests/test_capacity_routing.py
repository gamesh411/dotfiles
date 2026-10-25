"""New catalog version numbers do not require an eligibility allowlist update."""
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("capacity_routing", ROOT / "dot_local/lib/agent_capacity/routing.py")
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
        for kwargs, reason in (({"used": 100}, "quota_exhausted"), ({"fresh": False}, "quota_stale")):
            with self.subTest(kwargs=kwargs), patch.object(routing, "_now", return_value=NOW):
                result = routing.recommendations(report("cursor-grok-99.12-medium-fast", **kwargs), "routine")
                self.assertIsNone(result["recommended"])
                self.assertIn(reason, result["candidates"][0]["reasons"])


if __name__ == "__main__":
    unittest.main()
