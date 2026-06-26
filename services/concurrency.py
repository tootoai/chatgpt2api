"""全局请求并发闸门。

单进程部署下，handler 通过 run_in_threadpool 在线程池里同步执行，
没有任何全局上限时高并发会把请求一股脑灌给上游导致拥堵/超时。

这里在事件循环层用 asyncio.Semaphore 卡住“同时打到上游的请求数”：
名额没抢到的请求在事件循环里排队（不占线程池、不打上游），
排队超过 request_queue_timeout_seconds 则快速失败为可重试错误。

闸门按 image / text 两类各自计数，容量从 config 读取并支持运行时调整。
limit<=0 表示该类不限流。
"""
from __future__ import annotations

import asyncio

from services.config import config


class ConcurrencyLimitTimeout(RuntimeError):
    """排队等待并发名额超时（可重试）。"""

    def __init__(self, kind: str, limit: int, timeout: float) -> None:
        self.kind = kind
        self.limit = limit
        self.timeout = timeout
        super().__init__(
            f"request queue timeout: waited {timeout}s for a {kind} slot (limit={limit})"
        )


class _Gate:
    """单类请求的并发闸门，容量变化时按需重建底层信号量。"""

    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._limit = 0
        self._sem: asyncio.Semaphore | None = None

    def _ensure(self, limit: int) -> asyncio.Semaphore | None:
        if limit <= 0:
            self._limit = 0
            self._sem = None
            return None
        # 容量变化时重建；存量请求持有的是旧信号量，释放到旧对象上，安全。
        if self._sem is None or limit != self._limit:
            self._sem = asyncio.Semaphore(limit)
            self._limit = limit
        return self._sem

    async def acquire(self, limit: int, timeout: float) -> asyncio.Semaphore | None:
        sem = self._ensure(limit)
        if sem is None:
            return None
        try:
            if timeout > 0:
                await asyncio.wait_for(sem.acquire(), timeout=timeout)
            else:
                await sem.acquire()
        except asyncio.TimeoutError as exc:
            raise ConcurrencyLimitTimeout(self._kind, limit, timeout) from exc
        return sem


_image_gate = _Gate("image")
_text_gate = _Gate("text")


def gate_for(endpoint: str, *, image: bool) -> "_GateBinding":
    """根据请求类型返回对应闸门的绑定（带当前 config 容量与超时）。"""
    if image or endpoint.startswith("/v1/images"):
        return _GateBinding(_image_gate, config.image_concurrency_limit)
    return _GateBinding(_text_gate, config.text_concurrency_limit)


class _GateBinding:
    def __init__(self, gate: _Gate, limit: int) -> None:
        self._gate = gate
        self._limit = limit
        self._sem: asyncio.Semaphore | None = None

    async def acquire(self) -> None:
        """抢一个名额；超时抛 ConcurrencyLimitTimeout。"""
        self._sem = await self._gate.acquire(
            self._limit, float(config.request_queue_timeout_seconds)
        )

    def release(self) -> None:
        if self._sem is not None:
            self._sem.release()
            self._sem = None

