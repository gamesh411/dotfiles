"""Prompt-free Claude quota from Claude's native account-bound usage cache.

Claude owns credentials and refresh. This module never reads Keychain items,
credential files, browser cookies, or tokens, never launches the CLI, and never
sends a model prompt. An account-bound native cache timestamp must prove
freshness before quota can qualify for routing; a stale or absent cache is
reported as stale or unknown rather than refreshed here.

Claude Code rewrites that cache only when /usage opens, on a once-a-day check,
or on an SDK get_usage request, so it is usually hours old. Its statusline,
though, receives the five-hour and seven-day windows from every API response.
The statusline command records them here, and a newer record overrides the
cache's shared windows while model-scoped windows still come from the cache.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time

MAX_RESPONSE_BYTES = 4 * 1024 * 1024
FRESH_SECONDS = 600
CLAUDE_FAMILIES = ("haiku", "sonnet", "opus", "fable")


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


def normalize_usage(payload, observed_at=None, now=None):
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
        family = label.lower() if label and label.lower() in CLAUDE_FAMILIES else label or "unknown_model"
        add("weekly_scoped_" + str(index), entry, 10080, family, "percent", model_id)
        scoped.append((label, _percent(entry.get("percent")), _reset(entry.get("resets_at"))))
    # The cached payload can carry scoped rows without the raw limits[]. Include
    # them for display; cache freshness still gates routing.
    projected = payload.get("model_scoped")
    if isinstance(projected, list):
        for index, entry in enumerate(projected[:100]):
            if not isinstance(entry, dict):
                continue
            label = _model(entry.get("display_name"))
            signature = (label, _percent(entry.get("utilization")), _reset(entry.get("resets_at")))
            if signature in scoped:
                continue
            scope = label.lower() if label and label.lower() in CLAUDE_FAMILIES else label or "unknown_model"
            add("model_scoped_" + str(index), entry, 10080, scope)
    known = any(window["status"] == "known" for window in windows)
    measured = any(window["used_percent"] is not None for window in windows)
    return {"provider": "claude", "quota_status": "known" if known else "stale" if measured and not fresh else "unknown",
            "quota_source": "native_usage_cache", "observed_at": _iso(observed_at),
            "age_seconds": round(age, 3), "freshness": "fresh" if fresh else "future" if age < 0 else "stale",
            "windows": windows}


def _read_config():
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
    return data if isinstance(data, dict) else None


def _account_digest(data):
    """A one-way account tag, so the statusline record never stores the raw ID."""
    account = data.get("oauthAccount") if isinstance(data, dict) else None
    uuid = account.get("accountUuid") if isinstance(account, dict) else None
    return hashlib.sha256(uuid.encode()).hexdigest() if isinstance(uuid, str) and uuid else None


def read_native_snapshot():
    """Read only the native cache and compare account IDs inside this process."""
    data = _read_config()
    if data is None:
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
    return {"payload": payload, "observed_at": observed_ms / 1000}


STATUSLINE_WINDOWS = (("five_hour", 300), ("seven_day", 10080))


def statusline_path():
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "agent-capacity" / "claude-statusline.json"


def _read_statusline_record(digest):
    try:
        record = json.loads(statusline_path().read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(record, dict) or digest is None or record.get("account") != digest:
        return None
    observed, windows = _number(record.get("observed_at")), record.get("windows")
    if observed is None or not isinstance(windows, dict):
        return None
    return {"observed_at": observed, "windows": windows}


def record_statusline(payload, now=None):
    """Persist the rate limits Claude Code hands its statusline; True when written.

    The transcript's last write stands in for when those limits were observed,
    because a statusline also reruns on idle triggers such as a mode change.
    """
    now = time.time() if now is None else now
    try:
        limits = payload.get("rate_limits") if isinstance(payload, dict) else None
        transcript = payload.get("transcript_path") if isinstance(payload, dict) else None
        if not isinstance(limits, dict) or not isinstance(transcript, str):
            return False
        windows = {}
        for name, _ in STATUSLINE_WINDOWS:
            raw = limits.get(name)
            raw = raw if isinstance(raw, dict) else {}
            used, reset = _percent(raw.get("used_percentage")), _number(raw.get("resets_at"))
            if used is not None and reset is not None:
                windows[name] = {"used_percent": used, "resets_at": reset}
        digest = _account_digest(_read_config())
        if not windows or digest is None:
            return False
        observed = min(Path(transcript).stat().st_mtime, now)
        existing = _read_statusline_record(digest)
        if existing and existing["observed_at"] > observed:
            return False
        path = statusline_path()
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Concurrent sessions each write; a rename keeps every reader on a whole file.
        temporary = path.with_name(path.name + "." + str(os.getpid()) + ".tmp")
        handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(handle, "w") as stream:
            json.dump({"schema": 1, "account": digest, "observed_at": observed, "windows": windows}, stream)
        os.replace(temporary, path)
        return True
    except (OSError, ValueError, TypeError):
        return False


def _with_statusline(base, record, now):
    age = now - record["observed_at"]
    fresh = 0 <= age <= FRESH_SECONDS
    windows = []
    for name, minutes in STATUSLINE_WINDOWS:
        raw = record["windows"].get(name)
        used = _percent(raw.get("used_percent")) if isinstance(raw, dict) else None
        reset = _number(raw.get("resets_at")) if isinstance(raw, dict) else None
        if used is None or reset is None:
            continue
        status = "expired" if reset <= now else "known" if fresh else "stale"
        windows.append({"name": name, "window_minutes": minutes, "scope": "all_models", "model_id": None,
                        "used_percent": used, "remaining_percent": 100 - used,
                        "resets_at": _iso(reset), "status": status})
    replaced = {window["name"] for window in windows}
    windows += [window for window in (base or {}).get("windows", []) if window["name"] not in replaced]
    known = any(window["status"] == "known" for window in windows)
    measured = any(window["used_percent"] is not None for window in windows)
    return {"provider": "claude", "quota_status": "known" if known else "stale" if measured and not fresh else "unknown",
            "quota_source": "statusline_rate_limits" + ("+native_usage_cache" if base else ""),
            "observed_at": _iso(record["observed_at"]), "age_seconds": round(age, 3),
            "freshness": "fresh" if fresh else "future" if age < 0 else "stale", "windows": windows}


def collect():
    """Return cached native quota, or stale/unknown data with a stable reason."""
    now = time.time()
    unknown = {"provider": "claude", "quota_status": "unknown", "quota_source": None,
               "observed_at": _iso(now), "windows": [], "usage_account_matches_cli": False}
    try:
        if any(os.environ.get(key) for key in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
                  "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")):
            raise ProbeError("native_auth_override_unsupported")
        if os.environ.get("ANTHROPIC_BASE_URL") not in (None, "", "https://api.anthropic.com"):
            raise ProbeError("native_provider_override_unsupported")
        snapshot = read_native_snapshot()
        record = _read_statusline_record(_account_digest(_read_config()))
        native = normalize_usage(snapshot["payload"], snapshot["observed_at"], now) if snapshot else None
        if record and (snapshot is None or record["observed_at"] > snapshot["observed_at"]):
            result = _with_statusline(native, record, now)
        elif native is not None:
            result = native
        else:
            raise ProbeError("native_usage_cache_unavailable")
        result["usage_account_matches_cli"] = True
        return result
    except ProbeError as exc:
        return {**unknown, "error": exc.code}
    except Exception:
        # Never include cache contents, identity, raw errors, or tracebacks.
        return {**unknown, "error": "native_usage_probe_failure"}
