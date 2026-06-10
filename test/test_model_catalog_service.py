from __future__ import annotations

import unittest
from unittest import mock

import services.model_catalog_service as module


class ModelCatalogServiceTests(unittest.TestCase):
    def test_configured_models_take_priority(self):
        settings = {
            "model_catalog": {
                "chat_models": ["custom-chat", "custom-chat", ""],
                "image_api_models": ["custom-image"],
            },
            "image_generation": {
                "model_options": [],
                "supported_models": ["ignored-image"],
            },
        }

        with (
            mock.patch.object(module.config, "get", return_value=settings),
            mock.patch.object(module.account_service, "list_accounts") as list_accounts,
        ):
            payload = module.get_model_catalog()

        self.assertEqual(payload["chat_models"], ["custom-chat"])
        self.assertEqual(payload["image_models"], ["custom-image"])
        self.assertEqual(payload["source"], {"chat": "config", "image": "config"})
        list_accounts.assert_not_called()

    def test_codex_accounts_enable_prefixed_image_models(self):
        with (
            mock.patch.object(module.config, "get", return_value={}),
            mock.patch.object(
                module.account_service,
                "list_accounts",
                return_value=[
                    {"source_type": "web", "type": "free", "status": "正常", "quota": 1},
                    {"source_type": "codex", "type": "team", "status": "正常", "quota": 1},
                ],
            ),
        ):
            payload = module.get_model_catalog()

        self.assertEqual(payload["source"]["chat"], "fallback")
        self.assertEqual(payload["source"]["image"], "accounts")
        self.assertIn("gpt-image-2", payload["image_models"])
        self.assertIn("codex-gpt-image-2", payload["image_models"])
        self.assertIn("team-codex-gpt-image-2", payload["image_models"])

    def test_unavailable_codex_accounts_do_not_enable_codex_image_models(self):
        with (
            mock.patch.object(module.config, "get", return_value={}),
            mock.patch.object(
                module.account_service,
                "list_accounts",
                return_value=[
                    {"source_type": "codex", "type": "pro", "status": "禁用", "quota": 99},
                    {"source_type": "codex", "type": "team", "status": "限流", "quota": 0},
                ],
            ),
        ):
            payload = module.get_model_catalog()

        self.assertEqual(payload["source"]["image"], "fallback")
        self.assertEqual(payload["image_models"], ["gpt-image-2"])

    def test_falls_back_without_config_or_accounts(self):
        with (
            mock.patch.object(module.config, "get", return_value={}),
            mock.patch.object(module.account_service, "list_accounts", return_value=[]),
        ):
            payload = module.get_model_catalog()

        self.assertEqual(payload["source"], {"chat": "fallback", "image": "fallback"})
        self.assertEqual(payload["chat_models"], module.FALLBACK_CHAT_MODELS)
        self.assertEqual(payload["image_models"], ["gpt-image-2"])
        self.assertEqual(payload["all_models"], [*module.FALLBACK_CHAT_MODELS, "gpt-image-2"])


if __name__ == "__main__":
    unittest.main()
