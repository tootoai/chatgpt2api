from __future__ import annotations

import hashlib
import secrets
import socket
import ssl
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from services.config import config
from utils.log import logger


class ImageLeaseUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ImageLease:
    key: str
    value: str
    backend: str = "local"


class _RedisProtocol:
    def __init__(self, url: str, timeout: float) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"redis", "rediss"}:
            raise ValueError("image lease redis url must start with redis:// or rediss://")
        self.scheme = parsed.scheme
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 6379
        self.username = unquote(parsed.username or "")
        self.password = unquote(parsed.password or "")
        self.db = int((parsed.path or "/0").strip("/") or "0")
        query = parse_qs(parsed.query or "")
        self.timeout = float(query.get("timeout", [timeout])[0] or timeout)

    def execute(self, *parts: object) -> Any:
        raw = self._encode(parts)
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.settimeout(self.timeout)
            if self.scheme == "rediss":
                with ssl.create_default_context().wrap_socket(sock, server_hostname=self.host) as tls_sock:
                    return self._execute_on_socket(tls_sock, raw)
            return self._execute_on_socket(sock, raw)

    def _execute_on_socket(self, sock: socket.socket, raw_command: bytes) -> Any:
        reader = sock.makefile("rb")
        if self.password:
            if self.username:
                sock.sendall(self._encode(("AUTH", self.username, self.password)))
            else:
                sock.sendall(self._encode(("AUTH", self.password)))
            self._parse(reader)
        if self.db:
            sock.sendall(self._encode(("SELECT", self.db)))
            self._parse(reader)
        sock.sendall(raw_command)
        return self._parse(reader)

    @staticmethod
    def _encode(parts: tuple[object, ...]) -> bytes:
        chunks = [f"*{len(parts)}\r\n".encode("ascii")]
        for part in parts:
            data = str(part).encode("utf-8")
            chunks.append(f"${len(data)}\r\n".encode("ascii"))
            chunks.append(data + b"\r\n")
        return b"".join(chunks)

    def _parse(self, reader) -> Any:
        prefix = reader.read(1)
        if not prefix:
            raise ImageLeaseUnavailable("redis closed the connection")
        line = reader.readline().rstrip(b"\r\n")
        if prefix == b"+":
            return line.decode("utf-8", errors="replace")
        if prefix == b"-":
            raise ImageLeaseUnavailable(line.decode("utf-8", errors="replace"))
        if prefix == b":":
            return int(line)
        if prefix == b"$":
            length = int(line)
            if length < 0:
                return None
            data = reader.read(length)
            reader.read(2)
            return data.decode("utf-8", errors="replace")
        if prefix == b"*":
            count = int(line)
            if count < 0:
                return None
            return [self._parse(reader) for _ in range(count)]
        raise ImageLeaseUnavailable("invalid redis response")


class ImageLeaseService:
    _ACQUIRE_SCRIPT = (
        "for i, key in ipairs(KEYS) do "
        "if redis.call('set', key, ARGV[1], 'NX', 'EX', ARGV[2]) then "
        "return key end "
        "end "
        "return nil"
    )
    _RELEASE_SCRIPT = (
        "if redis.call('get', KEYS[1]) == ARGV[1] then "
        "return redis.call('del', KEYS[1]) else return 0 end"
    )

    def _redis(self) -> _RedisProtocol | None:
        url = config.image_lease_redis_url
        if not url:
            return None
        return _RedisProtocol(url, config.image_lease_redis_timeout_secs)

    def _lease_key(self, token: str, slot: int) -> str:
        digest = hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()
        namespace = config.image_lease_namespace
        return f"{namespace}:image:lease:{digest}:{slot}"

    def acquire_first_account_slot(self, tokens: list[str], slots: int) -> tuple[str, ImageLease] | None:
        tokens = [str(token or "").strip() for token in tokens if str(token or "").strip()]
        if not tokens:
            return None
        redis = self._redis()
        if redis is None:
            return tokens[0], ImageLease(key="", value="", backend="local")
        slot_count = max(1, int(slots or 1))
        keys: list[str] = []
        key_to_token: dict[str, str] = {}
        for token in tokens:
            for slot in range(slot_count):
                key = self._lease_key(token, slot)
                keys.append(key)
                key_to_token[key] = token
        ttl = config.image_lease_ttl_secs
        value = secrets.token_hex(16)
        try:
            result = redis.execute("EVAL", self._ACQUIRE_SCRIPT, len(keys), *keys, value, ttl)
            if not result:
                return None
            key = str(result)
            token = key_to_token.get(key)
            if not token:
                raise ImageLeaseUnavailable("redis returned an unknown image lease key")
            return token, ImageLease(key=key, value=value, backend="redis")
        except Exception as exc:
            logger.error({"event": "image_lease_redis_error", "error": str(exc)})
            raise ImageLeaseUnavailable("image lease backend unavailable") from exc

    def acquire_account_slot(self, token: str, slots: int) -> ImageLease | None:
        result = self.acquire_first_account_slot([token], slots)
        return result[1] if result else None

    def release(self, lease: ImageLease | None) -> None:
        if lease is None or lease.backend != "redis":
            return
        redis = self._redis()
        if redis is None:
            return
        try:
            redis.execute("EVAL", self._RELEASE_SCRIPT, 1, lease.key, lease.value)
        except Exception as exc:
            logger.warning({"event": "image_lease_release_failed", "key": lease.key, "error": str(exc)})


image_lease_service = ImageLeaseService()
