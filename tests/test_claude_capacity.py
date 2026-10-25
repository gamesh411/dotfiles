"""Offline checks for Claude's cache-only quota reader."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


MODULE = Path(__file__).resolve().parents[1] / "dot_local/lib/agent_capacity/claude.py"
SPEC = importlib.util.spec_from_file_location("claude_capacity_under_test", MODULE)
claude = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(claude)

NOW = 1_800_000_000
PAYLOAD = {"five_hour": {"utilization": 20, "resets_at": claude._iso(NOW + 3600)},
           "seven_day": {"utilization": 40, "resets_at": claude._iso(NOW + 86400)}}


class ClaudeCacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": self.directory}, clear=True))
        self.enterContext(patch.object(claude.time, "time", return_value=NOW))
        # Collect must read the cache only; any CLI launch is a contract violation.
        self.launches = self.enterContext(patch("subprocess.Popen", side_effect=AssertionError("CLI launched")))

    def write_cache(self, age=0, account="private-account", cli_account=None, payload=None):
        data = {"cachedUsageUtilization": {"accountUuid": account, "fetchedAtMs": int((NOW - age) * 1000),
                                           "utilization": copy.deepcopy(PAYLOAD if payload is None else payload)},
                "oauthAccount": {"accountUuid": account if cli_account is None else cli_account}}
        (Path(self.directory) / ".config.json").write_text(json.dumps(data))

    def test_fresh_account_bound_cache_is_known_without_launching_cli(self):
        self.write_cache(age=10)
        result = claude.collect()
        self.launches.assert_not_called()
        self.assertEqual(result["quota_status"], "known")
        self.assertEqual(result["quota_source"], "native_usage_cache")
        self.assertEqual(result["age_seconds"], 10)
        self.assertEqual(result["freshness"], "fresh")
        self.assertTrue(result["usage_account_matches_cli"])
        self.assertNotIn("error", result)
        windows = {window["name"]: window for window in result["windows"]}
        self.assertEqual(windows["five_hour"]["remaining_percent"], 80)
        self.assertEqual(windows["seven_day"]["remaining_percent"], 60)

    def test_cache_is_fresh_up_to_ten_minutes_and_stale_after(self):
        self.write_cache(age=600)
        self.assertEqual(claude.collect()["quota_status"], "known")
        self.write_cache(age=601)
        result = claude.collect()
        self.launches.assert_not_called()
        self.assertEqual(result["quota_status"], "stale")
        self.assertEqual(result["freshness"], "stale")
        self.assertNotIn("known", {window["status"] for window in result["windows"]})

    def test_stale_cache_is_reported_stale_and_not_refreshed(self):
        self.write_cache(age=601)
        result = claude.collect()
        self.launches.assert_not_called()
        self.assertEqual(result["quota_status"], "stale")
        self.assertEqual(result["freshness"], "stale")
        self.assertNotIn("known", {window["status"] for window in result["windows"]})

    def test_future_dated_cache_is_not_fresh(self):
        self.write_cache(age=-1)
        result = claude.collect()
        self.assertEqual(result["freshness"], "future")
        self.assertNotEqual(result["quota_status"], "known")

    def test_absent_cache_is_unknown_without_launching_cli(self):
        result = claude.collect()
        self.launches.assert_not_called()
        self.assertEqual(result["quota_status"], "unknown")
        self.assertEqual(result["error"], "native_usage_cache_unavailable")
        self.assertFalse(result["usage_account_matches_cli"])

    def test_cache_for_another_account_is_unknown(self):
        self.write_cache(cli_account="another-account")
        result = claude.collect()
        self.assertEqual(result["quota_status"], "unknown")
        self.assertEqual(result["error"], "native_usage_cache_unavailable")
        self.assertNotIn("private-account", json.dumps(result))

    def test_auth_and_provider_overrides_are_rejected(self):
        self.write_cache(age=10)
        for environment, error in (({"ANTHROPIC_API_KEY": "key"}, "native_auth_override_unsupported"),
                                   ({"ANTHROPIC_BASE_URL": "https://proxy.example"}, "native_provider_override_unsupported")):
            with self.subTest(environment=environment), patch.dict(os.environ, environment):
                result = claude.collect()
                self.assertEqual(result["quota_status"], "unknown")
                self.assertEqual(result["error"], error)

    def test_expired_and_null_measurements_are_never_known(self):
        payload = {"five_hour": {"utilization": 20, "resets_at": claude._iso(NOW - 1)},
                   "seven_day": {"utilization": None, "resets_at": claude._iso(NOW + 86400)}}
        self.write_cache(age=10, payload=payload)
        result = claude.collect()
        windows = {window["name"]: window for window in result["windows"]}
        self.assertEqual(windows["five_hour"]["status"], "expired")
        self.assertEqual(windows["seven_day"]["status"], "unknown")
        self.assertEqual(result["quota_status"], "unknown")

    def test_weekly_scoped_model_window_keeps_its_scope(self):
        payload = {"limits": [{"kind": "weekly_scoped", "percent": 30,
                               "resets_at": claude._iso(NOW + 86400),
                               "scope": {"model": {"id": "claude-opus-5", "display_name": "Opus"}}}]}
        self.write_cache(age=10, payload=payload)
        result = claude.collect()
        [window] = [window for window in result["windows"] if window["name"] == "weekly_scoped_0"]
        self.assertEqual((window["scope"], window["model_id"], window["remaining_percent"]), ("opus", "claude-opus-5", 70))

    def test_native_snapshot_rejects_different_account(self):
        path = Path(self.directory) / ".config.json"
        data = {"cachedUsageUtilization": {"accountUuid": "cache-account",
                "fetchedAtMs": NOW * 1000, "utilization": PAYLOAD},
                "oauthAccount": {"accountUuid": "another-account"}}
        path.write_text(json.dumps(data))
        self.assertIsNone(claude.read_native_snapshot())
        data["oauthAccount"]["accountUuid"] = "cache-account"
        path.write_text(json.dumps(data))
        self.assertEqual(claude.read_native_snapshot()["observed_at"], NOW)


if __name__ == "__main__":
    unittest.main()
