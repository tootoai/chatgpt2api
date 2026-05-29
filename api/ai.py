from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field

from api.image_inputs import parse_image_edit_request, read_image_sources
from api.support import require_identity, resolve_image_base_url
from services.content_filter import check_request, request_text
from services.image_executor_service import image_executor_service
from services.log_service import LoggedCall
from services.protocol import (
    anthropic_v1_messages,
    openai_v1_chat_complete,
    openai_v1_image_edit,
    openai_v1_image_generations,
    openai_v1_models,
    openai_v1_response,
)
from utils.helper import IMAGE_MODELS, has_response_image_generation_tool, is_image_chat_request


def _image_model_or_default(model: object) -> str:
    value = str(model or "").strip()
    return value if value in IMAGE_MODELS else "gpt-image-2"


def _chat_has_image_reference(body: dict[str, object]) -> bool:
    messages = body.get("messages")
    if not isinstance(messages, list):
        return False
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if isinstance(item, dict) and str(item.get("type") or "").strip() in {"image_url", "input_image"}:
                return True
    return False


def _response_has_image_reference(value: object) -> bool:
    if isinstance(value, dict):
        item_type = str(value.get("type") or "").strip()
        if item_type in {"image_url", "input_image"}:
            return True
        return any(_response_has_image_reference(item) for item in value.values())
    if isinstance(value, list):
        return any(_response_has_image_reference(item) for item in value)
    return False


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: str = "gpt-image-2"
    n: int = Field(default=1, ge=1, le=4)
    size: str | None = None
    quality: str = "auto"
    response_format: str = "b64_json"
    history_disabled: bool = True
    stream: bool | None = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str | None = None
    prompt: str | None = None
    n: int | None = None
    stream: bool | None = None
    modalities: list[str] | None = None
    messages: list[dict[str, object]] | None = None


class ResponseCreateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str | None = None
    input: object | None = None
    tools: list[dict[str, object]] | None = None
    tool_choice: object | None = None
    stream: bool | None = None


class AnthropicMessageRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str | None = None
    messages: list[dict[str, object]] | None = None
    system: object | None = None
    stream: bool | None = None


async def filter_or_log(call: LoggedCall, text: str) -> None:
    try:
        await run_in_threadpool(check_request, text)
    except HTTPException as exc:
        call.log("调用失败", status="failed", error=str(exc.detail))
        raise


def create_router() -> APIRouter:
    router = APIRouter()

    @router.get("/v1/models")
    async def list_models(authorization: str | None = Header(default=None)):
        require_identity(authorization)
        try:
            return await run_in_threadpool(openai_v1_models.list_models)
        except Exception as exc:
            raise HTTPException(status_code=502, detail={"error": str(exc)}) from exc

    @router.post("/v1/images/generations")
    async def generate_images(
            body: ImageGenerationRequest,
            request: Request,
            authorization: str | None = Header(default=None),
    ):
        identity = require_identity(authorization)
        payload = body.model_dump(mode="python")
        payload["base_url"] = resolve_image_base_url(request)
        call = LoggedCall(identity, "/v1/images/generations", body.model, "文生图", request_text=body.prompt)
        await filter_or_log(call, body.prompt)
        if payload.get("stream"):
            return await call.run(openai_v1_image_generations.handle, payload)
        return await call.run(openai_v1_image_generations.handle, payload, executor=image_executor_service.run)

    @router.post("/v1/images/edits")
    async def edit_images(
            request: Request,
            authorization: str | None = Header(default=None),
    ):
        identity = require_identity(authorization)
        payload, image_sources = await parse_image_edit_request(request)
        prompt = str(payload["prompt"])
        model = str(payload["model"])
        call = LoggedCall(identity, "/v1/images/edits", model, "图生图", request_text=prompt)
        await filter_or_log(call, prompt)
        payload["images"] = await read_image_sources(image_sources)
        payload["base_url"] = resolve_image_base_url(request)
        if payload.get("stream"):
            return await call.run(openai_v1_image_edit.handle, payload)
        return await call.run(openai_v1_image_edit.handle, payload, executor=image_executor_service.run)

    @router.post("/v1/chat/completions")
    async def create_chat_completion(
            body: ChatCompletionRequest,
            request: Request,
            authorization: str | None = Header(default=None),
    ):
        identity = require_identity(authorization)
        payload = body.model_dump(mode="python")
        model = str(payload.get("model") or "auto")
        request_preview = request_text(payload.get("prompt"), payload.get("messages"))
        is_image_request = is_image_chat_request(payload)
        if is_image_request and model not in IMAGE_MODELS:
            model = "gpt-image-2"
            payload["model"] = model
        if is_image_request:
            payload["base_url"] = resolve_image_base_url(request)
        has_reference_image = _chat_has_image_reference(payload) if is_image_request else False
        summary = "图生图" if has_reference_image else "文生图" if is_image_request else "文本生成"
        call = LoggedCall(identity, "/v1/chat/completions", model, summary, request_text=request_preview)
        await filter_or_log(call, request_preview)
        if is_image_request:
            if payload.get("stream"):
                return await call.run(openai_v1_chat_complete.handle, payload)
            return await call.run(openai_v1_chat_complete.handle, payload, executor=image_executor_service.run)
        return await call.run(openai_v1_chat_complete.handle, payload)

    @router.post("/v1/responses")
    async def create_response(
            body: ResponseCreateRequest,
            request: Request,
            authorization: str | None = Header(default=None),
    ):
        identity = require_identity(authorization)
        payload = body.model_dump(mode="python")
        model = str(payload.get("model") or "auto")
        request_preview = request_text(payload.get("input"), payload.get("instructions"))
        is_image_request = has_response_image_generation_tool(payload) or model in IMAGE_MODELS
        if is_image_request:
            model = _image_model_or_default(payload.get("model"))
            payload["model"] = model
            payload["base_url"] = resolve_image_base_url(request)
        summary = "图生图" if is_image_request and _response_has_image_reference(payload.get("input")) else "文生图" if is_image_request else "Responses"
        call = LoggedCall(identity, "/v1/responses", model, summary, request_text=request_preview)
        await filter_or_log(call, request_preview)
        if is_image_request:
            if payload.get("stream"):
                return await call.run(openai_v1_response.handle, payload)
            return await call.run(openai_v1_response.handle, payload, executor=image_executor_service.run)
        return await call.run(openai_v1_response.handle, payload)

    @router.post("/v1/messages")
    async def create_message(
            body: AnthropicMessageRequest,
            authorization: str | None = Header(default=None),
            x_api_key: str | None = Header(default=None, alias="x-api-key"),
            anthropic_version: str | None = Header(default=None, alias="anthropic-version"),
    ):
        identity = require_identity(authorization or (f"Bearer {x_api_key}" if x_api_key else None))
        payload = body.model_dump(mode="python")
        model = str(payload.get("model") or "auto")
        request_preview = request_text(payload.get("system"), payload.get("messages"), payload.get("tools"))
        call = LoggedCall(identity, "/v1/messages", model, "Messages", request_text=request_preview)
        await filter_or_log(call, request_preview)
        if model in IMAGE_MODELS:
            error = "Anthropic /v1/messages 不支持图片模型，请使用 /v1/images/*、/v1/chat/completions 或 /v1/responses。"
            call.log("调用失败", status="failed", error=error)
            raise HTTPException(status_code=400, detail={"error": error})
        return await call.run(anthropic_v1_messages.handle, payload, sse="anthropic")

    return router
