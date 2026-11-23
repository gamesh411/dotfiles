"""Routing follows the user's quality tiers, then spare capacity, from live catalog entries."""
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
GROK = "grok-4.7-high-fast"


def report(models, used=10, fresh=True):
    observed = NOW if fresh else NOW - timedelta(hours=1)
    return {"providers": [{
        "provider": "cursor", "status": "ok", "checked_at": NOW.isoformat(),
        "auth": {"status": "authenticated"},
        "models": {"status": "ok", "entries": [{"id": m} for m in models], "observed_at": NOW.isoformat()},
        "quota": {"status": "ok", "observed_at": observed.isoformat(),
                  "usage_account_matches_cli": True, "source": "native usage fixture",
                  "windows": [{"name": "cursor_models", "scope": "cursor_models", "status": "known",
                               "used_percent": used, "remaining_percent": 100 - used,
                               "resets_at": (NOW + timedelta(days=1)).isoformat()}]},
    }]}


class CursorModelPinTest(unittest.TestCase):
    """Cursor work uses the newest Grok version at high-fast; other Grok entries stay visible but never qualify."""

    CATALOG = ["cursor-grok-4.6-high-fast", "grok-4.7-low-fast", "grok-4.7-medium-fast",
               "grok-4.7-high-fast", "grok-4.7-xhigh-fast"]

    def assert_only(self, catalog, model):
        for task in ("tiny", "research"):
            with self.subTest(task=task, model=model), patch.object(routing, "_now", return_value=NOW):
                result = routing.recommendations(report(catalog), task)
                self.assertEqual(result["recommended"]["model_id"], model)
                self.assertEqual(result["recommended"]["reasoning_effort"], "high")
                for candidate in result["candidates"]:
                    self.assertEqual("cursor_model_not_latest_high_fast" in candidate["reasons"],
                                     candidate["model_id"] != model)

    def test_newest_high_fast_in_the_catalog_is_the_only_cursor_route(self):
        self.assert_only(self.CATALOG, GROK)

    def test_a_new_version_takes_over_without_a_config_change(self):
        self.assert_only(self.CATALOG + ["grok-4.8-high-fast", "grok-4.9-low-fast"], "grok-4.8-high-fast")

    def test_pinned_model_still_needs_fresh_available_capacity(self):
        cases: tuple[tuple[dict, str], ...] = (({"used": 100}, "quota_exhausted"), ({"fresh": False}, "quota_stale"))
        for kwargs, reason in cases:
            with self.subTest(kwargs=kwargs), patch.object(routing, "_now", return_value=NOW):
                result = routing.recommendations(report([GROK], **kwargs), "tiny")
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
       ("cursor", [GROK]),
       ("claude", ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-1"])]


class TaskPreferenceTest(unittest.TestCase):
    def recommend(self, task, constrained=()):
        rows = [provider(name, models, used=95 if name in constrained else 10) for name, models in ALL]
        with patch.object(routing, "_now", return_value=NOW):
            chosen = routing.recommendations({"providers": rows}, task)["recommended"]
        return (chosen["provider"], chosen["family"]) if chosen else None

    def test_each_task_class_gets_its_preferred_route(self):
        # Code work stays on Claude; everything else goes to the other providers.
        expected = {"tiny": ("codex", "luna"), "routine": ("claude", "opus"),
                    "substantial": ("claude", "opus"), "review": ("codex", "sol"),
                    "research": ("codex", "sol"), "computer_use": ("codex", "sol"),
                    "aesthetic": ("claude", "fable")}
        self.assertEqual(set(expected), set(routing.TASKS))
        for task, route in expected.items():
            with self.subTest(task=task):
                self.assertEqual(self.recommend(task), route)

    def test_backups_take_over_when_the_preferred_pool_is_constrained(self):
        self.assertEqual(self.recommend("routine", constrained=("claude",)), ("codex", "terra"))
        self.assertEqual(self.recommend("substantial", constrained=("claude",)), ("codex", "sol"))
        self.assertEqual(self.recommend("aesthetic", constrained=("claude",)), ("codex", "astra"))
        self.assertEqual(self.recommend("review", constrained=("codex",)), ("claude", "opus"))
        self.assertEqual(self.recommend("research", constrained=("codex",)), ("cursor", "grok_fast"))
        self.assertEqual(self.recommend("tiny", constrained=("codex",)), ("cursor", "grok_fast"))

    def test_computer_use_only_goes_to_codex(self):
        self.assertIsNone(self.recommend("computer_use", constrained=("codex",)))

    def test_non_code_work_reaches_claude_only_as_a_fallback(self):
        for task in ("tiny", "review", "research", "computer_use"):
            with self.subTest(task=task):
                self.assertNotIn("claude", {name for name, _ in routing.TIERS[task][0]})

    def test_grok_fast_ranks_where_haiku_does_except_on_tiny_work(self):
        # The user rates Grok Fast as Haiku-class but wants Cursor used, so it
        # shares Codex's top tier for tiny work and spare capacity decides.
        for task, tiers in routing.TIERS.items():
            with self.subTest(task=task):
                grok = [i for i, tier in enumerate(tiers) if ("cursor", "grok_fast") in tier]
                haiku = [i for i, tier in enumerate(tiers) if ("claude", "haiku") in tier]
                if task == "tiny":
                    self.assertEqual(grok, [0])
                    self.assertIn(("codex", "luna"), tiers[0])
                    self.assertGreater(haiku[0], 0)
                else:
                    self.assertEqual(grok, haiku)

    def test_opus_precedes_sonnet_wherever_both_are_ranked(self):
        for task, order in routing.ORDERS.items():
            if ("claude", "sonnet") in order:
                with self.subTest(task=task):
                    self.assertLess(order.index(("claude", "opus")), order.index(("claude", "sonnet")))

    def test_every_ranked_route_sits_in_exactly_one_quality_tier(self):
        for task, tiers in routing.TIERS.items():
            with self.subTest(task=task):
                flat = [route for tier in tiers for route in tier]
                self.assertEqual(flat, routing.ORDERS[task])
                self.assertEqual(len(flat), len(set(flat)))

    def test_unknown_task_is_rejected(self):
        with self.assertRaises(ValueError):
            routing.recommendations({"providers": []}, "huge")


def paced(name, models, remaining, left, length):
    """A provider whose only window has `remaining`% left with `left` of a `length` window to go."""
    row = provider(name, models, used=100 - remaining)
    reset = (NOW + left).isoformat()
    minutes = length.total_seconds() / 60
    if name == "codex":
        row["quota"]["buckets"][0]["primary"].update(resets_at_utc=reset, window_minutes=minutes)
    else:
        row["quota"]["windows"][0].update(resets_at=reset, window_minutes=minutes)
    return row


WEEK, MONTH = timedelta(days=7), timedelta(days=30)


class SpareCapacityTest(unittest.TestCase):
    """Quality tiers come first; within a tier the allowance most likely to reset unused wins."""

    def recommend(self, task, rows):
        with patch.object(routing, "_now", return_value=NOW):
            result = routing.recommendations({"providers": rows}, task)
        return result, (result["recommended"]["provider"], result["recommended"]["family"])

    def test_underused_pool_wins_within_a_tier(self):
        # Codex is a little ahead of pace; Cursor has barely been touched this cycle.
        rows = [paced("codex", ["gpt-6-luna"], 36, timedelta(days=2), WEEK),
                paced("cursor", [GROK], 100, timedelta(days=20), MONTH)]
        result, route = self.recommend("tiny", rows)
        self.assertEqual(route, ("cursor", "grok_fast"))
        slack = {c["provider"]: c["slack_percent"] for c in result["candidates"]}
        self.assertAlmostEqual(slack["codex"], 36 - 100 * 2 / 7)
        self.assertAlmostEqual(slack["cursor"], 100 - 100 * 20 / 30)

    def test_pool_about_to_reset_with_allowance_left_wins(self):
        rows = [paced("codex", ["gpt-6-luna"], 90, timedelta(days=1), WEEK),
                paced("cursor", [GROK], 50, timedelta(days=25), MONTH)]
        self.assertEqual(self.recommend("tiny", rows)[1], ("codex", "luna"))

    def test_spare_capacity_never_lifts_a_lower_quality_tier(self):
        rows = [paced("codex", ["gpt-6.2-sol"], 20, timedelta(days=1), WEEK),
                paced("cursor", [GROK], 100, timedelta(days=1), MONTH)]
        self.assertEqual(self.recommend("research", rows)[1], ("codex", "sol"))
        rows = [paced("claude", ["claude-opus-5-5"], 20, timedelta(days=1), WEEK),
                paced("cursor", [GROK], 100, timedelta(days=1), MONTH)]
        self.assertEqual(self.recommend("routine", rows)[1], ("claude", "opus"))

    def test_unmeasured_higher_tier_still_outranks_measured_lower_tier(self):
        rows = [provider("claude", ["claude-opus-5-5"]), paced("cursor", [GROK], 100, timedelta(days=1), MONTH)]
        result, route = self.recommend("routine", rows)
        self.assertEqual(route, ("claude", "opus"))
        self.assertIsNone(result["recommended"]["slack_percent"])

    def test_inconsistent_window_length_gives_no_slack(self):
        # A reset further away than the window is long is bad data, not spare capacity.
        row = paced("codex", ["gpt-6.1-terra"], 100, timedelta(days=8), WEEK)
        result, _ = self.recommend("routine", [row])
        self.assertIsNone(result["recommended"]["slack_percent"])

    def test_the_tightest_window_decides_a_pools_slack(self):
        row = paced("codex", ["gpt-6.1-terra"], 90, timedelta(days=1), WEEK)
        row["quota"]["buckets"][0]["secondary"] = {"used_percent": 70, "remaining_percent": 30,
                                                    "resets_at_utc": (NOW + timedelta(days=6)).isoformat(),
                                                    "window_minutes": WEEK.total_seconds() / 60}
        result, _ = self.recommend("routine", [row])
        self.assertAlmostEqual(result["recommended"]["slack_percent"], 30 - 100 * 6 / 7)

    def test_measured_slack_ranks_first_then_listed_order(self):
        rows = [provider("codex", ["gpt-6-luna"]), paced("cursor", [GROK], 50, timedelta(days=6), WEEK)]
        result, route = self.recommend("tiny", rows)
        self.assertEqual(route, ("cursor", "grok_fast"))
        codex = next(c for c in result["candidates"] if c["provider"] == "codex")
        self.assertIsNone(codex["slack_percent"])
        rows = [provider("codex", ["gpt-6-luna"]), provider("cursor", [GROK])]
        self.assertEqual(self.recommend("tiny", rows)[1], ("codex", "luna"))


class UnverifiedPreferredRouteTest(unittest.TestCase):
    """Claude quota is often unmeasured; that must not silently drop code work a tier."""

    def run_routine(self, claude):
        rows = [claude, provider("cursor", [GROK])]
        with patch.object(routing, "_now", return_value=NOW):
            return routing.recommendations({"providers": rows}, "routine")

    def test_stale_higher_tier_route_is_surfaced_beside_the_verified_pick(self):
        claude = provider("claude", ["claude-opus-5-5"])
        claude["quota"]["observed_at"] = (NOW - timedelta(hours=20)).isoformat()
        result = self.run_routine(claude)
        self.assertEqual(result["recommended"]["provider"], "cursor")
        self.assertEqual(result["preferred_unverified"]["family"], "opus")
        self.assertIn("quota_stale", result["preferred_unverified"]["reasons"])

    def test_known_exhaustion_is_not_an_unverified_preference(self):
        result = self.run_routine(provider("claude", ["claude-opus-5-5"], used=100))
        self.assertEqual(result["recommended"]["provider"], "cursor")
        self.assertIsNone(result["preferred_unverified"])

    def test_stale_record_showing_exhaustion_is_not_an_unverified_preference(self):
        for used in (100, 90):
            with self.subTest(used=used):
                claude = provider("claude", ["claude-opus-5-5"], used=used)
                claude["quota"]["observed_at"] = (NOW - timedelta(hours=2)).isoformat()
                claude["quota"]["windows"][0]["status"] = "stale"
                result = self.run_routine(claude)
                self.assertEqual(result["recommended"]["provider"], "cursor")
                self.assertIsNone(result["preferred_unverified"])

    def test_stale_record_with_headroom_is_still_surfaced(self):
        claude = provider("claude", ["claude-opus-5-5"], used=40)
        claude["quota"]["observed_at"] = (NOW - timedelta(hours=2)).isoformat()
        claude["quota"]["windows"][0]["status"] = "stale"
        self.assertEqual(self.run_routine(claude)["preferred_unverified"]["family"], "opus")

    def test_claude_without_any_quota_data_is_surfaced(self):
        # What collect() reports before any cache or statusline record exists.
        claude = provider("claude", ["claude-opus-5-5"])
        claude["quota"] = {"status": "unknown", "observed_at": NOW.isoformat(), "windows": [],
                           "usage_account_matches_cli": False, "error": "native_usage_cache_unavailable"}
        result = self.run_routine(claude)
        self.assertEqual(result["recommended"]["provider"], "cursor")
        self.assertEqual(result["preferred_unverified"]["family"], "opus")
        self.assertIn("model_quota_missing", result["preferred_unverified"]["reasons"])

    def test_unknown_scope_window_is_still_surfaced(self):
        claude = provider("claude", ["claude-opus-5-5"])
        claude["quota"]["observed_at"] = (NOW - timedelta(hours=2)).isoformat()
        claude["quota"]["windows"].append({"name": "seven_day_oauth_apps", "scope": "oauth_apps_unknown_applicability",
                                           "status": "known", "used_percent": 10, "remaining_percent": 90,
                                           "resets_at": (NOW + timedelta(days=1)).isoformat()})
        result = self.run_routine(claude)
        self.assertEqual(result["preferred_unverified"]["family"], "opus")
        self.assertIn("quota_scope_applicability_unknown", result["preferred_unverified"]["reasons"])

    def test_mismatched_cursor_account_is_never_surfaced(self):
        cursor_row = provider("cursor", [GROK])
        cursor_row["quota"] = {"status": "unknown", "observed_at": NOW.isoformat(), "windows": [],
                               "usage_account_matches_cli": False, "reason": "usage_account_mismatch"}
        rows = [cursor_row, provider("claude", ["claude-sonnet-5-5"])]
        with patch.object(routing, "_now", return_value=NOW):
            result = routing.recommendations({"providers": rows}, "routine")
        self.assertEqual(result["recommended"]["family"], "sonnet")
        self.assertNotEqual(result["preferred_unverified"]["provider"], "cursor")
        grok = next(c for c in result["candidates"] if c["provider"] == "cursor")
        self.assertIn("usage_account_mismatch", grok["reasons"])

    def test_verified_pick_in_the_top_tier_needs_no_unverified_hint(self):
        result = self.run_routine(provider("claude", ["claude-opus-5-5"]))
        self.assertEqual(result["recommended"]["family"], "opus")
        self.assertIsNone(result["preferred_unverified"])


CURSOR_SPEC = importlib.util.spec_from_file_location("capacity_cursor", ROOT / "dot_local/lib/agent_capacity/cursor.py")
assert CURSOR_SPEC is not None and CURSOR_SPEC.loader is not None
cursor = importlib.util.module_from_spec(CURSOR_SPEC)
CURSOR_SPEC.loader.exec_module(cursor)


class CursorWindowLengthTest(unittest.TestCase):
    def test_billing_cycle_gives_each_pool_its_window_length(self):
        now = datetime.now(timezone.utc)
        summary = {"billingCycleStart": (now - timedelta(days=10)).isoformat(),
                   "billingCycleEnd": (now + timedelta(days=20)).isoformat(),
                   "individualUsage": {"plan": {"enabled": True, "autoPercentUsed": 5, "apiPercentUsed": 0}}}
        windows = cursor.normalize(summary, "fixture")["windows"]
        self.assertEqual([w["window_minutes"] for w in windows], [30 * 24 * 60] * 2)

    def test_missing_cycle_start_leaves_length_unknown(self):
        now = datetime.now(timezone.utc)
        summary = {"billingCycleEnd": (now + timedelta(days=20)).isoformat(),
                   "individualUsage": {"plan": {"enabled": True, "autoPercentUsed": 5}}}
        self.assertEqual({w["window_minutes"] for w in cursor.normalize(summary, "fixture")["windows"]}, {None})


if __name__ == "__main__":
    unittest.main()
