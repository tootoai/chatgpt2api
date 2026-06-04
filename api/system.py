from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict

from api.support import require_admin, require_identity, resolve_image_base_url
from services.backup_service import BackupError, backup_service
from services.config import config
from services.image_service import (
    compress_images,
    delete_images,
    delete_to_target,
    download_images_zip,
    get_image_download_response,
    get_image_response,
    get_thumbnail_response,
    list_images,
    storage_stats,
)
from services.image_storage_service import ImageStorageError, image_storage_service
from services.image_tags_service import delete_tag, get_all_tags, set_tags
from services.log_service import LOG_TYPE_CALL, log_service
from services.proxy_service import normalize_profile_reference, resolve_proxy_url, test_proxy
from services.runtime_log_service import list_runtime_logs


class SettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")


class ProxyTestRequest(BaseModel):
    url: str = ""


class ProxyProfileRequest(BaseModel):
    id: str = ""
    name: str = ""
    proxy: str = ""
    no_proxy: str = ""
    enabled: bool = True
    notes: str = ""
    create_only: bool = False


class ProxyProfileTestRequest(BaseModel):
    id: str = ""
    url: str = ""


class ImageDeleteRequest(BaseModel):
    paths: list[str] = []
    start_date: str = ""
    end_date: str = ""
    all_matching: bool = False

class ImageDownloadRequest(BaseModel):
    paths: list[str]

class ImageTagsRequest(BaseModel):
    path: str
    tags: list[str]

class LogDeleteRequest(BaseModel):
    ids: list[str] = []
class BackupDeleteRequest(BaseModel):
    key: str = ""


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _proxy_profiles_payload() -> dict[str, Any]:
    return {"profiles": config.get_proxy_profiles()}


def _proxy_profile_id(value: object) -> str:
    reference = normalize_profile_reference(value)
    return reference.split(":", 1)[1] if ":" in reference else ""


def _upsert_proxy_profile(body: ProxyProfileRequest) -> dict[str, Any]:
    profile_id = _proxy_profile_id(body.id or body.name)
    if not profile_id:
        raise ValueError("profile id is required")
    profiles = config.get_proxy_profiles()
    exists = any(profile.get("id") == profile_id for profile in profiles)
    if body.create_only and exists:
        raise ValueError("proxy profile already exists")
    next_profile = {
        "id": profile_id,
        "name": body.name or profile_id,
        "proxy": body.proxy,
        "no_proxy": body.no_proxy,
        "enabled": body.enabled,
        "notes": body.notes,
    }
    next_profiles = [profile for profile in profiles if profile.get("id") != profile_id]
    next_profiles.append(next_profile)
    updated = config.update({"proxy_profiles": next_profiles})
    return {
        "profile": next(
            profile for profile in updated.get("proxy_profiles", []) if profile.get("id") == profile_id
        ),
        "profiles": updated.get("proxy_profiles", []),
    }


def _increment(counter: dict[str, int], key: object, default: str = "unknown") -> None:
    label = _clean_text(key) or default
    counter[label] = counter.get(label, 0) + 1


def _detail_value(item: dict[str, Any], key: str, default: object = "") -> object:
    detail = item.get("detail")
    if isinstance(detail, dict):
        value = detail.get(key)
        if value not in (None, ""):
            return value
    value = item.get(key)
    return default if value in (None, "") else value


def _parse_log_time(value: object) -> datetime | None:
    raw = _clean_text(value)
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _dashboard_bucket_config(time_range: str) -> tuple[str, int]:
    if time_range == "7d":
        return "day", 7
    if time_range == "30d":
        return "day", 30
    return "hour", 24


def _dashboard_buckets(time_range: str, now: datetime | None = None) -> tuple[list[str], dict[str, int]]:
    mode, count = _dashboard_bucket_config(time_range)
    current = now or datetime.now()
    if mode == "day":
        start = datetime(current.year, current.month, current.day) - timedelta(days=count - 1)
        labels = [(start + timedelta(days=idx)).strftime("%m-%d") for idx in range(count)]
        keys = [(start + timedelta(days=idx)).strftime("%Y-%m-%d") for idx in range(count)]
    else:
        start = current.replace(minute=0, second=0, microsecond=0) - timedelta(hours=count - 1)
        labels = [(start + timedelta(hours=idx)).strftime("%H:00") for idx in range(count)]
        keys = [(start + timedelta(hours=idx)).strftime("%Y-%m-%d %H:00") for idx in range(count)]
    return labels, {key: idx for idx, key in enumerate(keys)}


