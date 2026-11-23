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
assert SPEC is not None and SPEC.loader is not None
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


FABLE_SCOPED = {**PAYLOAD, "limits": [{"kind": "weekly_scoped", "percent": 10, "resets_at": claude._iso(NOW + 86400),
                                       "scope": {"model": {"display_name": "Fable"}}}]}


def statusline_payload(directory, five=30, seven=50, observed=NOW - 5, windows=("five_hour", "seven_day")):
    transcript = Path(directory) / "session.jsonl"
    transcript.write_text("{}\n")
    os.utime(transcript, (observed, observed))
    limits = {"five_hour": {"used_percentage": five, "resets_at": NOW + 3600},
              "seven_day": {"used_percentage": seven, "resets_at": NOW + 86400}}
    return {"session_id": "s", "transcript_path": str(transcript),
            "rate_limits": {name: limits[name] for name in windows}}


class ClaudeStatuslineTests(unittest.TestCase):
    """Claude Code rewrites its usage cache only on /usage and a daily check, so the
    statusline, which receives live rate limits after every response, records them."""

    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.cache_home = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": self.directory,
                                                  "XDG_CACHE_HOME": self.cache_home}, clear=True))
        self.enterContext(patch.object(claude.time, "time", return_value=NOW))
        self.launches = self.enterContext(patch("subprocess.Popen", side_effect=AssertionError("CLI launched")))
        self.write_config()

    def write_config(self, account="private-account", cache_age=None, payload=FABLE_SCOPED):
        data: dict = {"oauthAccount": {"accountUuid": account}}
        if cache_age is not None:
            data["cachedUsageUtilization"] = {"accountUuid": account, "fetchedAtMs": int((NOW - cache_age) * 1000),
                                              "utilization": copy.deepcopy(payload)}
        (Path(self.directory) / ".config.json").write_text(json.dumps(data))

    def statusline(self, transcript_age=5, **kwargs):
        return statusline_payload(self.directory, observed=NOW - transcript_age, **kwargs)

    def windows(self, result):
        return {window["name"]: window for window in result["windows"]}

    def test_recorded_statusline_makes_a_day_old_cache_fresh(self):
        self.write_config(cache_age=86400)
        self.assertTrue(claude.record_statusline(self.statusline()))
        result = claude.collect()
        self.launches.assert_not_called()
        self.assertEqual((result["quota_status"], result["freshness"]), ("known", "fresh"))
        self.assertEqual(result["observed_at"], claude._iso(NOW - 5))
        self.assertTrue(result["usage_account_matches_cli"])
        windows = self.windows(result)
        self.assertEqual((windows["five_hour"]["remaining_percent"], windows["five_hour"]["status"]), (70, "known"))
        self.assertEqual(windows["seven_day"]["remaining_percent"], 50)
        # Model-scoped limits only exist in the native cache and keep its staleness.
        self.assertEqual((windows["weekly_scoped_0"]["scope"], windows["weekly_scoped_0"]["status"]), ("fable", "stale"))

    def test_statusline_alone_is_enough_without_a_native_cache(self):
        claude.record_statusline(self.statusline())
        result = claude.collect()
        self.assertEqual(result["quota_status"], "known")
        self.assertEqual(set(self.windows(result)), {"five_hour", "seven_day"})

    def test_newer_native_cache_wins_over_an_older_statusline_record(self):
        claude.record_statusline(self.statusline(transcript_age=300))
        self.write_config(cache_age=10)
        result = claude.collect()
        self.assertEqual(result["quota_source"], "native_usage_cache")
        self.assertEqual(self.windows(result)["five_hour"]["remaining_percent"], 80)

    def test_an_older_observation_never_replaces_a_newer_one(self):
        self.assertTrue(claude.record_statusline(self.statusline(five=30, transcript_age=5)))
        self.assertFalse(claude.record_statusline(self.statusline(five=90, transcript_age=100)))
        self.assertEqual(self.windows(claude.collect())["five_hour"]["used_percent"], 30)

    def test_a_record_ages_like_the_native_cache(self):
        claude.record_statusline(self.statusline(transcript_age=601))
        result = claude.collect()
        self.assertEqual((result["quota_status"], result["freshness"]), ("stale", "stale"))

    def test_a_window_the_statusline_dropped_falls_back_to_the_native_one(self):
        self.write_config(cache_age=86400)
        claude.record_statusline(self.statusline(windows=("five_hour",)))
        windows = self.windows(claude.collect())
        self.assertEqual(windows["five_hour"]["status"], "known")
        self.assertEqual(windows["seven_day"]["status"], "stale")

    def test_a_record_for_another_account_is_ignored(self):
        claude.record_statusline(self.statusline())
        self.write_config(account="another-account")
        result = claude.collect()
        self.assertEqual(result["quota_status"], "unknown")
        self.assertEqual(result["error"], "native_usage_cache_unavailable")

    def test_future_transcript_times_are_capped_at_now(self):
        claude.record_statusline(self.statusline(transcript_age=-120))
        self.assertEqual(claude.collect()["observed_at"], claude._iso(NOW))

    def test_payloads_without_rate_limits_or_transcript_record_nothing(self):
        for payload in ({}, {"rate_limits": {}}, {**self.statusline(), "transcript_path": None}, "not a dict"):
            with self.subTest(payload=str(payload)[:30]):
                self.assertFalse(claude.record_statusline(payload))
        self.assertFalse(claude.statusline_path().exists())

    def test_record_is_private_and_holds_no_raw_identity(self):
        claude.record_statusline(self.statusline())
        path = claude.statusline_path()
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        text = path.read_text()
        self.assertNotIn("private-account", text)
        self.assertNotIn("session", text)


class ClaudeStatuslineCommandTests(unittest.TestCase):
    """The statusline command must never print or fail, or it would show in the UI."""

    def test_cli_records_silently_and_survives_garbage(self):
        import subprocess
        import sys
        cli = Path(__file__).resolve().parents[1] / "dot_local/bin/executable_agent-capacity"
        with tempfile.TemporaryDirectory() as config, tempfile.TemporaryDirectory() as cache:
            (Path(config) / ".config.json").write_text(json.dumps({"oauthAccount": {"accountUuid": "a"}}))
            env = {"PATH": os.environ.get("PATH", ""), "CLAUDE_CONFIG_DIR": config, "XDG_CACHE_HOME": cache}
            # A future transcript time is capped to the real clock inside the child.
            for stdin in (json.dumps(statusline_payload(config)), "{not json", ""):
                with self.subTest(stdin=stdin[:10]):
                    done = subprocess.run([sys.executable, str(cli), "--record-claude-statusline"], input=stdin,
                                          env=env, capture_output=True, text=True, timeout=10)
                    self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))
            self.assertTrue((Path(cache) / "agent-capacity" / "claude-statusline.json").exists())


if __name__ == "__main__":
    unittest.main()
