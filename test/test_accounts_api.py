from __future__ import annotations

import os
import unittest
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

TEST_AUTH_KEY = "chatgpt2api"
os.environ["CHATGPT2API_AUTH_KEY"] = TEST_AUTH_KEY

import api.accounts as accounts_module


AUTH_HEADERS = {"Authorization": f"Bearer {TEST_AUTH_KEY}"}


class FakeAccountService:
    def __init__(self) -> None:
        self.page_calls = []
        self.list_calls = 0
        self.add_accounts_calls = []
        self.add_account_items_calls = []
        self.refresh_calls = []
        self.update_accounts_calls = []
        self.accounts = {
            "token-a": {"access_token": "token-a", "email": "a@example.test"},
            "token-b": {"access_token": "token-b", "email": "b@example.test"},
        }

    def list_accounts_page(self, **kwargs):
        self.page_calls.append(kwargs)
        return {
            "items": [self.accounts["token-b"]],
            "total": 7,
            "all_total": 12,
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
        }

    def list_accounts(self):
        self.list_calls += 1
        return list(self.accounts.values())

    def add_accounts(self, tokens, source_type="web", include_items=True):
        self.add_accounts_calls.append(
            {"tokens": list(tokens), "source_type": source_type, "include_items": include_items}
        )
        return {"added": len(tokens), "skipped": 0}

    def add_account_items(self, items, include_items=True):
        self.add_account_items_calls.append({"items": list(items), "include_items": include_items})
        return {"added": len(items), "skipped": 0}

    def refresh_accounts(self, tokens, progress_id=None, include_items=True):
        self.refresh_calls.append(
            {"tokens": list(tokens), "progress_id": progress_id, "include_items": include_items}
        )
        return {"refreshed": len(tokens), "errors": []}

    def account_group_counts(self):
        return {"ms": 2}

    def tokens_for_group(self, group_id):
        return ["token-a"] if group_id == "ms" else []

    def get_account(self, token):
        return self.accounts.get(token)

    def update_accounts(self, access_tokens, updates, quiet=False, include_items=True):
        self.update_accounts_calls.append(
            {
                "access_tokens": list(access_tokens),
                "updates": dict(updates),
                "quiet": quiet,
                "include_items": include_items,
            }
        )
        for token in access_tokens:
            if token in self.accounts:
                self.accounts[token] = {**self.accounts[token], **updates}
        return {"updated": sum(1 for token in access_tokens if token in self.accounts)}


class AccountsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(accounts_module.create_router())
        self.client = TestClient(app)

    def test_paginated_account_list_forwards_server_side_filters(self):
        fake = FakeAccountService()
        with mock.patch.object(accounts_module, "account_service", fake):
            response = self.client.get(
                "/api/accounts?page=2&page_size=50&keyword=duck&status=normal&group_id=ms",
                headers=AUTH_HEADERS,
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 7)
        self.assertEqual(response.json()["all_total"], 12)
        self.assertEqual(
            fake.page_calls,
            [
                {
                    "page": 2,
                    "page_size": 50,
                    "keyword": "duck",
                    "status": "normal",
                    "group_id": "ms",
                }
            ],
        )
        self.assertEqual(fake.list_calls, 0)

    def test_create_accounts_uses_lightweight_add_and_refresh(self):
        fake = FakeAccountService()
        with mock.patch.object(accounts_module, "account_service", fake):
            response = self.client.post(
                "/api/accounts",
                headers=AUTH_HEADERS,
                json={"tokens": ["token-a"]},
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["added"], 1)
        self.assertEqual(payload["refreshed"], 1)
        self.assertEqual(payload["items"], [fake.accounts["token-a"]])
        self.assertEqual(
            fake.add_accounts_calls,
            [{"tokens": ["token-a"], "source_type": "web", "include_items": False}],
        )
        self.assertEqual(
            fake.refresh_calls,
            [{"tokens": ["token-a"], "progress_id": None, "include_items": False}],
        )

    def test_account_groups_include_server_side_account_counts(self):
        fake = FakeAccountService()
        with (
            mock.patch.object(accounts_module, "account_service", fake),
            mock.patch.object(
                accounts_module.config,
                "get_account_groups",
                return_value=[{"id": "ms", "name": "Microsoft"}, {"id": "codex", "name": "Codex"}],
            ),
            mock.patch.object(accounts_module.config, "get_proxy_groups", return_value=[]),
        ):
            response = self.client.get("/api/account-groups", headers=AUTH_HEADERS)

        self.assertEqual(response.status_code, 200, response.text)
        groups = response.json()["groups"]
        self.assertEqual(groups[0]["account_count"], 2)
        self.assertEqual(groups[1]["account_count"], 0)

    def test_create_account_group_rejects_missing_proxy_group(self):
        with (
            mock.patch.object(accounts_module.config, "get_account_groups", return_value=[]),
            mock.patch.object(accounts_module.config, "get_proxy_group", return_value=None),
            mock.patch.object(accounts_module.config, "update") as update_mock,
        ):
            response = self.client.post(
                "/api/account-groups",
                headers=AUTH_HEADERS,
                json={"id": "ms", "name": "Microsoft", "proxy_group_id": "missing"},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["detail"]["error"], "proxy group not found")
        update_mock.assert_not_called()

    def test_create_account_group_rejects_duplicate_name(self):
        with (
            mock.patch.object(
                accounts_module.config,
                "get_account_groups",
                return_value=[{"id": "ms", "name": "Microsoft", "proxy_group_id": "", "enabled": True, "notes": ""}],
            ),
            mock.patch.object(accounts_module.config, "get_proxy_group", return_value=None),
            mock.patch.object(accounts_module.config, "update") as update_mock,
        ):
            response = self.client.post(
                "/api/account-groups",
                headers=AUTH_HEADERS,
                json={"id": "ms-secondary", "name": " microsoft "},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["detail"]["error"], "account group name already exists")
        update_mock.assert_not_called()

    def test_delete_account_group_clears_bound_accounts(self):
        fake = FakeAccountService()

        def fake_update(data):
            return {"account_groups": list(data.get("account_groups", [])), "proxy_groups": []}

        with (
            mock.patch.object(accounts_module, "account_service", fake),
            mock.patch.object(
                accounts_module.config,
                "get_account_groups",
                return_value=[{"id": "ms", "name": "Microsoft", "proxy_group_id": "", "enabled": True, "notes": ""}],
            ),
            mock.patch.object(accounts_module.config, "get_proxy_groups", return_value=[]),
            mock.patch.object(accounts_module.config, "update", side_effect=fake_update),
        ):
            response = self.client.delete("/api/account-groups/ms", headers=AUTH_HEADERS)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["deleted"], "ms")
        self.assertEqual(response.json()["groups"], [])
        self.assertEqual(
            fake.update_accounts_calls,
            [
                {
                    "access_tokens": ["token-a"],
                    "updates": {"group_id": ""},
                    "quiet": True,
                    "include_items": False,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
