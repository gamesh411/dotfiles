"""Prompt-free Claude quota via the native get_usage control request.

Claude owns credentials and refresh. This module never reads Keychain items,
credential files, browser cookies, or tokens, and never sends a model prompt.
Native responses may silently contain last-known usage. An account-bound native
cache timestamp must prove freshness before quota can qualify for routing.
"""
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time

MAX_RESPONSE_BYTES = 4 * 1024 * 1024
FRESH_SECONDS = 60
VERIFIED_VERSIONS = {(2, 1, 286)}


class ProbeError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat().replace("+00:00", "Z")


def _number(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def _percent(value):
    value = _number(value)
    return value if value is not None and 0 <= value <= 100 else None


def _reset(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo is not None else None
    except (ValueError, OverflowError, OSError):
        return None


def _model(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9 ._\[\]-]{1,128}", value) else None


def normalize_usage(payload, observed_at=None, source="native_control_usage", now=None):
    """Keep quota windows only, including null measurements as unknown.

    is_active means headline selection in Claude's wire schema. It does not
    establish whether the limit constrains a model. Both shared windows apply.
    """
    now = time.time() if now is None else now
    observed_at = now if observed_at is None else observed_at
    age = now - observed_at
    fresh = 0 <= age <= FRESH_SECONDS
    windows = []

    def add(name, raw, duration, scope, usage_key="utilization", model_id=None):
        raw = raw if isinstance(raw, dict) else {}
        used, reset = _percent(raw.get(usage_key)), _reset(raw.get("resets_at"))
        status = "known" if used is not None else "unknown"
        if status == "known" and not fresh:
            status = "stale"
        if used is not None and reset is not None and reset <= now:
            status = "expired"
        windows.append({"name": name, "window_minutes": duration, "scope": scope,
                        "model_id": model_id, "used_percent": used,
                        "remaining_percent": 100 - used if used is not None else None,
                        "resets_at": _iso(reset) if reset is not None else None,
                        "status": status})

    limits = payload.get("limits")
    limits = limits if isinstance(limits, list) else []
    for name, kind, minutes in (("five_hour", "session", 300), ("seven_day", "weekly_all", 10080)):
        raw = payload.get(name)
        if not isinstance(raw, dict):
            # Newer server rows can supply a main window when flat fields do not.
            rows = [row for row in limits if isinstance(row, dict) and row.get("kind") == kind]
            if len(rows) == 1:
                add(name, rows[0], minutes, "all_models", "percent")
                continue
        add(name, raw, minutes, "all_models")

    for name, scope in (("seven_day_opus", "opus"), ("seven_day_sonnet", "sonnet"),
                        ("seven_day_oauth_apps", "oauth_apps_unknown_applicability")):
        if isinstance(payload.get(name), dict):
            add(name, payload[name], 10080, scope)

    scoped = []
    for index, entry in enumerate(limits[:100]):
        if not isinstance(entry, dict) or entry.get("kind") != "weekly_scoped":
            continue
        scope = entry.get("scope")
        model = scope.get("model") if isinstance(scope, dict) else None
        model = model if isinstance(model, dict) else {}
        model_id, label = _model(model.get("id")), _model(model.get("display_name"))
        family = label.lower() if label and label.lower() in ("haiku", "sonnet", "opus") else label or "unknown_model"
        add("weekly_scoped_" + str(index), entry, 10080, family, "percent", model_id)
        scoped.append((label, _percent(entry.get("percent")), _reset(entry.get("resets_at"))))
    # Native get_usage can project scoped rows without the raw limits[] on a
    # seeded reply. Include them for display; cache freshness still gates routing.
    projected = payload.get("model_scoped")
    if isinstance(projected, list):
        for index, entry in enumerate(projected[:100]):
            if not isinstance(entry, dict):
                continue
            label = _model(entry.get("display_name"))
            signature = (label, _percent(entry.get("utilization")), _reset(entry.get("resets_at")))
            if signature in scoped:
                continue
            scope = label.lower() if label and label.lower() in ("haiku", "sonnet", "opus") else label or "unknown_model"
            add("model_scoped_" + str(index), entry, 10080, scope)
    known = any(window["status"] == "known" for window in windows)
    measured = any(window["used_percent"] is not None for window in windows)
    return {"provider": "claude", "quota_status": "known" if known else "stale" if measured and not fresh else "unknown",
            "quota_source": source, "observed_at": _iso(observed_at),
            "age_seconds": round(age, 3), "freshness": "fresh" if fresh else "future" if age < 0 else "stale",
            "windows": windows}


def read_native_snapshot():
    """Read only the native cache and compare account IDs inside this process."""
    config_dir = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    preferred = config_dir / ".config.json"
    fallback = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home()) / ".claude.json"
    path = preferred if preferred.exists() else fallback
    try:
        if path.stat().st_size > MAX_RESPONSE_BYTES:
            return None
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    cache, account = data.get("cachedUsageUtilization"), data.get("oauthAccount")
    if not isinstance(cache, dict) or not isinstance(account, dict):
        return None
    cache_id, cli_id = cache.get("accountUuid"), account.get("accountUuid")
    matches = isinstance(cache_id, str) and bool(cache_id) and cache_id == cli_id
    observed_ms = _number(cache.get("fetchedAtMs"))
    payload = cache.get("utilization")
    if not matches or observed_ms is None or observed_ms <= 0 or not isinstance(payload, dict):
        return None
    return {"payload": payload, "observed_at": observed_ms / 1000, "account": cache_id}


def _capture(argv, deadline, input_text=None, environment=None):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ProbeError("native_usage_timeout")
    try:
        process = subprocess.Popen(argv, stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   env=environment, start_new_session=os.name == "posix")
    except OSError:
        raise ProbeError("native_cli_unavailable") from None
    try:
        stdout, _ = process.communicate(input_text, timeout=max(0.001, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            process.kill()
        process.communicate()
        raise ProbeError("native_usage_timeout") from None
    if len(stdout.encode()) > MAX_RESPONSE_BYTES:
        raise ProbeError("native_usage_response_too_large")
    if process.returncode != 0:
        raise ProbeError("native_usage_failed")
    return stdout


def request_native_usage(binary, deadline):
    """Control input only. Unsupported requests fail without model inference."""
    environment = dict(os.environ)
    # Disabling all nonessential traffic also disables quota refresh in this
    # installed client. Respect that caller setting, but do not set it ourselves.
    environment.update(DISABLE_TELEMETRY="1", DISABLE_ERROR_REPORTING="1", DISABLE_AUTOUPDATER="1")
    argv = [binary, "--safe-mode", "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
            "--permission-mode", "dontAsk", "--permission-prompts", "none", "--no-session-persistence",
            "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", "--print"]
    request = {"type": "control_request", "request_id": "agent-capacity-quota",
               "request": {"subtype": "get_usage", "skip_behaviors": True}}
    output = _capture(argv, deadline, json.dumps(request) + "\n", environment)
    replies = []
    for line in output.splitlines():
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if not isinstance(message, dict):
            continue
        if message.get("type") == "result" and (message.get("num_turns", 0) != 0 or message.get("total_cost_usd", 0) != 0):
            raise ProbeError("native_usage_unexpected_model_activity")
        if message.get("type") != "control_response":
            continue
        outer = message.get("response")
        if not isinstance(outer, dict) or outer.get("request_id") != request["request_id"]:
            continue
        if outer.get("subtype") != "success":
            raise ProbeError("native_usage_control_unsupported")
        response = outer.get("response")
        if isinstance(response, dict):
            replies.append(response)
    if len(replies) != 1:
        raise ProbeError("native_usage_response_invalid")
    reply = replies[0]
    session = reply.get("session")
    if not isinstance(session, dict) or _number(session.get("total_cost_usd")) != 0:
        raise ProbeError("native_usage_zero_cost_unverified")
    if reply.get("rate_limits_available") is not True:
        raise ProbeError("native_usage_not_subscription_limits")
    payload = reply.get("rate_limits")
    if not isinstance(payload, dict):
        raise ProbeError("native_usage_limits_unavailable")
    return payload


def _signature(result):
    return sorted((w["name"], w["used_percent"], w["resets_at"], w["model_id"], w["scope"]) for w in result["windows"])


def _snapshot_result(snapshot, error=None):
    result = normalize_usage(snapshot["payload"], snapshot["observed_at"], "native_usage_cache")
    result["usage_account_matches_cli"] = True
    if error:
        result["error"] = error
    return result


def collect(timeout=15, binary="claude"):
    """Return sanitized quota, or honest stale/unknown data with a stable reason."""
    now = time.time()
    unknown = {"provider": "claude", "quota_status": "unknown", "quota_source": None,
               "observed_at": _iso(now), "windows": [], "usage_account_matches_cli": False}
    try:
        if _number(timeout) is None or not 0 < timeout <= 60:
            raise ProbeError("invalid_timeout")
        if any(os.environ.get(key) for key in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
                  "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")):
            raise ProbeError("native_auth_override_unsupported")
        if os.environ.get("ANTHROPIC_BASE_URL") not in (None, "", "https://api.anthropic.com"):
            raise ProbeError("native_provider_override_unsupported")
        deadline = time.monotonic() + timeout
        version_text = _capture([binary, "--version"], deadline)
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+) \(Claude Code\)\s*", version_text)
        if not match or tuple(map(int, match.groups())) not in VERIFIED_VERSIONS:
            raise ProbeError("native_usage_interface_unverified")
        before = read_native_snapshot()
        if before and 0 <= now - before["observed_at"] <= FRESH_SECONDS:
            return _snapshot_result(before)
        try:
            payload = request_native_usage(binary, deadline)
        except ProbeError as exc:
            after = read_native_snapshot()
            return _snapshot_result(after, exc.code) if after else {**unknown, "error": exc.code}
        after = read_native_snapshot()
        if not after:
            raise ProbeError("native_usage_provenance_unavailable")
        cache_result = _snapshot_result(after)
        reply_result = normalize_usage(payload, after["observed_at"], "native_control_usage")
        # Cached and live replies must refer to the same measured windows. Native
        # model_scoped is a duplicate projection, so compare shared windows here.
        cache_common = [w for w in cache_result["windows"] if w["scope"] == "all_models"]
        reply_common = [w for w in reply_result["windows"] if w["scope"] == "all_models"]
        if _signature({"windows": cache_common}) != _signature({"windows": reply_common}):
            raise ProbeError("native_usage_cache_response_mismatch")
        if before and before["account"] != after["account"]:
            raise ProbeError("native_usage_account_changed_during_probe")
        if reply_result["quota_status"] != "known":
            return _snapshot_result(after, "native_usage_refresh_unverified")
        # The native cache preserves the complete server scoped inventory; the
        # control reply can hide some projected model rows behind an allowlist.
        cache_result["quota_source"] = "native_control_usage"
        cache_result["native_model_requests"] = 0
        return cache_result
    except ProbeError as exc:
        return {**unknown, "error": exc.code}
    except Exception:
        # Never include native stdout, identity, raw errors, or tracebacks.
        return {**unknown, "error": "native_usage_probe_failure"}
