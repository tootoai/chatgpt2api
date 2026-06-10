from __future__ import annotations

import json
import unittest
from unittest import mock

import services.openai_backend_api as backend_module
from services.openai_backend_api import OpenAIBackendAPI
from services.protocol.conversation import ConversationRequest, ImageGenerationError, stream_codex_image_outputs
from utils.helper import UpstreamHTTPError


class FakeResponse:
    def __init__(self, *, status_code: int, headers: dict | None = None, body: object = ""):
        self.status_code = status_code
        self.headers = headers or {}
        if isinstance(body, (dict, list)):
            self._json_body = body
            self.text = json.dumps(body, ensure_ascii=False)
            self.content = self.text.encode("utf-8")
        elif isinstance(body, bytes):
            self._json_body = None
            self.content = body
            self.text = body.decode("utf-8", "replace")
        else:
            self._json_body = None
            self.text = str(body)
            self.content = self.text.encode("utf-8")

    def json(self):
        if self._json_body is None:
            raise ValueError("not json")
        return self._json_body


class FakeSession:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls: list[dict] = []

    def post(self, url: str, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.response


class FakeCodexImageBackend:
    def __init__(self, events: list[dict]):
        self.events = events
        self.calls: list[dict] = []

    def iter_codex_image_response_events(self, **kwargs):
        self.calls.append(kwargs)
        return iter(self.events)


def make_api(response: FakeResponse) -> tuple[OpenAIBackendAPI, FakeSession]:
    session = FakeSession(response)
    api = OpenAIBackendAPI.__new__(OpenAIBackendAPI)
    api.base_url = "https://chatgpt.com"
    api.access_token = "test-token"
    api.session = session
    api._ensure_codex_source_account = lambda: None
    api._codex_image_input = lambda prompt, images: [{
        "role": "user",
        "content": [{"type": "input_text", "text": prompt}],
    }]
    return api, session


class CodexResponsesTransportTests(unittest.TestCase):
    def test_codex_image_responses_uses_configured_session_transport(self):
        response = FakeResponse(
            status_code=200,
            headers={"content-type": "text/event-stream"},
            body=b'data: {"type":"response.completed","status":"completed"}\n\n',
        )
        api, session = make_api(response)

        with (
            mock.patch.object(backend_module.account_service, "get_account", return_value={}),
            mock.patch.object(backend_module.account_service, "_decode_jwt_payload", return_value={}),
        ):
            events = list(api.iter_codex_image_response_events("draw a cat", size="1024x1024"))

        self.assertEqual(events, [{"type": "response.completed", "status": "completed"}])
        self.assertEqual(len(session.calls), 1)
        call = session.calls[0]
        self.assertEqual(call["url"], "https://chatgpt.com/backend-api/codex/responses")
        self.assertEqual(call["timeout"], 1200)
        self.assertEqual(call["headers"]["Authorization"], "Bearer test-token")
        payload = json.loads(call["data"].decode("utf-8"))
        self.assertEqual(payload["tools"][0]["model"], "gpt-image-2")
        self.assertEqual(payload["tools"][0]["action"], "generate")

    def test_codex_image_responses_preserves_http_error_details(self):
        response = FakeResponse(
            status_code=429,
            headers={"Retry-After": "12"},
            body={"error": {"message": "rate limited"}},
        )
        api, _session = make_api(response)

        with (
            mock.patch.object(backend_module.account_service, "get_account", return_value={}),
            mock.patch.object(backend_module.account_service, "_decode_jwt_payload", return_value={}),
        ):
            with self.assertRaises(UpstreamHTTPError) as caught:
                list(api.iter_codex_image_response_events("draw a cat"))

        self.assertEqual(caught.exception.status_code, 429)
        self.assertEqual(caught.exception.retry_after, 12)
        self.assertEqual(caught.exception.body, {"error": {"message": "rate limited"}})

    def test_codex_image_stream_exposes_sse_server_error_request_id(self):
        request_id = "2121cd16-460a-48f0-8214-558a61e6f939"
        backend = FakeCodexImageBackend([
            {"type": "response.image_generation_call.generating"},
            {
                "type": "error",
                "error": {
                    "type": "server_error",
                    "code": "server_error",
                    "message": (
                        "An error occurred while processing your request. "
                        f"Please include the request ID {request_id} in your message."
                    ),
                },
            },
            {"type": "response.failed", "response": {"status": "failed"}},
        ])

        with self.assertRaises(ImageGenerationError) as caught:
            list(stream_codex_image_outputs(
                backend,
                ConversationRequest(
                    prompt="draw a poster",
                    model="plus-codex-gpt-image-2",
                    size="2160x3840",
                    quality="high",
                ),
            ))

        self.assertEqual(caught.exception.code, "server_error")
        self.assertEqual(caught.exception.stage, "codex_image_tool")
        self.assertEqual(caught.exception.reason, "Codex 上游图片工具返回错误，没有产出图片资产")
        self.assertEqual(caught.exception.upstream_error_type, "server_error")
        self.assertEqual(caught.exception.upstream_request_id, request_id)
        self.assertEqual(backend.calls[0]["size"], "2160x3840")
        self.assertEqual(backend.calls[0]["quality"], "high")


if __name__ == "__main__":
    unittest.main()
