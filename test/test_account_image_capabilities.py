from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("CHATGPT2API_AUTH_KEY", "test-auth")

from services.account_service import AccountService
from services.auth_service import AuthService
from services.config import config
from services.openai_backend_api import ImagePollTimeoutError
from services.storage.json_storage import JSONStorageBackend
from services.protocol import conversation as conversation_protocol
from services.protocol.conversation import ConversationRequest, ImageGenerationError
from utils.helper import anonymize_token, split_image_model


class AccountCapabilityTests(unittest.TestCase):
    def test_unknown_quota_accounts_are_available_only_when_not_throttled(self) -> None:
        self.assertFalse(
            AccountService._is_image_account_available(
                {"status": "限流", "image_quota_unknown": True, "quota": 0}
            )
        )
        self.assertTrue(
            AccountService._is_image_account_available(
                {"status": "正常", "image_quota_unknown": True, "quota": 0}
            )
        )

    def test_prolite_variants_are_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AccountService(JSONStorageBackend(Path(tmp_dir) / "accounts.json"))
            self.assertEqual(service._normalize_account_type("prolite"), "ProLite")
            self.assertEqual(service._normalize_account_type("pro_lite"), "ProLite")

    def test_search_account_type_ignores_unrelated_scalar_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AccountService(JSONStorageBackend(Path(tmp_dir) / "accounts.json"))
            self.assertIsNone(
                service._search_account_type(
                    {
                        "amr": ["pwd", "otp", "mfa"],
                        "chatgpt_compute_residency": "no_constraint",
                        "chatgpt_data_residency": "no_constraint",
                        "user_id": "user-I52GFfLGFM0dokFk2dBiKEBn",
                    }
                )
            )

    def test_mark_image_result_does_not_consume_unknown_quota(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AccountService(JSONStorageBackend(Path(tmp_dir) / "accounts.json"))
            service.add_accounts(["token-1"])
            service.update_account(
                "token-1",
                {
                    "status": "正常",
                    "quota": 0,
                    "image_quota_unknown": True,
                },
            )

            updated = service.mark_image_result("token-1", success=True)

            self.assertIsNotNone(updated)
            self.assertEqual(updated["quota"], 0)
            self.assertEqual(updated["status"], "正常")
            self.assertTrue(updated["image_quota_unknown"])

    def test_split_image_model_supports_plan_type_prefix(self) -> None:
        self.assertEqual(split_image_model("gpt-image-2"), (None, "gpt-image-2"))
        self.assertEqual(split_image_model("plus-codex-gpt-image-2"), ("plus", "codex-gpt-image-2"))
        self.assertEqual(split_image_model("team-codex-gpt-image-2"), ("team", "codex-gpt-image-2"))
        self.assertEqual(split_image_model("pro-codex-gpt-image-2"), ("pro", "codex-gpt-image-2"))
        self.assertEqual(split_image_model("plus-gpt-image-2"), (None, None))
        self.assertEqual(split_image_model("unknown-image-model"), (None, None))

    def test_get_available_access_token_filters_by_plan_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AccountService(JSONStorageBackend(Path(tmp_dir) / "accounts.json"))
            service.add_account_items(
                [
                    {"access_token": "token-plus", "type": "Plus", "status": "正常", "quota": 3},
                    {"access_token": "token-pro", "type": "Pro", "status": "正常", "quota": 3},
                ]
            )

            service.fetch_remote_info = lambda access_token, event="fetch_remote_info": service.get_account(access_token)

            plus_token = service.get_available_access_token(plan_type="plus")
            pro_token = service.get_available_access_token(plan_type="pro")
            service.release_image_slot(plus_token)
            service.release_image_slot(pro_token)

            self.assertEqual(plus_token, "token-plus")
            self.assertEqual(pro_token, "token-pro")

    def test_get_available_access_token_stops_after_transport_error_burst(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AccountService(JSONStorageBackend(Path(tmp_dir) / "accounts.json"))
            service.add_account_items([
                {"access_token": f"token-{index}", "status": "正常", "quota": 3}
                for index in range(10)
            ])
            calls = []

            def fail_transport(access_token: str, event: str = "fetch_remote_info") -> dict:
                calls.append(access_token)
                raise RuntimeError("Recv failure: Connection was reset")

            service.fetch_remote_info = fail_transport

            with self.assertRaisesRegex(RuntimeError, "temporarily unavailable"):
                service.get_available_access_token()

            self.assertEqual(len(calls), service._IMAGE_SELECTION_TRANSPORT_ERROR_LIMIT)
            self.assertEqual(service._image_inflight, {})

    def test_concurrent_image_selection_does_not_overbook_or_leak_slots(self) -> None:
        old_concurrency = config.data.get("image_account_concurrency")
        config.data["image_account_concurrency"] = 2
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                service = AccountService(JSONStorageBackend(Path(tmp_dir) / "accounts.json"))
                service.add_account_items([
                    {"access_token": f"token-{index}", "status": "正常", "quota": 1000}
                    for index in range(4)
                ])
                service.fetch_remote_info = lambda access_token, event="fetch_remote_info": service.get_account(
                    access_token
                )
                errors: list[str] = []
                max_seen: dict[str, int] = {}
                completed = 0
                guard = threading.Lock()

                def worker() -> None:
                    nonlocal completed
                    try:
                        for _ in range(20):
                            access_token = service.get_available_access_token()
                            try:
                                with service._lock:
                                    snapshot = dict(service._image_inflight)
                                with guard:
                                    for token, count in snapshot.items():
                                        max_seen[token] = max(max_seen.get(token, 0), count)
                                        if count > 2:
                                            errors.append(f"overbooked {token}: {count}")
                                    completed += 1
                                time.sleep(0.001)
                            finally:
                                service.mark_image_result(access_token, success=True)
                    except Exception as exc:
                        with guard:
                            errors.append(repr(exc))

                threads = [threading.Thread(target=worker) for _ in range(24)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=5)

                self.assertEqual([thread for thread in threads if thread.is_alive()], [])
                self.assertEqual(errors, [])
                self.assertEqual(completed, 480)
                self.assertEqual(service._image_inflight, {})
                self.assertLessEqual(max(max_seen.values(), default=0), 2)
        finally:
            if old_concurrency is None:
                config.data.pop("image_account_concurrency", None)
            else:
                config.data["image_account_concurrency"] = old_concurrency

    def test_concurrent_transport_error_bursts_do_not_leak_slots(self) -> None:
        old_concurrency = config.data.get("image_account_concurrency")
        config.data["image_account_concurrency"] = 2
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                service = AccountService(JSONStorageBackend(Path(tmp_dir) / "accounts.json"))
                service.add_account_items([
                    {"access_token": f"token-{index}", "status": "正常", "quota": 1000}
                    for index in range(12)
                ])
                calls: list[str] = []
                errors: list[str] = []
                guard = threading.Lock()

                def fail_transport(access_token: str, event: str = "fetch_remote_info") -> dict:
                    with guard:
                        calls.append(access_token)
                    raise RuntimeError("Recv failure: Connection was reset")

                def worker() -> None:
                    try:
                        service.get_available_access_token()
                        with guard:
                            errors.append("unexpected success")
                    except RuntimeError as exc:
                        if "temporarily unavailable" not in str(exc):
                            with guard:
                                errors.append(repr(exc))
                    except Exception as exc:
                        with guard:
                            errors.append(repr(exc))

                service.fetch_remote_info = fail_transport
                threads = [threading.Thread(target=worker) for _ in range(24)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=5)

                self.assertEqual([thread for thread in threads if thread.is_alive()], [])
                self.assertEqual(errors, [])
                self.assertLessEqual(len(calls), 24 * service._IMAGE_SELECTION_TRANSPORT_ERROR_LIMIT)
                self.assertEqual(service._image_inflight, {})
        finally:
            if old_concurrency is None:
                config.data.pop("image_account_concurrency", None)
            else:
                config.data["image_account_concurrency"] = old_concurrency

    def test_image_poll_timeout_releases_image_slot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AccountService(JSONStorageBackend(Path(tmp_dir) / "accounts.json"))
            service.add_account_items([
                {"access_token": "token-1", "status": "正常", "quota": 3, "email": "image@example.test"}
            ])
            service.fetch_remote_info = lambda access_token, event="fetch_remote_info": service.get_account(access_token)

            def fail_poll(*_args, **_kwargs):
                raise ImagePollTimeoutError("poll timed out")

            with (
                mock.patch.object(conversation_protocol, "account_service", service),
                mock.patch.object(conversation_protocol, "OpenAIBackendAPI", lambda access_token="": object()),
                mock.patch.object(conversation_protocol, "stream_image_outputs", fail_poll),
            ):
                with self.assertRaises(ImageGenerationError):
                    list(conversation_protocol.stream_image_outputs_with_pool(
                        ConversationRequest(prompt="draw", model="gpt-image-2")
                    ))

            self.assertEqual(service._image_inflight, {})
            self.assertEqual(service.get_account("token-1")["fail"], 1)


class TokenLogTests(unittest.TestCase):
    def test_anonymize_token_hides_raw_value(self) -> None:
        token = "super-secret-token"
        token_ref = anonymize_token(token)

        self.assertTrue(token_ref.startswith("token:"))
        self.assertNotIn(token, token_ref)


class AuthServiceTests(unittest.TestCase):
    def test_create_authenticate_disable_and_delete_user_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AuthService(JSONStorageBackend(Path(tmp_dir) / "accounts.json", Path(tmp_dir) / "auth_keys.json"))

            item, raw_key = service.create_key(role="user", name="Alice")

            self.assertEqual(item["role"], "user")
            self.assertEqual(item["name"], "Alice")
            self.assertTrue(item["enabled"])
            self.assertTrue(raw_key.startswith("sk-"))

            authed = service.authenticate(raw_key)
            self.assertIsNotNone(authed)
            self.assertEqual(authed["id"], item["id"])
            self.assertEqual(authed["role"], "user")
            self.assertIsNotNone(authed["last_used_at"])

            updated = service.update_key(item["id"], {"enabled": False}, role="user")
            self.assertIsNotNone(updated)
            self.assertFalse(updated["enabled"])
            self.assertIsNone(service.authenticate(raw_key))

            self.assertTrue(service.delete_key(item["id"], role="user"))
            self.assertFalse(service.delete_key(item["id"], role="user"))
            self.assertEqual(service.list_keys(role="user"), [])

    def test_authenticate_ignores_last_used_save_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AuthService(JSONStorageBackend(Path(tmp_dir) / "accounts.json", Path(tmp_dir) / "auth_keys.json"))
            item, raw_key = service.create_key(role="user", name="Alice")

            def fail_save() -> None:
                raise OSError("disk unavailable")

            service._save = fail_save

            authed = service.authenticate(raw_key)

            self.assertIsNotNone(authed)
            self.assertEqual(authed["id"], item["id"])
            self.assertIsNotNone(authed["last_used_at"])

    def test_update_user_key_replaces_raw_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AuthService(JSONStorageBackend(Path(tmp_dir) / "accounts.json", Path(tmp_dir) / "auth_keys.json"))
            item, raw_key = service.create_key(role="user", name="Alice")

            updated = service.update_key(item["id"], {"key": "sk-user-custom-key"}, role="user")

            self.assertIsNotNone(updated)
            self.assertIsNone(service.authenticate(raw_key))

            authed = service.authenticate("sk-user-custom-key")
            self.assertIsNotNone(authed)
            self.assertEqual(authed["id"], item["id"])

    def test_user_key_name_must_be_unique(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AuthService(JSONStorageBackend(Path(tmp_dir) / "accounts.json", Path(tmp_dir) / "auth_keys.json"))
            first, _ = service.create_key(role="user", name="Alice")
            second, _ = service.create_key(role="user", name="Bob")

            with self.assertRaisesRegex(ValueError, "这个名称已经在使用中了"):
                service.create_key(role="user", name="Alice")

            with self.assertRaisesRegex(ValueError, "这个名称已经在使用中了"):
                service.update_key(second["id"], {"name": "Alice"}, role="user")

            updated = service.update_key(first["id"], {"name": "Alice"}, role="user")
            self.assertIsNotNone(updated)
            self.assertEqual(updated["name"], "Alice")


if __name__ == "__main__":
    unittest.main()
