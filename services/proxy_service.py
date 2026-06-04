"""Global outbound proxy helpers for upstream ChatGPT and CPA requests."""

from __future__ import annotations

import time
from urllib.parse import urlparse

from curl_cffi.requests import Session

from services.config import config

PROXY_PROFILE_PREFIX = "profile:"
DIRECT_PROXY_VALUE = "direct"


class ProxySettingsStore:
    def build_session_kwargs(self, account: dict | None = None, proxy: str = "", **session_kwargs) -> dict[str, object]:
        resolved_proxy = resolve_proxy(account=account, proxy=proxy)
        if resolved_proxy:
            session_kwargs["proxy"] = resolved_proxy
        return session_kwargs


def _clean(value: object) -> str:
    return str(value or "").strip()


def _is_valid_proxy_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https", "socks5", "socks5h"} and bool(parsed.netloc)


def normalize_profile_reference(profile_id: object) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in _clean(profile_id))
    cleaned = cleaned.strip("-._")[:64]
    return f"{PROXY_PROFILE_PREFIX}{cleaned}" if cleaned else ""


def is_profile_reference(value: object) -> bool:
    return _clean(value).lower().startswith(PROXY_PROFILE_PREFIX)


def profile_id_from_reference(value: object) -> str:
    raw = _clean(value)
    if not raw.lower().startswith(PROXY_PROFILE_PREFIX):
        return ""
    return raw[len(PROXY_PROFILE_PREFIX):].strip()


def resolve_proxy_url(value: object) -> str | None:
    raw = _clean(value)
    if not raw:
        return ""
    if raw.lower() == DIRECT_PROXY_VALUE:
        return ""
    if is_profile_reference(raw):
        profile = config.get_proxy_profile(profile_id_from_reference(raw))
        if not profile or profile.get("enabled") is False:
            return None
        return _clean(profile.get("proxy"))
    return raw


def resolve_proxy(account: dict | None = None, proxy: str = "") -> str:
    explicit = _clean(proxy)
    account_proxy = _clean((account or {}).get("proxy"))
    global_proxy = _clean(config.get_proxy_settings())

    for candidate in (explicit, account_proxy):
        if not candidate:
            continue
        resolved = resolve_proxy_url(candidate)
        if resolved is not None:
            return resolved
        break

    resolved_global = resolve_proxy_url(global_proxy)
    return resolved_global or ""


def test_proxy(url: str, *, timeout: float = 15.0) -> dict:
    candidate = _clean(url)
    if not candidate:
        return {"ok": False, "status": 0, "latency_ms": 0, "error": "proxy url is required"}
    if not _is_valid_proxy_url(candidate):
        return {"ok": False, "status": 0, "latency_ms": 0, "error": "invalid proxy url"}
    session = Session(impersonate="edge101", verify=True, proxy=candidate)
    started = time.perf_counter()
    try:
        response = session.get(
            "https://chatgpt.com/api/auth/csrf",
            headers={"user-agent": "Mozilla/5.0 (chatgpt2api proxy test)"},
            timeout=timeout,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": response.status_code < 500,
            "status": int(response.status_code),
            "latency_ms": latency_ms,
            "error": None if response.status_code < 500 else f"HTTP {response.status_code}",
        }
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": False,
            "status": 0,
            "latency_ms": latency_ms,
            "error": str(exc) or exc.__class__.__name__,
        }
    finally:
        session.close()

proxy_settings = ProxySettingsStore()

