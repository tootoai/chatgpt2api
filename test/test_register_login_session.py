from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from services.register import openai_register


class FakeCookies:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str | None]] = []

    def set(self, name: str, value: str, domain: str | None = None) -> None:
        self.items.append((name, value, domain))


class FakeSession:
    def __init__(self, name: str) -> None:
        self.name = name
        self.cookies = FakeCookies()
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = ""

    def json(self) -> dict:
        return self._payload


class RegisterLoginSessionTests(unittest.TestCase):
    def test_login_exchange_uses_fresh_session_and_device_id(self) -> None:
        registrar = object.__new__(openai_register.PlatformRegistrar)
        original_session = FakeSession("registration")
        login_session = FakeSession("login")
        registrar.session = original_session
        registrar.device_id = "registration-device"
        login_device_id = "11111111-2222-3333-4444-555555555555"
        requests_seen: list[tuple[FakeSession, str, str, dict]] = []

        def fake_request(session, method, url, retry_attempts=3, **kwargs):
            requests_seen.append((session, method, url, kwargs))
            if "/api/accounts/authorize?" in url:
                return FakeResponse(200), ""
            if url.endswith("/api/accounts/password/verify"):
                return FakeResponse(200, {"continue_url": "https://auth.openai.com/consent"}), ""
            raise AssertionError(f"unexpected request: {method} {url}")

        exchange_calls = []

        def fake_exchange(session, device_id, code_verifier, continue_url):
            exchange_calls.append((session, device_id, code_verifier, continue_url))
            return {
                "email": "fresh@example.test",
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "id_token": "id-token",
            }

        with (
            patch.object(openai_register, "create_session", return_value=login_session) as create_session,
            patch.object(openai_register.uuid, "uuid4", return_value=uuid.UUID(login_device_id)),
            patch.object(openai_register, "request_with_local_retry", side_effect=fake_request),
            patch.object(openai_register, "build_sentinel_token", return_value="sentinel-token") as build_sentinel,
            patch.object(openai_register, "exchange_platform_tokens", side_effect=fake_exchange),
        ):
            tokens = registrar._login_and_exchange_tokens("fresh@example.test", "password", {}, 1)

        create_session.assert_called_once_with(openai_register.config["proxy"])
        self.assertEqual(tokens["access_token"], "access-token")
        self.assertIs(registrar.session, original_session)
        self.assertEqual(registrar.device_id, "registration-device")
        self.assertTrue(login_session.closed)
        self.assertEqual(
            login_session.cookies.items,
            [
                ("oai-did", login_device_id, ".auth.openai.com"),
                ("oai-did", login_device_id, "auth.openai.com"),
            ],
        )
        self.assertTrue(requests_seen)
        self.assertTrue(all(session is login_session for session, _, _, _ in requests_seen))
        authorize = next(item for item in requests_seen if "/api/accounts/authorize?" in item[2])
        self.assertIn(f"device_id={login_device_id}", authorize[2])
        password_verify = next(item for item in requests_seen if item[2].endswith("/api/accounts/password/verify"))
        self.assertEqual(password_verify[3]["headers"]["oai-device-id"], login_device_id)
        build_sentinel.assert_called_once_with(login_session, login_device_id, "password_verify")
        self.assertEqual(exchange_calls[0][0], login_session)
        self.assertEqual(exchange_calls[0][1], login_device_id)


if __name__ == "__main__":
    unittest.main()
