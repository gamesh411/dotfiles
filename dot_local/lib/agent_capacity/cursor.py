#!/usr/bin/env python3
"""Prompt-free Cursor allowance probe. Native session only, no credential output."""
import base64
import datetime as dt
import email.utils
import http.client
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import ssl
import sys
import time

ENDPOINT = "https://cursor.com/api/usage-summary"


class ProbeError(Exception):
    def __init__(self, reason, retry_after_seconds=None):
        super().__init__(reason)
        self.retry_after_seconds = retry_after_seconds


def auth_override_present():
    # A native personal session does not measure any of these alternate routes.
    return any(os.environ.get(key) for key in (
        "CURSOR_API_KEY", "CURSOR_AUTH_TOKEN", "CURSOR_API_ENDPOINT",
        "CURSOR_API_URL", "CURSOR_WEBSITE_URL", "CURSOR_LOCAL_AGENT_BASE_URL",
        "CURSOR_LOCAL_AGENT_API_KEY", "CURSOR_ENABLE_BEDROCK", "CURSOR_ENABLE_LOCAL_BEDROCK"))


def config_home():
    value = os.environ.get("XDG_CONFIG_HOME", "")
    return Path(value) if value.startswith("/") else Path.home() / ".config"


def native_token():
    if sys.platform == "darwin":
        auth = Path.home() / ".cursor/auth.json"
        database = Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
    elif sys.platform == "win32":
        roaming = os.environ.get("APPDATA", "")
        root = Path(roaming) if Path(roaming).is_absolute() else Path.home() / "AppData/Roaming"
        auth = root / "Cursor/auth.json"
        database = root / "Cursor/User/globalStorage/state.vscdb"
    else:
        auth = config_home() / "cursor/auth.json"
        database = config_home() / "Cursor/User/globalStorage/state.vscdb"
    if auth.is_file():
        try:
            data = json.loads(auth.read_text(encoding="utf-8"))
            value = data.get("accessToken") if isinstance(data, dict) else None
        except PermissionError:
            raise ProbeError("native_session_access_denied") from None
        except (OSError, ValueError):
            raise ProbeError("native_session_unreadable") from None
        if isinstance(data, dict) and (data.get("apiKey") or data.get("bedrockCredentials")):
            raise ProbeError("stored_auth_override")
        if value:
            return value, "cursor_cli_native_session"
    if database is None or not database.is_file():
        raise ProbeError("native_session_missing")
    # Immutable mode only when no live WAL/SHM exists; never ignore active WAL.
    suffix = "?mode=ro"
    if not Path(str(database) + "-wal").exists() and not Path(str(database) + "-shm").exists():
        suffix += "&immutable=1"
    try:
        with sqlite3.connect(database.as_uri() + suffix, uri=True, timeout=.25) as db:
            row = db.execute("SELECT value FROM ItemTable WHERE key=? LIMIT 1", ("cursorAuth/accessToken",)).fetchone()
    except sqlite3.Error:
        raise ProbeError("native_session_unreadable") from None
    value = row[0] if row else None
    if isinstance(value, bytes):
        try:
            ascii_utf16 = len(value) % 2 == 0 and all(0 < value[i] < 128 and value[i + 1] == 0 for i in range(0, len(value), 2))
            value = value.decode("utf-16-le" if ascii_utf16 else "utf-8")
        except UnicodeError:
            raise ProbeError("native_session_invalid") from None
    if not value:
        raise ProbeError("native_session_missing")
    return value, "cursor_app_native_session"


def token_payload(token):
    try:
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", token):
            raise ValueError
        segment = token.split(".")[1]
        payload = json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))
        subject = payload["sub"].split("|")[-1]
        expiry = payload["exp"]
        if not re.fullmatch(r"[A-Za-z0-9._-]+", subject) or isinstance(expiry, bool) or not isinstance(expiry, (int, float)) or not math.isfinite(expiry):
            raise ValueError
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        raise ProbeError("native_session_invalid") from None
    if expiry <= time.time() + 60:
        raise ProbeError("native_session_expired")
    return payload, subject


def cookie_for(token):
    _, subject = token_payload(token)
    return "WorkosCursorSessionToken=" + subject + "%3A%3A" + token


def usage_account_matches_cli(token, expected_cli_auth):
    """Compare entirely in memory. Never expose either side of the identity."""
    if not isinstance(expected_cli_auth, dict) or expected_cli_auth.get("isAuthenticated") is not True:
        return None
    current = expected_cli_auth.get("userInfo")
    if not isinstance(current, dict):
        return None
    _, subject = token_payload(token)
    # Current CLI status only exposes numeric userId. Its auth-info sync saves
    # getMe.authId with that same userId, providing the exact identity bridge.
    try:
        config = json.loads((Path.home() / ".cursor/cli-config.json").read_text(encoding="utf-8"))
        saved = config.get("authInfo")
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(saved, dict):
        return None
    fresh_id, saved_id = current.get("userId"), saved.get("userId")
    if type(fresh_id) is not int or type(saved_id) is not int or fresh_id != saved_id:
        return None
    if current.get("email") and saved.get("email") and current["email"] != saved["email"]:
        return None
    auth_id = saved.get("authId")
    if not isinstance(auth_id, str) or not auth_id:
        return None
    return auth_id.split("|")[-1] == subject


