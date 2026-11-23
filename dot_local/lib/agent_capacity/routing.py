"""Conservative, read-only model recommendations from quota observations.

The reserve is a local routing heuristic, not a provider guarantee. Percentages
from different pools are never treated as interchangeable token budgets; pools
are compared only by how far each is ahead of its own even spending pace.
"""

from datetime import datetime, timezone
import math
import re


def _now():
    return datetime.now(timezone.utc)


def _time(value):
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo is not None else None
        except ValueError:
            return None
    if type(value) in (int, float) and math.isfinite(value):
        try:
            return datetime.fromtimestamp(value, timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None
    return None


def _percent(value):
    return value if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 100 else None


def _freshness(observed, now, max_age):
    at = _time(observed)
    if at is None:
        return "unknown"
    age = (now - at).total_seconds()
    return "fresh" if 0 <= age <= max_age else "future" if age < 0 else "stale"


def _natural(value):
    return tuple(int(x) if x.isdigit() else x for x in re.split(r"(\d+)", value))


def _model_version(value):
    match = re.search(r"(?:gpt-|grok-)(\d+(?:\.\d+)*)-", value)
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def _cursor_effort(model_id):
    match = re.fullmatch(r"(?:cursor-)?grok-\d+(?:\.\d+)*-(low|medium|high|xhigh)-fast", model_id)
    return match.group(1) if match else None


def _auth_failure(provider):
    auth = provider.get("auth", {})
    if auth.get("status") in ("unauthenticated", "failed", "unavailable", "error"):
        return True
    if auth.get("network_access_verified") is False:
        return True
    if provider.get("status") == "unavailable":
        return True
    failures = {"unauthorized", "forbidden", "usage_unauthorized", "usage_forbidden", "access_denied",
                "authentication_failed", "credentials_expired_native_refresh_required"}
    for error in provider.get("errors", []):
        if not isinstance(error, dict):
            continue
        if error.get("code") in failures or error.get("http_status") in (401, 403):
            return True
        if error.get("operation") == "auth" and error.get("code") not in ("command_not_advertised",):
            return True
    quota = provider.get("quota", {})
    return quota.get("error") in failures or quota.get("reason") in failures or quota.get("http_status") in (401, 403)


def _window(raw, scope, name=None, codex=False, individual=False):
    used = _percent(raw.get("used_percent"))
    remaining = _percent(raw.get("remaining_percent"))
    reset = raw.get("resets_at_utc", raw.get("resets_at_epoch")) if codex else raw.get("resets_at")
    valid = remaining is not None and (individual or used is not None)
    if used is not None and remaining is not None and abs(used + remaining - 100) > 0.00001:
        valid = False
    minutes = raw.get("window_minutes")
    return {"scope": scope, "name": name or raw.get("name"), "used_percent": used,
            "remaining_percent": remaining if valid else None, "resets_at": reset,
            "window_minutes": minutes if type(minutes) in (int, float) and math.isfinite(minutes) and minutes > 0 else None,
            "status": "known" if valid and (codex or raw.get("status") == "known") else "unknown"}


def _slack(window, reset, now):
    """Percentage points of allowance above an even pace to the reset; positive means unused headroom."""
    if window["window_minutes"] is None:
        return None
    left = (reset - now).total_seconds() / 60 / window["window_minutes"]
    # A reset further away than the window is long is inconsistent data, not headroom.
    return window["remaining_percent"] - 100 * left if 0 <= left <= 1 else None


def _codex_windows(provider, entry):
    quota = provider.get("quota", {})
    buckets = quota.get("buckets", [])
    model_names = {entry["id"], entry.get("model", entry["id"])}
    common, specific, ambiguity = [], [], False
    for bucket in buckets:
        if not isinstance(bucket, dict):
            ambiguity = True
            continue
        limit_id, slug = bucket.get("limit_id"), bucket.get("normal_model_slug")
        if limit_id == "codex" and slug is None:
            common.append(bucket)
        elif slug in model_names:
            specific.append(bucket)
        elif slug is None or limit_id == "codex":
            # An unidentified pool could constrain this model. Do not guess.
            ambiguity = True
    if len(common) > 1 or len(specific) > 1:
        ambiguity = True
    applicable = common + specific
    reasons = ["ambiguous_model_limits"] if ambiguity else []
    windows = []
    for bucket in applicable:
        scope = "all_models" if bucket in common else "model:" + entry["id"]
        if bucket.get("spend_control_reached") is True:
            reasons.append("spend_control_reached")
        present = False
        for key in ("primary", "secondary"):
            raw = bucket.get(key)
            if isinstance(raw, dict):
                windows.append(_window(raw, scope, key, codex=True))
                present = True
        raw = bucket.get("individual_limit")
        if isinstance(raw, dict):
            windows.append(_window(raw, scope, "individual_limit", codex=True, individual=True))
            present = True
        if not present:
            reasons.append("included_quota_missing")
    if not applicable:
        reasons.append("model_quota_missing")
    return windows, reasons


def _scoped_windows(provider, entry, family):
    quota = provider.get("quota", {})
    windows, reasons = [], []
    model_names = {entry["id"], entry.get("model", entry["id"])}
    for raw in quota.get("windows", []):
        if not isinstance(raw, dict):
            continue
        scope = raw.get("scope")
        if provider["provider"] == "cursor":
            applies = scope == "cursor_models" if family == "grok_fast" else False
        else:
            model_id = raw.get("model_id")
            # A machine model ID takes precedence over a display label.
            if model_id is not None:
                applies = model_id in model_names
            else:
                applies = scope in ("all_models", family) or scope in model_names or scope == "model:" + entry["id"]
            if scope in ("unknown_model", "oauth_apps_unknown_applicability"):
                reasons.append("quota_scope_applicability_unknown")
        if applies:
            windows.append(_window(raw, scope))
    if not windows:
        reasons.append("model_quota_missing")
    return windows, reasons


def _entries(provider):
    entries = provider.get("models", {}).get("entries", [])
    return [row for row in entries if isinstance(row, dict) and isinstance(row.get("id"), str)
            and row.get("hidden") is not True]


# The user's routing preference per task class, as quality tiers, best first.
# Quality comes first, so a lower tier is used only when no route above it
# qualifies. The user also wants every subscription used, so within a tier the
# pool furthest ahead of its spending pace wins; listed order breaks ties.
# Code work (routine, substantial, aesthetic) prefers Claude Opus and Fable;
# everything else goes to the other providers, and computer use only to Codex.
# The user rates Cursor Grok Fast as Haiku-class, so it ranks where Haiku does,
# except on tiny work, where it shares Codex's top tier so the Cursor
# subscription is not starved. Sonnet trails every tier that holds Opus.
TIERS = {
    "tiny": [[("codex", "luna"), ("codex", "terra"), ("cursor", "grok_fast")], [("claude", "haiku")]],
    "routine": [[("claude", "opus"), ("claude", "fable")],
                [("codex", "terra")],
                [("codex", "luna")],
                [("cursor", "grok_fast"), ("claude", "haiku")],
                [("claude", "sonnet")]],
    "substantial": [[("claude", "opus"), ("claude", "fable")], [("codex", "sol")], [("claude", "sonnet")]],
    "review": [[("codex", "sol")], [("claude", "opus")], [("claude", "sonnet")]],
    "research": [[("codex", "sol")], [("codex", "terra")], [("cursor", "grok_fast"), ("claude", "haiku")]],
    "computer_use": [[("codex", "sol")], [("codex", "terra")]],
    "aesthetic": [[("claude", "fable")], [("codex", "astra")]],
}
# Cursor work uses the newest Grok version the catalog offers at high effort
# with Fast serving, so a new release takes over without a config change.
# Other Grok Fast entries stay visible as candidates but never qualify.
CURSOR_EFFORT = "high"
# Reasons that only mean the route could not be measured. Claude quota often
# reads stale, and silently dropping a tier for that would trade away quality.
UNMEASURED = frozenset({"quota_unknown", "quota_stale", "quota_window_unknown", "quota_window_expired",
                        "quota_reset_unknown", "model_availability_unverified", "usage_account_unverified",
                        "model_catalog_unknown", "model_catalog_stale", "model_quota_missing",
                        "quota_scope_applicability_unknown"})
ORDERS = {task: [route for tier in tiers for route in tier] for task, tiers in TIERS.items()}
TASKS = tuple(ORDERS)
CLAUDE_FAMILIES = ("haiku", "sonnet", "opus", "fable")


def _rank(task, provider, family):
    try:
        return ORDERS[task].index((provider, family))
    except ValueError:
        return None


def _tier(task, provider, family):
    return next((i for i, tier in enumerate(TIERS[task]) if (provider, family) in tier), None)


def _candidates(provider):
    name = provider.get("provider")
    entries = _entries(provider)
    if name == "codex":
        for entry in entries:
            match = re.fullmatch(r"gpt-\d+(?:\.\d+)*-(luna|terra|sol|astra)", entry["id"])
            if match:
                yield entry, match.group(1), True
    elif name == "cursor":
        for entry in entries:
            if re.fullmatch(r"(?:cursor-)?grok-\d+(?:\.\d+)*-(?:[a-z]+-)*fast", entry["id"]):
                yield entry, "grok_fast", True
            elif entry["id"] in ("auto", "router"):
                yield entry, "router", True
    elif name == "claude":
        found = set()
        for entry in entries:
            match = re.search(r"(?:^|-)(" + "|".join(CLAUDE_FAMILIES) + r")(?:-|$)", entry["id"])
            if match:
                found.add(match.group(1))
                yield entry, match.group(1), True
        for family in CLAUDE_FAMILIES:
            if family not in found:
                yield {"id": family, "model": family}, family, False


def recommendations(report, task, reserve_percent=15, max_age_seconds=600):
    """Return reviewable candidates and one qualified recommendation, never launch.

    The task class is an explicit caller choice. Stale/unknown quota cannot
    qualify, even when authentication, catalog entries or credits are present.
    """
    if task not in TASKS:
        raise ValueError("task must be one of " + ", ".join(TASKS))
    if _percent(reserve_percent) is None:
        raise ValueError("reserve_percent must be between 0 and 100")
    if type(max_age_seconds) not in (int, float) or not math.isfinite(max_age_seconds) or max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive")
    now, candidates = _now(), []
    for provider in report.get("providers", []):
        if not isinstance(provider, dict) or provider.get("provider") not in ("codex", "cursor", "claude"):
            continue
        name, quota = provider["provider"], provider.get("quota", {})
        observed = quota.get("observed_at", provider.get("checked_at") if name == "codex" else None)
        freshness = _freshness(observed, now, max_age_seconds)
        catalog_fresh = _freshness(provider.get("models", {}).get("observed_at", provider.get("checked_at")), now, max_age_seconds)
        latest_grok = max((_model_version(entry["id"]) for entry, family, _ in _candidates(provider)
                           if family == "grok_fast" and _cursor_effort(entry["id"]) == CURSOR_EFFORT), default=None)
        for entry, family, advertised in _candidates(provider):
            reasons = []
            rank = _rank(task, name, family)
            effort = _cursor_effort(entry["id"]) if family == "grok_fast" else "low" if task == "tiny" else "medium"
            if family == "grok_fast" and effort is None:
                reasons.append("encoded_reasoning_effort_unverified")
            if family == "grok_fast" and (effort != CURSOR_EFFORT or _model_version(entry["id"]) != latest_grok):
                reasons.append("cursor_model_not_latest_high_fast")
            if rank is None:
                reasons.append("unsuitable_task_class")
            if _auth_failure(provider):
                reasons.append("authentication_unavailable")
            if not advertised or provider.get("models", {}).get("status") != "ok":
                reasons.append("model_availability_unverified")
            if provider.get("models", {}).get("inference_access_verified") is False:
                reasons.append("model_access_unavailable")
            if catalog_fresh != "fresh":
                reasons.append("model_catalog_" + catalog_fresh)
            if quota.get("status") != "ok":
                reasons.append("quota_unknown")
            if freshness != "fresh":
                reasons.append("quota_" + freshness)
            if quota.get("ordinary_usage_allowed") is False:
                reasons.append("ordinary_usage_disallowed")
            if name != "codex" and quota.get("usage_account_matches_cli") is not True:
                reasons.append("usage_account_unverified")
            if name == "cursor" and quota.get("usage_account_matches_cli") is False:
                reasons.append("usage_account_mismatch")
            if family == "router":
                windows, mapping_reasons = [], ["quota_scope_applicability_unknown"]
            elif name == "codex":
                windows, mapping_reasons = _codex_windows(provider, entry)
            else:
                windows, mapping_reasons = _scoped_windows(provider, entry, family)
            reasons.extend(mapping_reasons)
            valid_remaining, slacks = [], []
            for window in windows:
                reset = _time(window["resets_at"])
                if window["status"] != "known" or window["remaining_percent"] is None:
                    reasons.append("quota_window_unknown")
                    if (window["remaining_percent"] is not None and reset is not None and reset > now
                            and window["remaining_percent"] <= reserve_percent):
                        reasons.append("last_known_quota_constrained")
                elif reset is None:
                    window["status"] = "unknown"
                    reasons.append("quota_reset_unknown")
                elif reset <= now:
                    window["status"] = "expired"
                    reasons.append("quota_window_expired")
                else:
                    valid_remaining.append(window["remaining_percent"])
                    slacks.append(_slack(window, reset, now))
            remaining = min(valid_remaining) if valid_remaining and len(valid_remaining) == len(windows) else None
            slack = min(slacks) if remaining is not None and None not in slacks else None
            if remaining is not None:
                if remaining == 0:
                    reasons.append("quota_exhausted")
                elif remaining <= reserve_percent:
                    reasons.append("below_local_reserve")
            availability = "unavailable" if "authentication_unavailable" in reasons else "advertised" if advertised else "unverified"
            candidate = {"provider": name, "model_id": entry["id"], "family": family,
                         "preference_rank": rank, "quality_tier": _tier(task, name, family),
                         "availability": availability, "freshness": freshness,
                         "observed_at": observed, "quota_source": quota.get("source"),
                         "remaining_percent": remaining, "slack_percent": slack,
                         "scopes": sorted({w["scope"] for w in windows}),
                         "windows": windows, "reasons": sorted(set(reasons)), "eligible": not reasons,
                         "service_tier": "default" if name == "codex" else None,
                         "reasoning_effort": effort}
            candidates.append(candidate)
    # Quality tier first, then unused headroom against each pool's own pace,
    # then listed preference and latest version. Raw percentages are never
    # compared across providers; slack is relative to each pool's own window.
    candidates.sort(key=lambda c: _natural(c["model_id"]), reverse=True)
    candidates.sort(key=lambda c: _model_version(c["model_id"]), reverse=True)
    candidates.sort(key=lambda c: (c["quality_tier"] is None,
                                    c["quality_tier"] if c["quality_tier"] is not None else 999,
                                    c["slack_percent"] is None,
                                    -c["slack_percent"] if c["slack_percent"] is not None else 0,
                                    c["preference_rank"] if c["preference_rank"] is not None else 999))
    chosen = next((c for c in candidates if c["eligible"]), None)
    ceiling = chosen["quality_tier"] if chosen else math.inf
    unverified = next((c for c in candidates if not c["eligible"] and c["quality_tier"] is not None
                       and c["quality_tier"] < ceiling and set(c["reasons"]) <= UNMEASURED), None)
    return {"task": task, "reserve_percent": reserve_percent, "max_age_seconds": max_age_seconds,
            "candidates": candidates, "recommended": chosen, "preferred_unverified": unverified,
            "policy": {"execution": "manual", "lead_retains_judgment": True,
                       "reserve_basis": "local heuristic; requires remaining above reserve",
                       "unknown_fallback": "manual bounded work only; never an automatic recommendation",
                       "cross_provider_percentages": "separate pools, not equally priced tokens",
                       "spare_capacity": "within one quality tier, prefer the pool furthest ahead of its own even pace"}}