def _bucket_key(value: datetime, time_range: str) -> str:
    mode, _ = _dashboard_bucket_config(time_range)
    if mode == "day":
        return value.strftime("%Y-%m-%d")
    return value.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:00")


def _as_duration_ms(value: object, started_at: datetime | None = None, ended_at: datetime | None = None) -> int | None:
    try:
        number = int(float(str(value)))
        if number >= 0:
            return number
    except (TypeError, ValueError):
        pass
    if started_at and ended_at and ended_at >= started_at:
        return int((ended_at - started_at).total_seconds() * 1000)
    return None


def _is_rate_limited_status(status: str, error_code: str, reason: str) -> bool:
    haystack = " ".join([status, error_code, reason]).lower()
    return any(marker in haystack for marker in ("rate_limited", "rate limit", "ratelimit", "too many requests", "429"))


def _zero_series(size: int) -> list[int]:
    return [0 for _ in range(size)]


def _average_series(sums: list[int], counts: list[int]) -> list[int]:
    return [
        int(round(total / count)) if count > 0 else 0
        for total, count in zip(sums, counts)
    ]


def _dashboard_log_summary(items: list[dict[str, Any]], failure_limit: int = 10, time_range: str = "24h") -> dict[str, Any]:
    by_endpoint: dict[str, int] = {}
    by_model: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_error_code: dict[str, int] = {}
    recent_failures: list[dict[str, Any]] = []
    success_count = 0
    failed_count = 0
    labels, bucket_index = _dashboard_buckets(time_range)
    bucket_count = len(labels)
    total_requests = _zero_series(bucket_count)
    success_requests = _zero_series(bucket_count)
    failed_requests = _zero_series(bucket_count)
    rate_limited_requests = _zero_series(bucket_count)
    model_requests: dict[str, list[int]] = {}
    model_duration_sums: dict[str, list[int]] = {}
    model_duration_counts: dict[str, list[int]] = {}

    for item in items:
        status = _clean_text(_detail_value(item, "status"))
        endpoint = _clean_text(_detail_value(item, "endpoint"))
        model = _clean_text(_detail_value(item, "model"))
        error_code = _clean_text(_detail_value(item, "error_code"))
        if not error_code:
            diagnosis = _detail_value(item, "diagnosis", {})
            if isinstance(diagnosis, dict):
                error_code = _clean_text(diagnosis.get("error_code"))
        reason = _clean_text(_detail_value(item, "reason"))
        started_at = _parse_log_time(_detail_value(item, "started_at"))
        ended_at = _parse_log_time(_detail_value(item, "ended_at"))
        item_time = started_at or _parse_log_time(item.get("time")) or ended_at
        duration_ms = _as_duration_ms(_detail_value(item, "duration_ms"), started_at, ended_at)
        is_rate_limited = _is_rate_limited_status(status, error_code, reason)

        _increment(by_endpoint, endpoint)
        _increment(by_model, model)
        _increment(by_status, status)
        if error_code:
            _increment(by_error_code, error_code)

        if status == "success":
            success_count += 1
        elif status == "failed":
            failed_count += 1
            if len(recent_failures) < failure_limit:
                recent_failures.append(
                    {
                        "id": item.get("id"),
                        "time": item.get("time"),
                        "summary": item.get("summary"),
                        "endpoint": endpoint,
                        "error_code": error_code,
                        "stage": _clean_text(_detail_value(item, "stage")),
                        "reason": _clean_text(_detail_value(item, "reason")),
                        "conversation_id": _clean_text(_detail_value(item, "conversation_id")),
                    }
                )

        if item_time:
            idx = bucket_index.get(_bucket_key(item_time, time_range))
            if idx is not None:
                total_requests[idx] += 1
                if status == "success":
                    success_requests[idx] += 1
                elif is_rate_limited:
                    rate_limited_requests[idx] += 1
                elif status == "failed":
                    failed_requests[idx] += 1

                model_name = model or "unknown"
                model_requests.setdefault(model_name, _zero_series(bucket_count))[idx] += 1
                if duration_ms is not None:
                    model_duration_sums.setdefault(model_name, _zero_series(bucket_count))[idx] += duration_ms
                    model_duration_counts.setdefault(model_name, _zero_series(bucket_count))[idx] += 1

    model_total_times = {
        model_name: _average_series(model_duration_sums[model_name], model_duration_counts.get(model_name, _zero_series(bucket_count)))
        for model_name in model_duration_sums
    }

    return {
        "total": len(items),
        "success": success_count,
        "failed": failed_count,
        "by_endpoint": by_endpoint,
        "by_model": by_model,
        "by_status": by_status,
        "by_error_code": by_error_code,
        "recent_failures": recent_failures,
        "trend": {
            "labels": labels,
            "total_requests": total_requests,
            "success_requests": success_requests,
            "failed_requests": failed_requests,
            "rate_limited_requests": rate_limited_requests,
            "model_requests": model_requests,
            "model_ttfb_times": {},
            "model_total_times": model_total_times,
        },
    }


