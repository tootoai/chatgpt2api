from __future__ import annotations

import hashlib
import json
import itertools
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
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
INTERNAL_RESPONSE_KEYS = {"_account_email", "_conversation_id"}


class LogService:
    def __init__(self, path: Path):
        self.path = path
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

    @staticmethod
    def _detail_value(item: dict[str, Any], key: str) -> str:
        detail = item.get("detail")
        if isinstance(detail, dict):
            value = detail.get(key)
            if value not in (None, ""):
                return str(value).strip()
            diagnosis = detail.get("diagnosis")
            if isinstance(diagnosis, dict):
                value = diagnosis.get(key)
                if value not in (None, ""):
                    return str(value).strip()
        value = item.get(key)
        return "" if value in (None, "") else str(value).strip()

    @classmethod
    def _is_success(cls, item: dict[str, Any]) -> bool:
        return cls._detail_value(item, "status").lower() == "success"

    @classmethod
    def _is_failed(cls, item: dict[str, Any]) -> bool:
        status = cls._detail_value(item, "status").lower()
        return status == "failed" or bool(cls._detail_value(item, "error") or cls._detail_value(item, "error_code"))

    @classmethod
    def _is_limited(cls, item: dict[str, Any]) -> bool:
        haystack = " ".join(
            [
                cls._detail_value(item, "status"),
                cls._detail_value(item, "error_code"),
                cls._detail_value(item, "reason"),
                cls._detail_value(item, "error"),
            ]
        ).lower()
        return any(marker in haystack for marker in ("limit", "quota", "429", "限流", "受限"))

    @classmethod
    def _account_label(cls, item: dict[str, Any]) -> str:
        return (
            cls._detail_value(item, "account_email")
            or cls._detail_value(item, "key_name")
            or cls._detail_value(item, "key_id")
        )

    @classmethod
    def _conversation_id(cls, item: dict[str, Any]) -> str:
        return cls._detail_value(item, "conversation_id")

    @classmethod
    def _search_blob(cls, item: dict[str, Any]) -> str:
        detail = item.get("detail")
        try:
            detail_text = json.dumps(detail or {}, ensure_ascii=False, sort_keys=True)
        except Exception:
            detail_text = str(detail or "")
        return " ".join(
            [
                str(item.get("id") or ""),
                str(item.get("time") or ""),
                str(item.get("type") or ""),
                str(item.get("summary") or ""),
                detail_text,
            ]
        ).lower()

    @classmethod
    def _matches_query_filters(
        cls,
        item: dict[str, Any],
        *,
        status: str = "",
        endpoint: str = "",
        model: str = "",
        account: str = "",
        conversation_id: str = "",
        search: str = "",
    ) -> bool:
        normalized_status = status.lower().strip()
        if normalized_status == "success" and not cls._is_success(item):
            return False
        if normalized_status == "failed" and not cls._is_failed(item):
            return False
        if normalized_status == "limited" and not cls._is_limited(item):
            return False
        if normalized_status not in {"", "success", "failed", "limited"}:
            if cls._detail_value(item, "status").lower() != normalized_status:
                return False

        endpoint_filter = endpoint.lower().strip()
        if endpoint_filter and endpoint_filter not in cls._detail_value(item, "endpoint").lower():
            return False

        model_filter = model.lower().strip()
        if model_filter and cls._detail_value(item, "model").lower() != model_filter:
            return False

        account_filter = account.lower().strip()
        if account_filter and cls._account_label(item).lower() != account_filter:
            return False

        conversation_filter = conversation_id.lower().strip()
        if conversation_filter and conversation_filter not in cls._conversation_id(item).lower():
            return False

        search_filter = search.lower().strip()
        if search_filter and search_filter not in cls._search_blob(item):
            return False
        return True

    @staticmethod
    def _increment(counter: dict[str, int], key: str) -> None:
        value = str(key or "").strip()
        if value:
            counter[value] = counter.get(value, 0) + 1

    @classmethod
    def _collect_facets(cls, item: dict[str, Any], facets: dict[str, dict[str, int]]) -> None:
        cls._increment(facets["statuses"], cls._detail_value(item, "status"))
        cls._increment(facets["endpoints"], cls._detail_value(item, "endpoint"))
        cls._increment(facets["models"], cls._detail_value(item, "model"))
        cls._increment(facets["accounts"], cls._account_label(item))

    @classmethod
    def _increment_stats(cls, item: dict[str, Any], stats: dict[str, int]) -> None:
        stats["total"] += 1
        if cls._is_success(item):
            stats["success"] += 1
        if cls._is_failed(item):
            stats["failed"] += 1
        if cls._is_limited(item):
            stats["limited"] += 1
        if "/images/" in cls._detail_value(item, "endpoint"):
            stats["image"] += 1
        if cls._detail_value(item, "error_code") == "upstream_text_reply" or cls._detail_value(item, "raw_upstream_message"):
            stats["text_reply"] += 1

    def add(self, type: str, summary: str = "", detail: dict[str, Any] | None = None, **data: Any) -> None:
        item = {
            "id": uuid4().hex,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": type,
            "summary": summary,
            "detail": detail or data,
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(self._serialize_item(item) + "\n")

    def list(self, type: str = "", start_date: str = "", end_date: str = "", limit: int = 200) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        items: list[dict[str, Any]] = []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        for line_number in range(len(lines) - 1, -1, -1):
            item = self._parse_line(lines[line_number], line_number)
            if item is None:
                continue
            if not self._matches_filters(item, type=type, start_date=start_date, end_date=end_date):
                continue
            items.append(item)
            if len(items) >= limit:
                break
        return items

    def query(
        self,
        *,
        type: str = "",
        start_date: str = "",
        end_date: str = "",
        status: str = "",
        endpoint: str = "",
        model: str = "",
        account: str = "",
        conversation_id: str = "",
        search: str = "",
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        safe_limit = min(max(int(limit or 200), 1), 20000)
        safe_offset = max(int(offset or 0), 0)
        result = {
            "items": [],
            "total": 0,
            "limit": safe_limit,
            "offset": safe_offset,
            "has_more": False,
            "facets": {
                "statuses": {},
                "endpoints": {},
                "models": {},
                "accounts": {},
            },
            "stats": {
                "total": 0,
                "success": 0,
                "failed": 0,
                "limited": 0,
                "image": 0,
                "text_reply": 0,
            },
        }
        if not self.path.exists():
            return result

        lines = self.path.read_text(encoding="utf-8").splitlines()
        for line_number in range(len(lines) - 1, -1, -1):
            item = self._parse_line(lines[line_number], line_number)
            if item is None:
                continue
            if not self._matches_filters(item, type=type, start_date=start_date, end_date=end_date):
                continue
            self._collect_facets(item, result["facets"])
            if not self._matches_query_filters(
                item,
                status=status,
                endpoint=endpoint,
                model=model,
                account=account,
                conversation_id=conversation_id,
                search=search,
            ):
                continue
            self._increment_stats(item, result["stats"])
            result["total"] += 1
            if result["total"] <= safe_offset:
                continue
            if len(result["items"]) < safe_limit:
                result["items"].append(item)

        result["has_more"] = safe_offset + len(result["items"]) < result["total"]
        return result

    def list_page(self, **kwargs: Any) -> dict[str, Any]:
        return self.query(**kwargs)

    def delete(self, ids: list[str]) -> dict[str, int]:
        target_ids = {str(item or "").strip() for item in ids if str(item or "").strip()}
        if not self.path.exists() or not target_ids:
            return {"removed": 0}
        lines = self.path.read_text(encoding="utf-8").splitlines()
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
        content = "\n".join(kept_lines)
        if content:
            content += "\n"
        self.path.write_text(content, encoding="utf-8")
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


def _collect_account_emails(value: object) -> list[str]:
    emails: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"_account_email", "account_email"} and isinstance(item, str) and item.strip():
                emails.append(item.strip())
            else:
                emails.extend(_collect_account_emails(item))
    elif isinstance(value, list):
        for item in value:
            emails.extend(_collect_account_emails(item))
    return emails


def _collect_conversation_ids(value: object) -> list[str]:
    ids: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "_conversation_id" and isinstance(item, str) and item.strip():
                ids.append(item.strip())
            else:
                ids.extend(_collect_conversation_ids(item))
    elif isinstance(value, list):
        for item in value:
            ids.extend(_collect_conversation_ids(item))
    return ids


def _strip_internal_response_fields(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _strip_internal_response_fields(item)
            for key, item in value.items()
            if key not in INTERNAL_RESPONSE_KEYS
        }
    if isinstance(value, list):
        return [_strip_internal_response_fields(item) for item in value]
    return value


def _request_excerpt(text: object, limit: int = 1000) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


IMAGE_ERROR_CONTEXT_FIELDS = (
    "error_code",
    "stage",
    "reason",
    "conversation_id",
    "can_resume_poll",
    "upstream_message_len",
    "upstream_message_preview",
    "upstream_message_truncated",
    "raw_upstream_message",
    "raw_upstream_message_len",
    "raw_upstream_message_truncated",
    "tool_invoked",
    "turn_use_case",
    "blocked",
    "terminal_message",
)


def _image_error_context(exc: Exception) -> dict[str, Any]:
    context: dict[str, Any] = {}
    diagnostics = getattr(exc, "diagnostics", None)
    if isinstance(diagnostics, dict):
        context.update({key: value for key, value in diagnostics.items() if value not in (None, "")})
    status_code = getattr(exc, "status_code", None)
    if status_code not in (None, ""):
        try:
            context.setdefault("response_status_code", int(status_code))
        except (TypeError, ValueError):
            context.setdefault("response_status_code", status_code)
    try:
        from services.protocol.conversation import image_error_diagnostic

        diagnostic = image_error_diagnostic(exc)
    except Exception:
        diagnostic = {}
    if diagnostic:
        context.update(diagnostic)
        context["diagnosis"] = dict(diagnostic)
    for key in IMAGE_ERROR_CONTEXT_FIELDS:
        if not hasattr(exc, key):
            continue
        value = getattr(exc, key)
        if value is None or value == "":
            continue
        if key == "upstream_message_len" and value == 0:
            continue
        context.setdefault(key, value)
    return context


def _image_error_response(exc: Exception) -> JSONResponse:
    from services.protocol.conversation import public_image_error_message

    message = public_image_error_message(str(exc))
    if "no available image quota" in message.lower():
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
    request_shape: dict[str, int] | None = None

    async def run(self, handler, *args, sse: str = "openai"):
        from services.protocol.conversation import ImageGenerationError

        try:
            result = await run_in_threadpool(handler, *args)
        except ImageGenerationError as exc:
            self.log(
                "调用失败",
                status="failed",
                error=str(exc),
                account_email=getattr(exc, "account_email", ""),
                conversation_id=getattr(exc, "conversation_id", ""),
                extra=_image_error_context(exc),
            )
            return _image_error_response(exc)
        except HTTPException as exc:
            self.log("调用失败", status="failed", error=str(exc.detail))
            raise
        except Exception as exc:
            self.log(
                "调用失败",
                status="failed",
                error=str(exc),
                account_email=getattr(exc, "account_email", ""),
                extra=_image_error_context(exc) if self.endpoint.startswith("/v1/images") else None,
            )
            if self.endpoint.startswith("/v1/images"):
                return _image_error_response(exc)
            return _protocol_error_response(exc, 502, sse)

        if isinstance(result, dict):
            self.log("调用完成", result)
            response = dict(result)
            response.pop("_account_email", None)
            return response

        sender = anthropic_sse_stream if sse == "anthropic" else sse_json_stream
        try:
            has_first, first = await run_in_threadpool(_next_item, result)
        except ImageGenerationError as exc:
            self.log(
                "调用失败",
                status="failed",
                error=str(exc),
                account_email=getattr(exc, "account_email", ""),
                conversation_id=getattr(exc, "conversation_id", ""),
                extra=_image_error_context(exc),
            )
            return _image_error_response(exc)
        except HTTPException as exc:
            self.log("调用失败", status="failed", error=str(exc.detail))
            raise
        except Exception as exc:
            self.log(
                "调用失败",
                status="failed",
                error=str(exc),
                account_email=getattr(exc, "account_email", ""),
                extra=_image_error_context(exc) if self.endpoint.startswith("/v1/images") else None,
            )
            if self.endpoint.startswith("/v1/images"):
                return _image_error_response(exc)
            return _protocol_error_response(exc, 502, sse)
        if not has_first:
            self.log("流式调用结束")
            return StreamingResponse(sender(()), media_type="text/event-stream")
        return StreamingResponse(sender(self.stream(itertools.chain([first], result))), media_type="text/event-stream")

    def stream(self, items):
        urls: list[str] = []
        account_emails: list[str] = []
        conversation_ids: list[str] = []
        failed = False
        try:
            for item in items:
                urls.extend(_collect_urls(item))
                account_emails.extend(_collect_account_emails(item))
                conversation_ids.extend(_collect_conversation_ids(item))
                yield _strip_internal_response_fields(item)
        except Exception as exc:
            failed = True
            self.log(
                "流式调用失败",
                status="failed",
                error=str(exc),
                urls=urls,
                account_email=(account_emails[0] if account_emails else getattr(exc, "account_email", "")),
                conversation_id=(conversation_ids[0] if conversation_ids else getattr(exc, "conversation_id", "")),
                extra=_image_error_context(exc),
            )
            if self.endpoint.startswith("/v1/images") and not hasattr(exc, "to_openai_error"):
                from services.protocol.conversation import ImageGenerationError, public_image_error_message

                raise ImageGenerationError(public_image_error_message(str(exc))) from exc
            raise
        finally:
            if not failed:
                self.log("流式调用结束", urls=urls, account_email=account_emails[0] if account_emails else "",
                         conversation_id=conversation_ids[0] if conversation_ids else "")

    def log(self, suffix: str, result: object = None, status: str = "success", error: str = "",
            urls: list[str] | None = None, account_email: str = "", conversation_id: str = "",
            extra: dict[str, Any] | None = None) -> None:
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
        if self.request_shape:
            detail["request_shape"] = self.request_shape
        if extra:
            detail.update(extra)
        if error:
            detail["error"] = error
        email = str(account_email or "").strip()
        if not email:
            emails = _collect_account_emails(result)
            email = emails[0] if emails else ""
        if email:
            detail["account_email"] = email
        conv_id = str(conversation_id or "").strip()
        if not conv_id:
            conv_ids = _collect_conversation_ids(result)
            conv_id = conv_ids[0] if conv_ids else ""
        if conv_id:
            detail["conversation_id"] = conv_id
        collected_urls = [*(urls or []), *_collect_urls(result)]
        if collected_urls and not self.endpoint.startswith("/v1/search"):
            detail["urls"] = list(dict.fromkeys(collected_urls))
        log_service.add(LOG_TYPE_CALL, f"{self.summary}{suffix}", detail)
