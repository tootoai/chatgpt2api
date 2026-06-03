from __future__ import annotations

import os
import unittest
from unittest import mock

os.environ.setdefault("CHATGPT2API_AUTH_KEY", "test-auth")

from services.log_service import LoggedCall
from services.protocol.conversation import ImageGenerationError


class LoggedCallImageContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_image_error_context_is_persisted_in_call_log_detail(self) -> None:
        def handler():
            error = ImageGenerationError("poll timed out", account_email="image@example.test")
            error.conversation_id = "conv-1"
            error.upstream_message_len = 42
            error.upstream_message_preview = "upstream returned text but no generated image asset"
            error.upstream_message_truncated = False
            error.tool_invoked = False
            error.turn_use_case = "image gen"
            error.blocked = False
            error.terminal_message = False
            raise error

        call = LoggedCall(
            {"id": "key-1", "name": "Key", "role": "admin"},
            "/v1/images/edits",
            "gpt-image-2",
            "image edit",
        )
        with mock.patch("services.log_service.log_service.add") as add_log:
            response = await call.run(handler)

        self.assertEqual(response.status_code, 502)
        detail = add_log.call_args.args[2]
        self.assertEqual(detail["conversation_id"], "conv-1")
        self.assertEqual(
            detail["upstream_message_preview"],
            "upstream returned text but no generated image asset",
        )
        self.assertEqual(detail["upstream_message_len"], 42)
        self.assertFalse(detail["upstream_message_truncated"])
        self.assertFalse(detail["tool_invoked"])
        self.assertEqual(detail["turn_use_case"], "image gen")
        self.assertFalse(detail["blocked"])
        self.assertFalse(detail["terminal_message"])
        self.assertEqual(detail["account_email"], "image@example.test")


if __name__ == "__main__":
    unittest.main()
