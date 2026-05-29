from __future__ import annotations

import hashlib
import json
import itertools
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse

from services.config import DATA_DIR
from services.protocol.error_response import anthropic_error_response, openai_error_response
from utils.helper import anthropic_sse_stream, sse_json_stream

LOG_TYPE_CALL = "call"
LOG_TYPE_ACCOUNT = "account"
MAX_LOG_ITEMS = 1000


class LogService:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _legacy_id(raw_line: str, line_number: int) -> str:
        payload = f"{line_number}:{raw_line}".encode("utf-8", errors="ignore")
        return hashlib.sha1(payload).hexdigest()[:24]

    def _parse_line(self, raw_line: str, line_number: int) -> dict[str, Any] | None:
        try:
            item = json.loads(raw_line)
        except Exception:
            return None
        if not isinstance(item, dict):
            return None
        parsed = dict(item)
        parsed["id"] = str(parsed.get("id") or self._legacy_id(raw_line, line_number))
        return parsed

    @staticmethod
    def _serialize_item(item: dict[str, Any]) -> str:
        return json.dumps(item, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _matches_filters(item: dict[str, Any], *, type: str = "", start_date: str = "", end_date: str = "") -> bool:
        t = str(item.get("time") or "")
        day = t[:10]
        if type and item.get("type") != type:
            return False
        if start_date and day < start_date:
            return False
        if end_date and day > end_date:
            return False
        return True

    def add(self, type: str, summary: str = "", detail: dict[str, Any] | None = None, **data: Any) -> None:
        item = {
            "id": uuid4().hex,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": type,
            "summary": summary,
            "detail": detail or data,
        }
        with self._lock:
            with self.path.open("a", encoding="utf-8") as file:
                file.write(self._serialize_item(item) + "\n")
            self._trim_locked()

    def _read_lines_locked(self) -> list[str]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_LOG_ITEMS:
            lines = lines[-MAX_LOG_ITEMS:]
            self._write_lines_locked(lines)
        return lines

    def _write_lines_locked(self, lines: list[str]) -> None:
        content = "\n".join(lines)
        if content:
            content += "\n"
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(self.path)

    def _trim_locked(self) -> None:
        if not self.path.exists():
            return
        lines = self.path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= MAX_LOG_ITEMS:
            return
        self._write_lines_locked(lines[-MAX_LOG_ITEMS:])

    def list(
            self,
            type: str = "",
            start_date: str = "",
            end_date: str = "",
            limit: int = 200,
            offset: int = 0,
    ) -> list[dict[str, Any]]:
        return self.list_page(
            type=type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )["items"]

    def list_page(
            self,
            type: str = "",
            start_date: str = "",
            end_date: str = "",
            limit: int = 200,
            offset: int = 0,
    ) -> dict[str, Any]:
        if not self.path.exists():
            return {"items": [], "total": 0, "limit": limit, "offset": offset}
        items: list[dict[str, Any]] = []
        total = 0
        safe_limit = max(1, min(int(limit or 200), 500))
        safe_offset = max(0, int(offset or 0))
        with self._lock:
            lines = self._read_lines_locked()
            for line_number in range(len(lines) - 1, -1, -1):
                item = self._parse_line(lines[line_number], line_number)
                if item is None:
                    continue
                if not self._matches_filters(item, type=type, start_date=start_date, end_date=end_date):
                    continue
                matched_index = total
                total += 1
                if matched_index < safe_offset:
                    continue
                if len(items) < safe_limit:
                    items.append(item)
        return {"items": items, "total": total, "limit": safe_limit, "offset": safe_offset}

    def delete(self, ids: list[str]) -> dict[str, int]:
        target_ids = {str(item or "").strip() for item in ids if str(item or "").strip()}
        if not self.path.exists() or not target_ids:
            return {"removed": 0}
        with self._lock:
            lines = self._read_lines_locked()
            kept_lines: list[str] = []
            removed = 0
            for line_number, raw_line in enumerate(lines):
                item = self._parse_line(raw_line, line_number)
                if item is None:
                    kept_lines.append(raw_line)
                    continue
                if str(item.get("id") or "") in target_ids:
                    removed += 1
                    continue
                kept_lines.append(self._serialize_item(item))
            self._write_lines_locked(kept_lines[-MAX_LOG_ITEMS:])
        return {"removed": removed}


log_service = LogService(DATA_DIR / "logs.jsonl")


def _collect_urls(value: object) -> list[str]:
    urls: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "url" and isinstance(item, str):
                urls.append(item)
            elif key == "urls" and isinstance(item, list):
                urls.extend(str(url) for url in item if isinstance(url, str))
            else:
                urls.extend(_collect_urls(item))
    elif isinstance(value, list):
        for item in value:
            urls.extend(_collect_urls(item))
    return urls


def _collect_log_urls(value: object) -> list[str]:
    urls = getattr(value, "log_urls", None)
    if not isinstance(urls, list):
        return []
    return [url for url in urls if isinstance(url, str) and url]


def _collect_diagnostics(value: object) -> dict[str, Any]:
    diagnostics = getattr(value, "diagnostics", None)
    return dict(diagnostics) if isinstance(diagnostics, dict) else {}


def _request_excerpt(text: object, limit: int = 1000) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _image_error_response(exc: Exception) -> JSONResponse:
    message = str(exc)
    lower = message.lower()
    if "no available image quota" in lower:
        return openai_error_response(
            {
                "error": {
                    "message": "no available image quota",
                    "type": "insufficient_quota",
                    "param": None,
                    "code": "insufficient_quota",
                }
            },
            429,
        )
    if "all image accounts are busy" in lower or "image workers are busy" in lower:
        return openai_error_response(
            {
                "error": {
                    "message": message or "image service is busy, please retry later",
                    "type": "rate_limit_error",
                    "param": None,
                    "code": "rate_limit_exceeded",
                }
            },
            429,
        )
    if hasattr(exc, "to_openai_error") and hasattr(exc, "status_code"):
        return JSONResponse(status_code=int(exc.status_code), content=exc.to_openai_error())
    return openai_error_response(message, 502)


def _protocol_error_response(exc: Exception, status_code: int, sse: str) -> JSONResponse:
    message = str(exc)
    if sse == "anthropic":
        return anthropic_error_response(message, status_code)
    return openai_error_response(message, status_code)


def _next_item(items):
    try:
        return True, next(items)
    except StopIteration:
        return False, None


@dataclass
class LoggedCall:
    identity: dict[str, object]
    endpoint: str
    model: str
    summary: str
    started: float = field(default_factory=time.time)
    request_text: str = ""

    async def run(
            self,
            handler,
            *args,
            sse: str = "openai",
            executor: Callable[..., Awaitable[Any]] | None = None,
    ):
        from services.protocol.conversation import ImageGenerationError
        from services.image_executor_service import ImageWorkerRejected

        run_callable = executor or run_in_threadpool
        try:
            result = await run_callable(handler, *args)
        except ImageWorkerRejected as exc:
            self.log("调用失败", exc, status="failed", error=str(exc))
            return _protocol_error_response(exc, 429, sse)
        except ImageGenerationError as exc:
            self.log("调用失败", exc, status="failed", error=str(exc))
            return _image_error_response(exc)
        except HTTPException as exc:
            self.log("调用失败", exc, status="failed", error=str(exc.detail))
            raise
        except Exception as exc:
            self.log("调用失败", exc, status="failed", error=str(exc))
            return _protocol_error_response(exc, 502, sse)

        if isinstance(result, dict):
            self.log("调用完成", result)
            return result

        sender = anthropic_sse_stream if sse == "anthropic" else sse_json_stream
        try:
            has_first, first = await run_in_threadpool(_next_item, result)
        except ImageWorkerRejected as exc:
            self.log("调用失败", exc, status="failed", error=str(exc))
            return _image_error_response(exc)
        except ImageGenerationError as exc:
            self.log("调用失败", exc, status="failed", error=str(exc))
            return _image_error_response(exc)
        except HTTPException as exc:
            self.log("调用失败", exc, status="failed", error=str(exc.detail))
            raise
        except Exception as exc:
            self.log("调用失败", exc, status="failed", error=str(exc))
            return _protocol_error_response(exc, 502, sse)
        if not has_first:
            self.log("流式调用结束")
            return StreamingResponse(sender(()), media_type="text/event-stream")
        return StreamingResponse(sender(self.stream(itertools.chain([first], result))), media_type="text/event-stream")

    def stream(self, items):
        urls: list[str] = []
        diagnostics: dict[str, Any] = {}
        failed = False
        try:
            for item in items:
                urls.extend(_collect_log_urls(item))
                urls.extend(_collect_urls(item))
                diagnostics.update(_collect_diagnostics(item))
                yield item
        except Exception as exc:
            failed = True
            self.log("流式调用失败", exc, status="failed", error=str(exc), urls=urls, diagnostics=diagnostics)
            raise
        finally:
            if not failed:
                self.log("流式调用结束", urls=urls, diagnostics=diagnostics)

    def log(self, suffix: str, result: object = None, status: str = "success", error: str = "",
            urls: list[str] | None = None, diagnostics: dict[str, Any] | None = None) -> None:
        detail = {
            "key_id": self.identity.get("id"),
            "key_name": self.identity.get("name"),
            "role": self.identity.get("role"),
            "endpoint": self.endpoint,
            "model": self.model,
            "started_at": datetime.fromtimestamp(self.started).strftime("%Y-%m-%d %H:%M:%S"),
            "ended_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration_ms": int((time.time() - self.started) * 1000),
            "status": status,
        }
        request_excerpt = _request_excerpt(self.request_text)
        if request_excerpt:
            detail["request_text"] = request_excerpt
        if error:
            detail["error"] = error
        response_status_code = getattr(result, "status_code", None)
        if isinstance(response_status_code, int):
            detail["response_status_code"] = response_status_code
        error_type = getattr(result, "error_type", None)
        if error_type:
            detail["error_type"] = str(error_type)
        error_code = getattr(result, "code", None)
        if error_code:
            detail["error_code"] = str(error_code)
        merged_diagnostics = _collect_diagnostics(result)
        if isinstance(diagnostics, dict):
            merged_diagnostics.update(diagnostics)
        if merged_diagnostics:
            for key in (
                    "image_trace_id",
                    "image_stage",
                    "response_status_code",
                    "error_type",
                    "error_code",
                    "conversation_id",
                    "submit_ms",
                    "progress_events",
                    "tool_invoked",
                    "turn_use_case",
                    "url_count",
                    "token",
                    "email",
                    "account_status",
                    "account_type",
                    "quota",
                    "image_quota_unknown",
                    "attempts_made",
                    "tool_records_count",
                    "last_file_ids_count",
                    "last_sediment_ids_count",
                    "timeout_secs",
                    "initial_wait_exhausted_budget",
                    "stage_ms",
                    "stage_timings",
                    "upstream_status",
                    "upstream_context",
                    "download_source",
                    "download_id",
                    "download_error_type",
                    "download_error",
                    "account_selection_errors_count",
                    "account_selection_last_token",
                    "account_selection_last_error_type",
                    "account_selection_last_error",
                    "account_selection_error",
                    "account_selection_wait_secs",
                    "account_pool_total",
                    "account_pool_excluded",
                    "account_pool_ready",
                    "account_pool_available_local",
                    "account_pool_busy_local",
                    "account_pool_disabled",
                    "account_pool_rate_limited",
                    "account_pool_abnormal",
                    "account_pool_no_quota",
                    "account_pool_unknown_quota",
                    "account_pool_concurrency",
                    "image_worker_queue_ms",
                    "image_worker_concurrency",
                    "retry_counts",
                    "last_retry",
            ):
                if key in merged_diagnostics:
                    detail[key] = merged_diagnostics[key]
        collected_urls = [*(urls or []), *_collect_log_urls(result), *_collect_urls(result)]
        if collected_urls:
            detail["urls"] = list(dict.fromkeys(collected_urls))
        log_service.add(LOG_TYPE_CALL, f"{self.summary}{suffix}", detail)