def retry_after_seconds(value):
    """Return only parsed numeric delay, never a server header string."""
    if not isinstance(value, str):
        return None
    if re.fullmatch(r"[0-9]{1,10}", value.strip()):
        return int(value.strip())
    try:
        deadline = email.utils.parsedate_to_datetime(value)
        if deadline.tzinfo is None:
            return None
        return max(0, math.ceil((deadline - dt.datetime.now(dt.timezone.utc)).total_seconds()))
    except (ValueError, TypeError, OverflowError):
        return None


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return None


def sanitize(summary):
    """Fixed schema excludes identity, messages, raw response, and unknown fields."""
    result = {"billingCycleStart": timestamp(summary.get("billingCycleStart")),
              "billingCycleEnd": timestamp(summary.get("billingCycleEnd"))}
    for root in ("individualUsage", "teamUsage"):
        obj = summary.get(root)
        if not isinstance(obj, dict):
            continue
        result[root] = {}
        for name in (("plan", "overall", "onDemand") if root == "individualUsage" else ("pooled", "onDemand")):
            block = obj.get(name)
            if not isinstance(block, dict):
                continue
            projected = {k: number(block.get(k)) for k in ("used", "limit", "remaining")}
            projected["enabled"] = block.get("enabled") if type(block.get("enabled")) is bool else None
            if name == "plan":
                for k in ("autoPercentUsed", "apiPercentUsed", "totalPercentUsed"):
                    projected[k] = number(block.get(k))
            result[root][name] = projected
    return result


def normalize(summary, source):
    safe = sanitize(summary)
    observed = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    plan = safe.get("individualUsage", {}).get("plan", {})
    cycle_end = safe["billingCycleEnd"]
    cycle_start = safe["billingCycleStart"]
    current = bool(cycle_start and cycle_end and
                   dt.datetime.fromisoformat(cycle_start.replace("Z", "+00:00")) <=
                   dt.datetime.fromisoformat(observed.replace("Z", "+00:00")) <
                   dt.datetime.fromisoformat(cycle_end.replace("Z", "+00:00")))
    enabled = plan.get("enabled") is True
    windows = []
    for scope, field in (("cursor_models", "autoPercentUsed"), ("other_models", "apiPercentUsed")):
        used = plan.get(field)
        valid = used is not None and current and enabled
        windows.append({"scope": scope, "label": "Cursor Models" if scope == "cursor_models" else "Other Models",
                        "source_field": "individualUsage.plan." + field,
                        "used_percent": used if valid else None,
                        "remaining_percent": max(0.0, min(100.0, 100.0 - used)) if valid else None,
                        "resets_at": cycle_end, "status": "known" if valid else "unknown"})
    total = plan.get("totalPercentUsed")
    aggregate = {"scope": "individual_plan_aggregate", "used_percent": total if current and enabled else None,
                 "remaining_percent": max(0.0, min(100.0, 100.0 - total)) if total is not None and current and enabled else None,
                 "used_cents": plan.get("used"), "limit_cents": plan.get("limit"), "remaining_cents": plan.get("remaining"),
                 "resets_at": cycle_end}
    return {"provider": "cursor", "quota_status": "known" if any(w["status"] == "known" for w in windows) else "unknown",
            "quota_source": ENDPOINT, "auth_source": source, "observed_at": observed, "billing_cycle_start": cycle_start,
            "windows": windows, "aggregate": aggregate, "sanitized_response": safe,
            "usage_basis": "server_reported", "scope_mapping_source": "CodexBar docs/cursor.md snapshot mapping; Cursor usage-limits model pools"}


def fetch_quota(timeout=10, expected_cli_auth=None):
    source = None
    session_match = None
    retry_seconds = None
    try:
        if auth_override_present():
            raise ProbeError("auth_or_endpoint_override")
        token, source = native_token()
        session_match = usage_account_matches_cli(token, expected_cli_auth)
        if session_match is False:
            raise ProbeError("usage_account_mismatch")
        header = cookie_for(token)
        # HTTPSConnection makes one verified-host request. It never follows redirects,
        # imports proxy credentials, stores cookies, or refreshes the session.
        conn = http.client.HTTPSConnection("cursor.com", timeout=timeout, context=ssl.create_default_context())
        try:
            conn.request("GET", "/api/usage-summary", headers={"Cookie": header, "Accept": "application/json", "User-Agent": "agent-capacity-allowance-probe/1"})
            response = conn.getresponse()
            if response.status != 200:
                reason = "access_denied" if response.status in (401, 403) else "rate_limited" if response.status == 429 else "http_" + str(response.status)
                raise ProbeError(reason, retry_after_seconds(response.getheader("Retry-After")))
            body = response.read(1024 * 1024 + 1)
            if len(body) > 1024 * 1024:
                raise ProbeError("response_too_large")
        finally:
            conn.close()
        try:
            summary = json.loads(body)
        except ValueError:
            raise ProbeError("invalid_response") from None
        if not isinstance(summary, dict):
            raise ProbeError("invalid_response")
        result = normalize(summary, source)
        result["usage_account_matches_cli"] = session_match
        return result
    except ProbeError as exc:
        reason = str(exc)
        retry_seconds = exc.retry_after_seconds
    except (OSError, http.client.HTTPException):
        reason = "network_unavailable"
    result = {"provider": "cursor", "quota_status": "unknown", "quota_source": ENDPOINT,
            "auth_source": source, "observed_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "windows": [], "reason": reason, "usage_account_matches_cli": session_match}
    if retry_seconds is not None:
        result["retry_after_seconds"] = retry_seconds
    return result


if __name__ == "__main__":
    print(json.dumps(fetch_quota(), indent=2, allow_nan=False))
