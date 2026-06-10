from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import unittest
from unittest import mock

import services.proxy_service as proxy_service_module


@contextmanager
def patched_proxy_config(
    *,
    global_proxy: str = "",
    proxy_groups: list[dict] | None = None,
    account_groups: list[dict] | None = None,
    profiles: list[dict] | None = None,
):
    proxy_groups_by_id = {str(item.get("id")): item for item in proxy_groups or []}
    account_groups_by_id = {str(item.get("id")): item for item in account_groups or []}
    profiles_by_id = {str(item.get("id")): item for item in profiles or []}

    def get_proxy_group(group_id):
        item = proxy_groups_by_id.get(str(group_id or "").strip())
        return deepcopy(item) if item is not None else None

    def get_account_group(group_id):
        item = account_groups_by_id.get(str(group_id or "").strip())
        return deepcopy(item) if item is not None else None

    def get_proxy_profile(profile_id):
        item = profiles_by_id.get(str(profile_id or "").strip())
        return deepcopy(item) if item is not None else None

    with (
        mock.patch.object(proxy_service_module.config, "get_proxy_settings", return_value=global_proxy),
        mock.patch.object(proxy_service_module.config, "get_proxy_group", side_effect=get_proxy_group),
        mock.patch.object(proxy_service_module.config, "get_account_group", side_effect=get_account_group),
        mock.patch.object(proxy_service_module.config, "get_proxy_profile", side_effect=get_proxy_profile),
    ):
        yield


class ProxyServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        proxy_service_module._proxy_group_indexes.clear()

    def test_account_direct_disables_all_proxy_fallbacks(self):
        with patched_proxy_config(
            global_proxy="http://global.example.test:7890",
            proxy_groups=[{"id": "pool", "enabled": True, "nodes": [{"url": "http://pool.example.test:7890"}]}],
            account_groups=[{"id": "ms", "enabled": True, "proxy_group_id": "pool"}],
        ):
            resolved = proxy_service_module.resolve_proxy({"proxy": "direct", "group_id": "ms"})

        self.assertEqual(resolved, "")

    def test_account_custom_proxy_beats_group_and_global(self):
        with patched_proxy_config(
            global_proxy="http://global.example.test:7890",
            proxy_groups=[{"id": "pool", "enabled": True, "nodes": [{"url": "http://pool.example.test:7890"}]}],
            account_groups=[{"id": "ms", "enabled": True, "proxy_group_id": "pool"}],
        ):
            resolved = proxy_service_module.resolve_proxy(
                {"proxy": "http://account.example.test:7890", "group_id": "ms"}
            )

        self.assertEqual(resolved, "http://account.example.test:7890")

    def test_account_proxy_group_beats_account_group_and_global(self):
        with patched_proxy_config(
            global_proxy="http://global.example.test:7890",
            proxy_groups=[
                {"id": "account-pool", "enabled": True, "nodes": [{"url": "http://account-pool.example.test:7890"}]},
                {"id": "group-pool", "enabled": True, "nodes": [{"url": "http://group-pool.example.test:7890"}]},
            ],
            account_groups=[{"id": "ms", "enabled": True, "proxy_group_id": "group-pool"}],
        ):
            resolved = proxy_service_module.resolve_proxy({"proxy": "group:account-pool", "group_id": "ms"})

        self.assertEqual(resolved, "http://account-pool.example.test:7890")

    def test_missing_account_proxy_group_falls_back_to_account_group(self):
        with patched_proxy_config(
            global_proxy="http://global.example.test:7890",
            proxy_groups=[{"id": "group-pool", "enabled": True, "nodes": [{"url": "http://group-pool.example.test:7890"}]}],
            account_groups=[{"id": "ms", "enabled": True, "proxy_group_id": "group-pool"}],
        ):
            resolved = proxy_service_module.resolve_proxy({"proxy": "group:missing", "group_id": "ms"})

        self.assertEqual(resolved, "http://group-pool.example.test:7890")

    def test_disabled_account_group_falls_back_to_global_proxy(self):
        with patched_proxy_config(
            global_proxy="http://global.example.test:7890",
            proxy_groups=[{"id": "group-pool", "enabled": True, "nodes": [{"url": "http://group-pool.example.test:7890"}]}],
            account_groups=[{"id": "ms", "enabled": False, "proxy_group_id": "group-pool"}],
        ):
            resolved = proxy_service_module.resolve_proxy({"group_id": "ms"})

        self.assertEqual(resolved, "http://global.example.test:7890")

    def test_proxy_group_round_robin_skips_disabled_and_cooldown_nodes(self):
        future = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        with patched_proxy_config(
            proxy_groups=[
                {
                    "id": "pool",
                    "enabled": True,
                    "nodes": [
                        {"id": "disabled", "enabled": False, "url": "http://disabled.example.test:7890"},
                        {"id": "cooldown", "enabled": True, "url": "http://cooldown.example.test:7890", "cooldown_until": future},
                        {"id": "node-a", "enabled": True, "url": "http://a.example.test:7890"},
                        {"id": "node-b", "enabled": True, "url": "http://b.example.test:7890"},
                    ],
                }
            ]
        ):
            first = proxy_service_module.select_proxy_group_url("pool")
            second = proxy_service_module.select_proxy_group_url("pool")
            third = proxy_service_module.select_proxy_group_url("pool")

        self.assertEqual(first, "http://a.example.test:7890")
        self.assertEqual(second, "http://b.example.test:7890")
        self.assertEqual(third, "http://a.example.test:7890")

    def test_legacy_profile_reference_still_resolves_for_compatibility(self):
        with patched_proxy_config(
            profiles=[
                {
                    "id": "legacy",
                    "enabled": True,
                    "proxy": "http://legacy.example.test:7890",
                }
            ]
        ):
            resolved = proxy_service_module.resolve_proxy({"proxy": "profile:legacy"})

        self.assertEqual(resolved, "http://legacy.example.test:7890")


if __name__ == "__main__":
    unittest.main()