def create_router(app_version: str) -> APIRouter:
    router = APIRouter()

    @router.post("/auth/login")
    async def login(authorization: str | None = Header(default=None)):
        identity = require_identity(authorization)
        return {
            "ok": True,
            "authenticated": True,
            "version": app_version,
            "role": identity.get("role"),
            "subject_id": identity.get("id"),
            "name": identity.get("name"),
        }

    @router.get("/auth/status")
    async def auth_status(authorization: str | None = Header(default=None)):
        try:
            identity = require_identity(authorization)
        except HTTPException:
            return {
                "ok": False,
                "authenticated": False,
                "version": app_version,
            }
        return {
            "ok": True,
            "authenticated": True,
            "version": app_version,
            "role": identity.get("role"),
            "subject_id": identity.get("id"),
            "name": identity.get("name"),
        }

    @router.get("/version")
    async def get_version():
        return {"version": app_version}

    @router.get("/api/settings")
    async def get_settings(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"config": config.get()}

    @router.post("/api/settings")
    async def save_settings(body: SettingsUpdateRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        try:
            return {"config": config.update(body.model_dump(mode="python"))}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc

    @router.get("/api/images")
    async def get_images(
        request: Request,
        start_date: str = "",
        end_date: str = "",
        media_type: str = "all",
        tag: str = "",
        search: str = "",
        limit: int = Query(default=0, ge=0, le=20000),
        offset: int = Query(default=0, ge=0),
        authorization: str | None = Header(default=None),
    ):
        require_admin(authorization)
        return list_images(
            resolve_image_base_url(request),
            start_date=start_date.strip(),
            end_date=end_date.strip(),
            media_type=media_type.strip(),
            tag=tag.strip(),
            search=search.strip(),
            limit=limit,
            offset=offset,
        )

    @router.get("/images/{image_path:path}", include_in_schema=False)
    async def get_image(image_path: str):
        return get_image_response(image_path)

    @router.get("/image-thumbnails/{image_path:path}", include_in_schema=False)
    async def get_image_thumbnail(image_path: str):
        return get_thumbnail_response(image_path)

    @router.post("/api/images/delete")
    async def delete_images_endpoint(body: ImageDeleteRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return delete_images(body.paths, start_date=body.start_date.strip(), end_date=body.end_date.strip(), all_matching=body.all_matching)

    @router.post("/api/images/download")
    async def download_images_endpoint(body: ImageDownloadRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        buf = download_images_zip(body.paths)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="images.zip"'},
        )

    @router.get("/api/images/download/{image_path:path}")
    async def download_single_image_endpoint(image_path: str, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return get_image_download_response(image_path)

    @router.get("/api/logs")
    async def get_logs(
        type: str = "",
        start_date: str = "",
        end_date: str = "",
        status: str = "",
        endpoint: str = "",
        model: str = "",
        account: str = "",
        conversation_id: str = "",
        search: str = "",
        limit: int = Query(default=500, ge=1, le=20000),
        offset: int = Query(default=0, ge=0),
        authorization: str | None = Header(default=None),
    ):
        require_admin(authorization)
        return log_service.query(
            type=type.strip(),
            start_date=start_date.strip(),
            end_date=end_date.strip(),
            status=status.strip(),
            endpoint=endpoint.strip(),
            model=model.strip(),
            account=account.strip(),
            conversation_id=conversation_id.strip(),
            search=search.strip(),
            limit=limit,
            offset=offset,
        )

    @router.post("/api/logs/delete")
    async def delete_logs(body: LogDeleteRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return log_service.delete(body.ids)

    @router.get("/api/runtime-logs")
    async def get_runtime_logs(
        level: str = "",
        search: str = "",
        source: str = "",
        limit: int = Query(default=300, ge=1, le=2000),
        authorization: str | None = Header(default=None),
    ):
        require_admin(authorization)
        return list_runtime_logs(
            level=level.strip(),
            search=search.strip(),
            source=source.strip(),
            limit=limit,
        )

    @router.post("/api/proxy/test")
    async def test_proxy_endpoint(body: ProxyTestRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        candidate = (body.url or "").strip() or config.get_proxy_settings()
        if not candidate:
            raise HTTPException(status_code=400, detail={"error": "proxy url is required"})
        resolved = resolve_proxy_url(candidate)
        if resolved is None:
            raise HTTPException(status_code=400, detail={"error": "proxy profile is disabled or not found"})
        return {"result": await run_in_threadpool(test_proxy, resolved)}

    @router.get("/api/proxy/profiles")
    async def list_proxy_profiles(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return _proxy_profiles_payload()

    @router.post("/api/proxy/profiles")
    async def save_proxy_profile(body: ProxyProfileRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        try:
            return _upsert_proxy_profile(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc

    @router.put("/api/proxy/profiles")
    async def replace_proxy_profiles(body: list[ProxyProfileRequest], authorization: str | None = Header(default=None)):
        require_admin(authorization)
        profiles: list[dict[str, object]] = []
        for item in body:
            profile_id = _proxy_profile_id(item.id or item.name)
            if not profile_id:
                continue
            profiles.append({
                "id": profile_id,
                "name": item.name or profile_id,
                "proxy": item.proxy,
                "no_proxy": item.no_proxy,
                "enabled": item.enabled,
                "notes": item.notes,
            })
        updated = config.update({"proxy_profiles": profiles})
        return {"profiles": updated.get("proxy_profiles", [])}

    @router.delete("/api/proxy/profiles/{profile_id}")
    async def delete_proxy_profile(profile_id: str, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        normalized = _proxy_profile_id(profile_id)
        profiles = config.get_proxy_profiles()
        next_profiles = [profile for profile in profiles if profile.get("id") != normalized]
        if len(next_profiles) == len(profiles):
            raise HTTPException(status_code=404, detail={"error": "proxy profile not found"})
        updated = config.update({"proxy_profiles": next_profiles})
        return {"deleted": normalized, "profiles": updated.get("proxy_profiles", [])}

    @router.post("/api/proxy/profiles/test")
    async def test_proxy_profile_endpoint(body: ProxyProfileTestRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        candidate = (body.url or "").strip()
        if not candidate and body.id.strip():
            candidate = normalize_profile_reference(body.id)
        if not candidate:
            raise HTTPException(status_code=400, detail={"error": "proxy url or profile id is required"})
        resolved = resolve_proxy_url(candidate)
        if resolved is None:
            raise HTTPException(status_code=400, detail={"error": "proxy profile is disabled or not found"})
        if not resolved:
            raise HTTPException(status_code=400, detail={"error": "proxy url is required"})
        return {"result": await run_in_threadpool(test_proxy, resolved)}

    @router.get("/api/storage/info")
    async def get_storage_info(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        storage = config.get_storage_backend()
        return {
            "backend": storage.get_backend_info(),
            "health": storage.health_check(),
        }

    @router.get("/api/dashboard")
    async def get_dashboard(
        authorization: str | None = Header(default=None),
        log_limit: int = Query(default=5000, ge=1, le=20000),
        time_range: str = Query(default="24h", pattern="^(24h|7d|30d)$"),
    ):
        require_admin(authorization)
        from services.account_service import account_service as acct_svc

        account_stats = acct_svc.get_stats()
        account_healthy = account_stats["active"] > 0 or account_stats["unlimited_quota_count"] > 0
        storage = config.get_storage_backend()
        call_logs = log_service.list(type=LOG_TYPE_CALL, limit=log_limit)
        image_storage_stats = await run_in_threadpool(storage_stats)
        storage_health = await run_in_threadpool(storage.health_check)
        return {
            "status": "ok" if account_healthy else "degraded",
            "healthy": account_healthy,
            "version": app_version,
            "accounts": {
                **account_stats,
                "healthy": account_healthy,
            },
            "storage": {
                "backend": storage.get_backend_info(),
                "health": storage_health,
                "images": image_storage_stats,
            },
            "logs": _dashboard_log_summary(call_logs, time_range=time_range),
        }

    @router.post("/api/backup/test")
    async def test_backup_connection(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        try:
            return {"result": await run_in_threadpool(backup_service.test_connection)}
        except BackupError as exc:
            raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc

    @router.post("/api/image-storage/test")
    async def test_image_storage_endpoint(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"result": await run_in_threadpool(image_storage_service.test_webdav)}

    @router.post("/api/image-storage/sync")
    async def sync_image_storage_endpoint(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        try:
            return {"result": await run_in_threadpool(image_storage_service.sync_all)}
        except ImageStorageError as exc:
            raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc

    @router.get("/api/backups")
    async def get_backups(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        try:
            return {
                "items": await run_in_threadpool(backup_service.list_backups),
                "state": backup_service.get_status(),
                "settings": backup_service.get_settings(),
            }
        except BackupError as exc:
            raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc

    @router.post("/api/backups/run")
    async def run_backup_endpoint(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        try:
            return {"result": await run_in_threadpool(backup_service.run_backup)}
        except BackupError as exc:
            raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc

    @router.post("/api/backups/delete")
    async def delete_backup_endpoint(body: BackupDeleteRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        try:
            await run_in_threadpool(backup_service.delete_backup, body.key)
            return {"ok": True}
        except BackupError as exc:
            raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc

    @router.get("/api/backups/detail")
    async def get_backup_detail(key: str = "", authorization: str | None = Header(default=None)):
        require_admin(authorization)
        try:
            return {"item": await run_in_threadpool(backup_service.get_backup_detail, key)}
        except BackupError as exc:
            raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc

    @router.get("/api/backups/download")
    async def download_backup_endpoint(key: str = "", authorization: str | None = Header(default=None)):
        require_admin(authorization)
        try:
            item = await run_in_threadpool(backup_service.download_backup, key)
        except BackupError as exc:
            raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc
        filename = str(item.get("name") or "backup.bin")
        quoted = quote(filename)
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{quoted}",
            "Content-Length": str(int(item.get("size") or 0)),
        }
        return Response(
            content=bytes(item.get("payload") or b""),
            media_type=str(item.get("content_type") or "application/octet-stream"),
            headers=headers,
        )


    @router.get("/api/images/tags")
    async def list_image_tags(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"tags": get_all_tags()}

    @router.post("/api/images/tags")
    async def update_image_tags(body: ImageTagsRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        rel = body.path.strip().lstrip("/")
        if not rel:
            raise HTTPException(status_code=400, detail={"error": "path is required"})
        tags = set_tags(rel, body.tags)
        return {"ok": True, "tags": tags}

    @router.delete("/api/images/tags/{tag}")
    async def delete_image_tag(tag: str, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        count = delete_tag(tag)
        return {"ok": True, "removed_from": count}

    @router.get("/api/images/storage")
    async def get_image_storage(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return storage_stats()

    @router.post("/api/images/storage/compress")
    async def compress_all_images(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return await run_in_threadpool(compress_images)

    @router.post("/api/images/storage/cleanup-to-target")
    async def cleanup_to_target(
        target_free_mb: int = 500,
        dry_run: bool = False,
        authorization: str | None = Header(default=None),
    ):
        require_admin(authorization)
        return await run_in_threadpool(delete_to_target, target_free_mb, dry_run)

    @router.get("/health", response_model=None)
    async def health_dashboard(format: str = Query(default="html")):
        from services.account_service import account_service as acct_svc
        stats = acct_svc.get_stats()
        storage = config.get_storage_backend()
        storage_health = storage.health_check()
        healthy = stats["active"] > 0 or stats["unlimited_quota_count"] > 0

        stats_json = {
            "status": "ok" if healthy else "degraded",
            "healthy": healthy,
            "version": app_version,
            "storage": {"backend": storage.get_backend_info(), "health": storage_health},
            "accounts": stats,
        }
        if format == "json":
            return stats_json
        return HTMLResponse(f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>号池健康监控 - chatgpt2api</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui,-apple-system,sans-serif;background:#0f1117;color:#e2e8f0;min-height:100vh}}
.header{{background:#1a1d27;border-bottom:1px solid #2a2d3a;padding:16px 24px;display:flex;justify-content:space-between;align-items:center}}
.header h1{{font-size:20px}}
.status-dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px}}
.status-ok{{background:#22c55e;box-shadow:0 0 8px #22c55e88}}
.status-degraded{{background:#f59e0b;box-shadow:0 0 8px #f59e0b88}}
.container{{max-width:960px;margin:0 auto;padding:24px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:24px}}
.card{{background:#1a1d27;border:1px solid #2a2d3a;border-radius:10px;padding:16px}}
.card .value{{font-size:28px;font-weight:700;margin:4px 0}}
.card .label{{font-size:13px;color:#94a3b8}}
.green{{color:#22c55e}}.yellow{{color:#f59e0b}}.red{{color:#ef4444}}.blue{{color:#6c63ff}}
table{{width:100%;border-collapse:collapse;background:#1a1d27;border:1px solid #2a2d3a;border-radius:10px;overflow:hidden}}
th{{background:#242836;font-weight:600;text-align:left;padding:10px 12px;font-size:12px;color:#94a3b8;text-transform:uppercase}}
td{{padding:8px 12px;border-top:1px solid #2a2d3a;font-size:14px}}tr:hover td{{background:rgba(108,99,255,.05)}}
.api-url{{font-family:monospace;font-size:12px;color:#6c63ff}}
.refresh{{font-size:12px;color:#64748b;text-align:center;margin-top:24px}}
</style>
<meta http-equiv="refresh" content="30">
</head>
<body>
<div class="header">
<h1><span class="status-dot {'status-ok' if healthy else 'status-degraded'}"></span>号池健康监控</h1>
<div style="font-size:13px;color:#94a3b8">v{app_version} · 30s 自动刷新</div>
</div>
<div class="container">
<div class="cards">
<div class="card"><div class="label">号池状态</div><div class="value {'green' if healthy else 'yellow'}">{'正常' if healthy else '异常'}</div></div>
<div class="card"><div class="label">当前账号</div><div class="value blue">{stats['total']}</div></div>
<div class="card"><div class="label">累计入库</div><div class="value">{stats['cumulative_total']}</div></div>
<div class="card"><div class="label">可用账号</div><div class="value green">{stats['active']}</div></div>
<div class="card"><div class="label">无限额</div><div class="value">{stats['unlimited_quota_count']}</div></div>
<div class="card"><div class="label">剩余额度</div><div class="value">{stats['total_quota']}</div></div>
<div class="card"><div class="label">限流</div><div class="value yellow">{stats['limited']}</div></div>
<div class="card"><div class="label">异常</div><div class="value red">{stats['abnormal']}</div></div>
<div class="card"><div class="label">禁用</div><div class="value">{stats['disabled']}</div></div>
<div class="card"><div class="label">成功/失败</div><div class="value">{stats['total_success']}<span style="font-size:18px;color:#94a3b8">/</span><span class="red">{stats['total_fail']}</span></div></div>
</div>
<h2 style="margin-bottom:12px;font-size:16px">账号类型分布</h2>
<table>
<tr><th>类型</th><th>数量</th></tr>
{''.join(f'<tr><td>{t}</td><td>{c}</td></tr>' for t,c in sorted(stats['by_type'].items()))}
</table>
<div class="refresh">JSON: <span class="api-url">/health?format=json</span></div>
</div></body></html>""")

    return router
