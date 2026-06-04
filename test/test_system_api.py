from __future__ import annotations

import io
import os
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

TEST_AUTH_KEY = "chatgpt2api"
os.environ["CHATGPT2API_AUTH_KEY"] = TEST_AUTH_KEY

import api.system as system_module
import services.image_service as image_service_module


AUTH_HEADERS = {"Authorization": f"Bearer {TEST_AUTH_KEY}"}


class FakeStorage:
    def get_backend_info(self):
        return {"type": "fake"}

    def health_check(self):
        return {"status": "healthy"}


class FakeAccountService:
    def get_stats(self):
        return {
            "total": 3,
            "cumulative_total": 5,
            "active": 2,
            "limited": 1,
            "abnormal": 0,
            "disabled": 0,
            "total_quota": 7,
            "unlimited_quota_count": 1,
            "total_success": 10,
            "total_fail": 2,
            "by_type": {"plus": 2, "free": 1},
        }


class FakeLogService:
    def __init__(self):
        self.calls = []
        self.queries = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        return [
            {
                "id": "log-success",
                "time": current_hour.strftime("%Y-%m-%d %H:%M:%S"),
                "type": "call",
                "summary": "success",
                "detail": {
                    "status": "success",
                    "endpoint": "/v1/images/generations",
                    "model": "gpt-image-2",
                    "duration_ms": 24000,
                },
            },
            {
                "id": "log-failed",
                "time": (current_hour + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"),
                "type": "call",
                "summary": "failed",
                "detail": {
                    "status": "failed",
                    "endpoint": "/v1/images/edits",
                    "model": "gpt-image-2",
                    "duration_ms": 32000,
                    "error_code": "upstream_text_reply",
                    "stage": "polling",
                    "reason": "upstream returned text",
                    "conversation_id": "conv-1",
                },
            },
        ]

    def query(self, **kwargs):
        self.queries.append(kwargs)
        return {
            "items": [],
            "total": 0,
            "limit": kwargs.get("limit", 0),
            "offset": kwargs.get("offset", 0),
            "has_more": False,
            "facets": {"statuses": {}, "endpoints": {}, "models": {}, "accounts": {}},
            "stats": {"total": 0, "success": 0, "failed": 0, "limited": 0, "image": 0, "text_reply": 0},
        }


class SystemApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(system_module.create_router("9.9.9-test"))
        self.client = TestClient(app)

    def test_auth_status_reports_invalid_without_401(self):
        response = self.client.get("/auth/status")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertFalse(payload["authenticated"])
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["version"], "9.9.9-test")

    def test_auth_status_reports_identity(self):
        response = self.client.get("/auth/status", headers=AUTH_HEADERS)

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["authenticated"])
        self.assertEqual(payload["role"], "admin")
        self.assertEqual(payload["subject_id"], "admin")
        self.assertEqual(payload["version"], "9.9.9-test")

    def test_dashboard_returns_frontend_summary(self):
        fake_logs = FakeLogService()
        fake_storage = FakeStorage()
        with (
            mock.patch("services.account_service.account_service", FakeAccountService()),
            mock.patch.object(system_module, "log_service", fake_logs),
            mock.patch.object(system_module.config, "get_storage_backend", return_value=fake_storage),
            mock.patch.object(system_module, "storage_stats", return_value={"image_count": 4, "image_size_mb": 12}),
        ):
            response = self.client.get("/api/dashboard?log_limit=50", headers=AUTH_HEADERS)

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["version"], "9.9.9-test")
        self.assertEqual(payload["accounts"]["active"], 2)
        self.assertEqual(payload["storage"]["backend"]["type"], "fake")
        self.assertEqual(payload["storage"]["images"]["image_count"], 4)
        self.assertEqual(payload["logs"]["total"], 2)
        self.assertEqual(payload["logs"]["success"], 1)
        self.assertEqual(payload["logs"]["failed"], 1)
        self.assertEqual(payload["logs"]["by_endpoint"]["/v1/images/edits"], 1)
        self.assertEqual(payload["logs"]["by_model"]["gpt-image-2"], 2)
        self.assertEqual(payload["logs"]["by_error_code"]["upstream_text_reply"], 1)
        self.assertEqual(payload["logs"]["recent_failures"][0]["conversation_id"], "conv-1")
        self.assertIn("trend", payload["logs"])
        self.assertIn("gpt-image-2", payload["logs"]["trend"]["model_requests"])
        self.assertIn("gpt-image-2", payload["logs"]["trend"]["model_total_times"])
        self.assertEqual(fake_logs.calls, [{"type": "call", "limit": 50}])

    def test_logs_endpoint_passes_server_side_filters(self):
        fake_logs = FakeLogService()
        with mock.patch.object(system_module, "log_service", fake_logs):
            response = self.client.get(
                "/api/logs?type=call&status=failed&endpoint=/v1/images&model=gpt-image-2"
                "&account=image@example.test&conversation_id=conv&search=upstream&limit=25&offset=50",
                headers=AUTH_HEADERS,
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["limit"], 25)
        self.assertEqual(payload["offset"], 50)
        self.assertEqual(
            fake_logs.queries,
            [
                {
                    "type": "call",
                    "start_date": "",
                    "end_date": "",
                    "status": "failed",
                    "endpoint": "/v1/images",
                    "model": "gpt-image-2",
                    "account": "image@example.test",
                    "conversation_id": "conv",
                    "search": "upstream",
                    "limit": 25,
                    "offset": 50,
                }
            ],
        )

    def test_runtime_logs_endpoint_passes_filters(self):
        expected = {
            "items": [
                {
                    "id": "runtime-1",
                    "time": "2026-06-04 15:30:00",
                    "level": "warning",
                    "message": "image upload failed",
                    "source": "memory",
                }
            ],
            "total": 1,
            "limit": 25,
            "sources": {"memory": True, "files": []},
        }
        with mock.patch.object(system_module, "list_runtime_logs", return_value=expected) as runtime_logs:
            response = self.client.get(
                "/api/runtime-logs?level=warning&search=image&source=memory&limit=25",
                headers=AUTH_HEADERS,
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), expected)
        runtime_logs.assert_called_once_with(
            level="warning",
            search="image",
            source="memory",
            limit=25,
        )

    def test_images_endpoint_passes_server_side_filters(self):
        with mock.patch.object(system_module, "list_images", return_value={"items": [], "total": 0}) as list_mock:
            response = self.client.get(
                "/api/images?start_date=2026-06-01&end_date=2026-06-03"
                "&media_type=image&tag=duck&search=hat&limit=24&offset=48",
                headers=AUTH_HEADERS,
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 0)
        list_mock.assert_called_once_with(
            "http://testserver",
            start_date="2026-06-01",
            end_date="2026-06-03",
            media_type="image",
            tag="duck",
            search="hat",
            limit=24,
            offset=48,
        )

    def test_image_list_filters_and_clamps_pagination(self):
        fake_items = [
            {
                "path": "2026/06/04/duck-a.png",
                "name": "duck-a.png",
                "date": "2026-06-04",
                "size": 100,
                "created_at": "2026-06-04 10:00:00",
                "storage": "local",
                "local": True,
                "webdav": False,
            },
            {
                "path": "2026/06/04/duck-b.png",
                "name": "duck-b.png",
                "date": "2026-06-04",
                "size": 200,
                "created_at": "2026-06-04 09:00:00",
                "storage": "local",
                "local": True,
                "webdav": False,
            },
            {
                "path": "2026/06/04/clip.mp4",
                "name": "clip.mp4",
                "date": "2026-06-04",
                "size": 300,
                "created_at": "2026-06-04 08:00:00",
                "storage": "local",
                "local": True,
                "webdav": False,
            },
        ]
        fake_tags = {
            "2026/06/04/duck-a.png": ["duck", "hat"],
            "2026/06/04/duck-b.png": ["duck"],
            "2026/06/04/clip.mp4": ["clip"],
        }

        with (
            mock.patch.object(image_service_module.config, "cleanup_old_images", return_value=0),
            mock.patch.object(image_service_module, "cleanup_image_thumbnails", return_value=0),
            mock.patch.object(image_service_module, "load_tags", return_value=fake_tags),
            mock.patch.object(image_service_module.image_storage_service, "list_items", return_value=fake_items),
        ):
            payload = image_service_module.list_images(
                "http://example.test",
                media_type="image",
                tag="duck",
                search="duck",
                limit=1,
                offset=50,
            )

        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["total_size"], 300)
        self.assertEqual(payload["counts"], {"all": 3, "image": 2, "video": 1, "music": 0})
        self.assertEqual(payload["page"], 2)
        self.assertEqual(payload["page_count"], 2)
        self.assertEqual(payload["offset"], 1)
        self.assertEqual(payload["items"][0]["path"], "2026/06/04/duck-b.png")

    def test_webdav_only_image_response_uses_remote_bytes(self):
        remote_bytes = b"remote-image-bytes"

        with (
            mock.patch.object(image_service_module.image_storage_service, "has_local", return_value=False),
            mock.patch.object(image_service_module.image_storage_service, "get_bytes", return_value=remote_bytes) as get_bytes,
        ):
            response = image_service_module.get_image_response("2099/01/01/remote-only.png")

        self.assertEqual(response.body, remote_bytes)
        self.assertEqual(response.media_type, "image/png")
        get_bytes.assert_called_once_with("2099/01/01/remote-only.png")

    def test_webdav_only_thumbnail_uses_remote_bytes(self):
        remote_path = "2099/01/01/remote-only.png"
        image_buf = io.BytesIO()
        Image.new("RGB", (4, 4), color=(255, 0, 0)).save(image_buf, format="PNG")

        with tempfile.TemporaryDirectory() as temp_dir:
            thumb_dir = Path(temp_dir) / "thumbs"
            with (
                mock.patch.object(type(image_service_module.config), "image_thumbnails_dir", new_callable=mock.PropertyMock) as thumb_prop,
                mock.patch.object(image_service_module.image_storage_service, "has_local", return_value=False),
                mock.patch.object(image_service_module.image_storage_service, "get_bytes", return_value=image_buf.getvalue()) as get_bytes,
            ):
                thumb_prop.return_value = thumb_dir
                thumbnail = image_service_module.ensure_thumbnail(remote_path)

            self.assertTrue(thumbnail.is_file())
            self.assertTrue(thumbnail.read_bytes())
            self.assertEqual(thumbnail.relative_to(thumb_dir).as_posix(), f"{remote_path}.png")
        get_bytes.assert_called_once_with(remote_path)

    def test_download_images_zip_uses_remote_bytes_when_local_missing(self):
        remote_path = "2099/01/01/unit-test-remote-only.png"
        remote_bytes = b"remote-image-bytes"

        with mock.patch.object(image_service_module.image_storage_service, "get_bytes", return_value=remote_bytes) as get_bytes:
            buf = image_service_module.download_images_zip([remote_path])

        with zipfile.ZipFile(buf, "r") as archive:
            self.assertEqual(archive.namelist(), ["unit-test-remote-only.png"])
            self.assertEqual(archive.read("unit-test-remote-only.png"), remote_bytes)
        get_bytes.assert_called_once_with(remote_path)

    def test_proxy_profiles_create_list_and_delete(self):
        profiles = []

        def fake_get_proxy_profiles():
            return [dict(item) for item in profiles]

        def fake_update(data):
            nonlocal profiles
            profiles = [dict(item) for item in data.get("proxy_profiles", profiles)]
            return {"proxy_profiles": [dict(item) for item in profiles]}

        with (
            mock.patch.object(system_module.config, "get_proxy_profiles", side_effect=fake_get_proxy_profiles),
            mock.patch.object(system_module.config, "update", side_effect=fake_update),
        ):
            create_response = self.client.post(
                "/api/proxy/profiles",
                headers=AUTH_HEADERS,
                json={
                    "id": "hk 1",
                    "name": "香港代理",
                    "proxy": "http://user:pass@example.com:7890",
                    "no_proxy": "localhost,127.0.0.1",
                    "enabled": True,
                    "notes": "primary",
                },
            )

            self.assertEqual(create_response.status_code, 200, create_response.text)
            created = create_response.json()["profile"]
            self.assertEqual(created["id"], "hk-1")
            self.assertEqual(created["name"], "香港代理")
            self.assertEqual(created["proxy"], "http://user:pass@example.com:7890")

            list_response = self.client.get("/api/proxy/profiles", headers=AUTH_HEADERS)
            self.assertEqual(list_response.status_code, 200, list_response.text)
            self.assertEqual(list_response.json()["profiles"][0]["id"], "hk-1")

            delete_response = self.client.delete("/api/proxy/profiles/hk-1", headers=AUTH_HEADERS)
            self.assertEqual(delete_response.status_code, 200, delete_response.text)
            self.assertEqual(delete_response.json()["deleted"], "hk-1")
            self.assertEqual(delete_response.json()["profiles"], [])

    def test_proxy_profile_test_resolves_profile_before_testing(self):
        with (
            mock.patch.object(system_module, "resolve_proxy_url", return_value="http://127.0.0.1:7890") as resolve_mock,
            mock.patch.object(
                system_module,
                "test_proxy",
                return_value={"ok": True, "status": 200, "latency_ms": 12, "error": None},
            ) as test_mock,
        ):
            response = self.client.post(
                "/api/proxy/profiles/test",
                headers=AUTH_HEADERS,
                json={"id": "hk-1"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["result"]["latency_ms"], 12)
        resolve_mock.assert_called_once_with("profile:hk-1")
        test_mock.assert_called_once_with("http://127.0.0.1:7890")


if __name__ == "__main__":
    unittest.main()
