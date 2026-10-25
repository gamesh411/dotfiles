"""Offline checks for Claude's prompt-free quota capability probe."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


MODULE = Path(__file__).resolve().parents[1] / "dot_local/lib/agent_capacity/claude.py"
SPEC = importlib.util.spec_from_file_location("claude_capacity_under_test", MODULE)
claude = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(claude)

NOW = 1_800_000_000
PAYLOAD = {"five_hour": {"utilization": 20, "resets_at": claude._iso(NOW + 3600)},
           "seven_day": {"utilization": 40, "resets_at": claude._iso(NOW + 86400)}}


def snapshot(age=0, account="private-account", payload=None):
    return {"observed_at": NOW - age, "account": account,
            "payload": copy.deepcopy(PAYLOAD if payload is None else payload)}


def response(**changes):
    reply = {"session": {"total_cost_usd": 0}, "rate_limits_available": True,
             "rate_limits": copy.deepcopy(PAYLOAD)}
    reply.update(changes)
    return json.dumps({"type": "control_response", "response": {
        "request_id": "agent-capacity-quota", "subtype": "success", "response": reply}})


class ClaudeCapacityTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        self.enterContext(patch.object(claude.time, "time", return_value=NOW))

    def collect(self, output=None, before=None, after=None):
        with patch.object(claude, "read_native_snapshot", side_effect=[before, after]), \
                patch.object(claude, "_capture", return_value=response() if output is None else output) as capture:
            result = claude.collect(binary="future-claude")
        return result, capture

    def test_unknown_future_version_uses_control_only_protocol(self):
        # An executable claiming any future version can participate. It refuses
        # everything except a single control request, with no prompt. Its help
        # deliberately advertises no flags, as supported flags may be hidden.
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "claude"
            executable.write_text(
                "#!" + sys.executable + "\nimport json, sys\n"
                "if sys.argv[1:] == ['--version']:\n    print('999.40.12 (Claude Code)')\n"
                "elif sys.argv[1:] == ['--help']:\n    print('No public options')\n"
                "else:\n"
                "    assert '--input-format' in sys.argv and '--print' in sys.argv\n"
                "    assert sys.argv[sys.argv.index('--tools') + 1] == ''\n"
                "    messages = [json.loads(line) for line in sys.stdin]\n"
                "    assert messages == [{'type': 'control_request', 'request_id': 'agent-capacity-quota', "
                "'request': {'subtype': 'get_usage', 'skip_behaviors': True}}]\n"
                "    print(" + repr(response()) + ")\n")
            executable.chmod(0o700)
            with patch.object(claude, "read_native_snapshot", side_effect=[None, snapshot()]):
                result = claude.collect(binary=str(executable))
        self.assertEqual(result["quota_status"], "known")
        self.assertEqual(result["quota_source"], "native_control_usage")
        self.assertEqual(result["native_model_requests"], 0)
        self.assertNotIn("private-account", json.dumps(result))

    def test_fresh_account_bound_cache_needs_no_cli_call(self):
        with patch.object(claude, "read_native_snapshot", return_value=snapshot(10)), \
                patch.object(claude, "_capture") as capture:
            result = claude.collect(binary="unavailable")
        capture.assert_not_called()
        self.assertEqual(result["quota_status"], "known")
        self.assertEqual(result["quota_source"], "native_usage_cache")
        self.assertEqual(result["age_seconds"], 10)
        self.assertTrue(result["usage_account_matches_cli"])

    def test_unsupported_flags_fail_without_a_weaker_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "claude"
            executable.write_text("#!" + sys.executable + "\nimport sys\n"
                                  "print('unknown option --safe-mode', file=sys.stderr)\n"
                                  "sys.exit(2)\n")
            executable.chmod(0o700)
            with patch.object(claude, "read_native_snapshot", return_value=None), \
                    patch.object(claude, "_capture", wraps=claude._capture) as capture:
                result = claude.collect(binary=str(executable))
        self.assertEqual(result["quota_status"], "unknown")
        self.assertEqual(result["error"], "native_usage_failed")
        self.assertEqual(capture.call_count, 1)
        self.assertIn("--safe-mode", capture.call_args.args[0])
        self.assertEqual(json.loads(capture.call_args.args[2])["type"], "control_request")

    def test_unsupported_control_request_is_unknown(self):
        output = json.dumps({"type": "control_response", "response": {
            "request_id": "agent-capacity-quota", "subtype": "error",
            "error": "private account and token must not appear"}})
        result, _ = self.collect(output=output)
        self.assertEqual(result["error"], "native_usage_control_unsupported")
        self.assertEqual(result["quota_status"], "unknown")
        self.assertNotIn("private account", json.dumps(result))

    def test_response_schema_and_zero_cost_are_required(self):
        for output, error in (
            (response(session={}), "native_usage_zero_cost_unverified"),
            (response(session={"total_cost_usd": False}), "native_usage_zero_cost_unverified"),
            (response(session={"total_cost_usd": 0.01}), "native_usage_zero_cost_unverified"),
            (response(rate_limits_available=False), "native_usage_not_subscription_limits"),
            (response(rate_limits=[]), "native_usage_limits_unavailable"),
            ("{}", "native_usage_response_invalid"),
            (response() + "\n" + response(), "native_usage_response_invalid")):
            with self.subTest(error=error, output=output):
                result, _ = self.collect(output=output)
                self.assertEqual(result["quota_status"], "unknown")
                self.assertEqual(result["error"], error)

    def test_model_messages_and_nonzero_activity_are_rejected(self):
        for activity in ({"type": "assistant"}, {"type": "user"}, {"type": "stream_event"},
                         {"type": "result", "num_turns": 1, "total_cost_usd": 0},
                         {"type": "result", "num_turns": 0, "total_cost_usd": 1}):
            with self.subTest(activity=activity):
                result, _ = self.collect(output=response() + "\n" + json.dumps(activity))
                self.assertEqual(result["error"], "native_usage_unexpected_model_activity")

    def test_result_metadata_must_verify_zero_activity(self):
        result, _ = self.collect(output=response() + '\n{"type":"result"}')
        self.assertEqual(result["error"], "native_usage_zero_cost_unverified")
        result, _ = self.collect(output=response() + '\n{"type":"result","num_turns":0,"total_cost_usd":0}', after=snapshot())
        self.assertEqual(result["quota_status"], "known")

    def test_no_fresh_provenance_cannot_become_known(self):
        for after, error in ((None, "native_usage_provenance_unavailable"),
                             (snapshot(61), "native_usage_refresh_unverified"),
                             (snapshot(-1), "native_usage_refresh_unverified")):
            with self.subTest(after=after):
                result, _ = self.collect(after=after)
                self.assertNotEqual(result["quota_status"], "known")
                self.assertEqual(result["error"], error)

    def test_cache_and_response_measurements_must_match(self):
        changed = copy.deepcopy(PAYLOAD)
        changed["five_hour"]["utilization"] = 21
        result, _ = self.collect(after=snapshot(payload=changed))
        self.assertEqual(result["error"], "native_usage_cache_response_mismatch")
        self.assertEqual(result["quota_status"], "unknown")

    def test_account_change_during_probe_is_rejected(self):
        result, _ = self.collect(before=snapshot(61), after=snapshot(account="another-account"))
        self.assertEqual(result["error"], "native_usage_account_changed_during_probe")
        self.assertEqual(result["quota_status"], "unknown")

    def test_timeout_fallback_preserves_freshness_and_account_checks(self):
        for after, status, error in (
            (None, "unknown", "native_usage_timeout"),
            (snapshot(61), "stale", "native_usage_timeout"),
            (snapshot(), "known", "native_usage_timeout"),
            (snapshot(account="different"), "unknown", "native_usage_account_changed_during_probe")):
            with self.subTest(after=after), \
                    patch.object(claude, "read_native_snapshot", side_effect=[snapshot(61), after]), \
                    patch.object(claude, "_capture", side_effect=claude.ProbeError("native_usage_timeout")):
                result = claude.collect()
                self.assertEqual(result["quota_status"], status)
                self.assertEqual(result["error"], error)

    def test_native_snapshot_rejects_different_account(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": directory}):
            path = Path(directory) / ".config.json"
            data = {"cachedUsageUtilization": {"accountUuid": "cache-account",
                    "fetchedAtMs": NOW * 1000, "utilization": PAYLOAD},
                    "oauthAccount": {"accountUuid": "another-account"}}
            path.write_text(json.dumps(data))
            self.assertIsNone(claude.read_native_snapshot())
            data["oauthAccount"]["accountUuid"] = "cache-account"
            path.write_text(json.dumps(data))
            self.assertEqual(claude.read_native_snapshot()["observed_at"], NOW)

    def test_probe_is_single_bounded_control_call_without_help_or_version(self):
        result, capture = self.collect(after=snapshot())
        self.assertEqual(result["quota_status"], "known")
        self.assertEqual(capture.call_count, 1)
        self.assertLessEqual(capture.call_args.args[1], time.monotonic() + 15)
        self.assertFalse(any("--help" in call.args[0] for call in capture.call_args_list))
        self.assertFalse(any("--version" in call.args[0] for call in capture.call_args_list))

    def test_real_subprocess_timeout_is_bounded(self):
        started = time.monotonic()
        with self.assertRaises(claude.ProbeError) as error:
            claude._capture([sys.executable, "-c", "import time; time.sleep(10)"], started + 0.1)
        self.assertEqual(error.exception.code, "native_usage_timeout")
        self.assertLess(time.monotonic() - started, 2)


if __name__ == "__main__":
    unittest.main()
