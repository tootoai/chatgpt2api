from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

os.environ.setdefault("CHATGPT2API_AUTH_KEY", "chatgpt2api")

import services.account_service as account_service_module
import services.protocol.conversation as conversation_module
from services.account_service import AccountService
from services.auth_service import AuthService
from services.openai_backend_api import ImagePollTimeoutError
from services.protocol.conversation import ConversationRequest, ImageGenerationError, ImageOutput
from services.storage.json_storage import JSONStorageBackend
from utils.helper import anonymize_token


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

    def test_single_account_slot_is_exclusive(self) -> None:
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

            with (
                mock.patch.object(
                    account_service_module.config.__class__,
                    "image_account_concurrency",
                    new_callable=mock.PropertyMock,
                    return_value=1,
                ),
                mock.patch.object(
                    account_service_module.config.__class__,
                    "image_slot_wait_timeout_secs",
                    new_callable=mock.PropertyMock,
                    return_value=0.01,
                ),
            ):
                self.assertEqual(service._acquire_next_candidate_token(), "token-1")
                with self.assertRaisesRegex(RuntimeError, "busy"):
                    service._acquire_next_candidate_token()
                service.release_image_slot("token-1")
                self.assertEqual(service._acquire_next_candidate_token(), "token-1")

    def test_image_account_cooldown_hides_account_until_expired(self) -> None:
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

            service.cool_down_image_account("token-1", 1, "test")

            with self.assertRaisesRegex(RuntimeError, "cooling down"):
                service._acquire_next_candidate_token()

            account = service.get_account("token-1")
            self.assertIsNotNone(account)
            self.assertEqual(account["image_runtime_status"], "冷却中")
            self.assertEqual(account["image_cooldown_reason"], "test")
            self.assertGreater(account["image_cooldown_remaining_secs"], 0)

            service.update_account(
                "token-1",
                {"image_cooldown_until": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()},
            )
            self.assertEqual(service._acquire_next_candidate_token(), "token-1")
            account = service.get_account("token-1")
            self.assertIsNotNone(account)
            self.assertEqual(account["image_runtime_status"], "生成中")
            self.assertEqual(account["image_cooldown_remaining_secs"], 0)

    def test_account_runtime_status_reports_busy_and_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AccountService(JSONStorageBackend(Path(tmp_dir) / "accounts.json"))
            service.add_account_items([
                {"access_token": "token-busy", "image_quota_unknown": True},
                {"access_token": "token-limited", "status": "限流", "quota": 0},
            ])

            with mock.patch.object(
                account_service_module.config.__class__,
                "image_account_concurrency",
                new_callable=mock.PropertyMock,
                return_value=1,
            ):
                self.assertEqual(service._acquire_next_candidate_token(), "token-busy")
                accounts = {item["access_token"]: item for item in service.list_accounts()}

            self.assertEqual(accounts["token-busy"]["image_runtime_status"], "生成中")
            self.assertEqual(accounts["token-busy"]["image_inflight"], 1)
            self.assertEqual(accounts["token-busy"]["image_capacity"], 0)
            self.assertEqual(accounts["token-limited"]["image_runtime_status"], "不可用")

    def test_excluded_tokens_are_skipped_when_selecting_image_account(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AccountService(JSONStorageBackend(Path(tmp_dir) / "accounts.json"))
            service.add_account_items([
                {"access_token": "token-a", "image_quota_unknown": True},
                {"access_token": "token-b", "image_quota_unknown": True},
            ])

            self.assertEqual(service.get_available_access_token(excluded_tokens={"token-a"}), "token-b")

    def test_image_pool_stats_reports_busy_and_cooldown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AccountService(JSONStorageBackend(Path(tmp_dir) / "accounts.json"))
            service.add_account_items([
                {"access_token": "token-a", "image_quota_unknown": True},
                {"access_token": "token-b", "image_quota_unknown": True},
            ])

            with mock.patch.object(
                account_service_module.config.__class__,
                "image_account_concurrency",
                new_callable=mock.PropertyMock,
                return_value=1,
            ):
                service._acquire_next_candidate_token()
                service.cool_down_image_account("token-b", 60, "test")
                stats = service.get_image_pool_stats()

            self.assertEqual(stats["total_busy"], 1)
            self.assertEqual(stats["total_inflight"], 1)
            self.assertEqual(stats["total_cooldown"], 1)
            self.assertEqual(stats["cooldown_reasons"], {"test": 1})

    def test_non_stream_image_poll_timeout_retries_next_account_after_progress(self) -> None:
        class Pool:
            def __init__(self) -> None:
                self.tokens = ["token-a", "token-b"]
                self.index = 0
                self.failed: list[tuple[str, bool]] = []
                self.cooldowns: list[tuple[str, int, str]] = []

            def get_available_access_token(self, excluded_tokens=None) -> str:
                excluded = set(excluded_tokens or set())
                while self.index < len(self.tokens):
                    token = self.tokens[self.index]
                    self.index += 1
                    if token not in excluded:
                        return token
                raise RuntimeError("no available image quota")

            def mark_image_result(self, token: str, success: bool) -> None:
                self.failed.append((token, success))

            def cool_down_image_account(self, token: str, seconds: int, reason: str) -> None:
                self.cooldowns.append((token, seconds, reason))

            def resolve_access_token(self, token: str) -> str:
                return token

        pool = Pool()

        def fake_stream(_backend, request, index=1, total=1):
            token = _backend.access_token
            if token == "token-a":
                yield ImageOutput(kind="progress", model=request.model, index=index, total=total)
                raise ImagePollTimeoutError("timed out")
            yield ImageOutput(
                kind="result",
                model=request.model,
                index=index,
                total=total,
                data=[{"b64_json": "ok"}],
            )

        with (
            mock.patch.object(conversation_module, "account_service", pool),
            mock.patch.object(conversation_module, "stream_image_outputs", side_effect=fake_stream),
            mock.patch.object(
                conversation_module.config.__class__,
                "image_account_slow_cooldown_secs",
                new_callable=mock.PropertyMock,
                return_value=600,
            ),
        ):
            outputs = list(conversation_module.stream_image_outputs_with_pool(
                ConversationRequest(model="gpt-image-2", prompt="cat", stream=False)
            ))

        self.assertEqual([output.kind for output in outputs], ["progress", "result"])
        self.assertEqual(pool.failed, [("token-a", False), ("token-b", True)])
        self.assertEqual(pool.cooldowns, [("token-a", 600, "image_poll_timeout")])

    def test_stream_image_poll_timeout_does_not_retry_after_progress(self) -> None:
        class Pool:
            def get_available_access_token(self, excluded_tokens=None) -> str:
                return "token-a"

            def mark_image_result(self, token: str, success: bool) -> None:
                return None

            def cool_down_image_account(self, token: str, seconds: int, reason: str) -> None:
                return None

            def resolve_access_token(self, token: str) -> str:
                return token

        def fake_stream(_backend, request, index=1, total=1):
            yield ImageOutput(kind="progress", model=request.model, index=index, total=total)
            raise ImagePollTimeoutError("timed out")

        with (
            mock.patch.object(conversation_module, "account_service", Pool()),
            mock.patch.object(conversation_module, "stream_image_outputs", side_effect=fake_stream),
            mock.patch.object(
                conversation_module.config.__class__,
                "image_account_slow_cooldown_secs",
                new_callable=mock.PropertyMock,
                return_value=600,
            ),
        ):
            outputs = conversation_module.stream_image_outputs_with_pool(
                ConversationRequest(model="gpt-image-2", prompt="cat", stream=True)
            )
            first = next(outputs)
            self.assertEqual(first.kind, "progress")
            with self.assertRaises(ImageGenerationError):
                next(outputs)


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
