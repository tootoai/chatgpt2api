from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable, Iterator, TypeVar

from services.config import config
from utils.log import logger

T = TypeVar("T")


class ImageWorkerRejected(RuntimeError):
    def __init__(self, message: str, diagnostics: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.status_code = 429
        self.error_type = "rate_limit_error"
        self.code = "rate_limit_exceeded"
        self.diagnostics = diagnostics or {}

    def to_openai_error(self) -> dict[str, object]:
        return {
            "error": {
                "message": str(self),
                "type": self.error_type,
                "param": None,
                "code": self.code,
            }
        }


class ImageExecutorService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._executor: ThreadPoolExecutor | None = None
        self._admission: threading.BoundedSemaphore | None = None
        self._tokens = 0

    def _get_executor(self) -> tuple[ThreadPoolExecutor, threading.BoundedSemaphore, int]:
        tokens = config.image_worker_concurrency
        with self._lock:
            if self._executor is None or self._tokens != tokens:
                old_executor = self._executor
                self._executor = ThreadPoolExecutor(max_workers=tokens, thread_name_prefix="image-worker")
                self._admission = threading.BoundedSemaphore(tokens)
                self._tokens = tokens
                if old_executor is not None:
                    old_executor.shutdown(wait=False, cancel_futures=False)
            assert self._admission is not None
            return self._executor, self._admission, tokens

    @staticmethod
    def _queue_ms(queued_at: float) -> int:
        return int((time.monotonic() - queued_at) * 1000)

    def _queue_diagnostics(self, queued_at: float, tokens: int) -> dict[str, object]:
        return {
            "image_stage": "worker_queue",
            "image_worker_queue_ms": self._queue_ms(queued_at),
            "image_worker_concurrency": tokens,
            "account_selection_error": "image workers are busy",
        }

    def _acquire_worker(self, admission: threading.BoundedSemaphore, queued_at: float, tokens: int) -> bool:
        wait_timeout = config.image_worker_queue_timeout_secs
        acquired = admission.acquire(timeout=wait_timeout) if wait_timeout > 0 else admission.acquire()
        if not acquired:
            logger.warning({
                "event": "image_worker_queue_timeout",
                "queue_ms": self._queue_ms(queued_at),
                "image_worker_concurrency": tokens,
            })
        return acquired

    async def _acquire_worker_async(
        self,
        admission: threading.BoundedSemaphore,
        queued_at: float,
        tokens: int,
    ) -> bool:
        wait_timeout = config.image_worker_queue_timeout_secs
        deadline = queued_at + wait_timeout if wait_timeout > 0 else None
        while True:
            if admission.acquire(blocking=False):
                return True
            if deadline is not None and time.monotonic() >= deadline:
                logger.warning({
                    "event": "image_worker_queue_timeout",
                    "queue_ms": self._queue_ms(queued_at),
                    "image_worker_concurrency": tokens,
                })
                return False
            await asyncio.sleep(0.05)

    def run_sync(self, func: Callable[..., T], *args) -> T:
        queued_at = time.monotonic()
        executor, admission, tokens = self._get_executor()
        if not self._acquire_worker(admission, queued_at, tokens):
            raise ImageWorkerRejected(
                "image workers are busy, please retry later",
                self._queue_diagnostics(queued_at, tokens),
            )

        def wrapped_call() -> T:
            wait_ms = self._queue_ms(queued_at)
            logger.debug({
                "event": "image_worker_acquired",
                "queue_ms": wait_ms,
                "image_worker_concurrency": tokens,
            })
            started = time.monotonic()
            try:
                return func(*args)
            finally:
                logger.info({
                    "event": "image_worker_finished",
                    "run_ms": int((time.monotonic() - started) * 1000),
                    "total_ms": int((time.monotonic() - queued_at) * 1000),
                    "image_worker_concurrency": tokens,
                })
                admission.release()

        try:
            future = executor.submit(wrapped_call)
        except Exception:
            admission.release()
            raise
        return future.result()

    async def run(self, func: Callable[..., T], *args) -> T:
        queued_at = time.monotonic()
        executor, admission, tokens = self._get_executor()
        if not await self._acquire_worker_async(admission, queued_at, tokens):
            raise ImageWorkerRejected(
                "image workers are busy, please retry later",
                self._queue_diagnostics(queued_at, tokens),
            )

        def wrapped_call() -> T:
            wait_ms = self._queue_ms(queued_at)
            logger.debug({
                "event": "image_worker_acquired",
                "queue_ms": wait_ms,
                "image_worker_concurrency": tokens,
            })
            started = time.monotonic()
            try:
                return func(*args)
            finally:
                logger.info({
                    "event": "image_worker_finished",
                    "run_ms": int((time.monotonic() - started) * 1000),
                    "total_ms": int((time.monotonic() - queued_at) * 1000),
                    "image_worker_concurrency": tokens,
                })
                admission.release()

        try:
            future = executor.submit(wrapped_call)
        except Exception:
            admission.release()
            raise
        wrapped = asyncio.wrap_future(future)
        return await wrapped

    def iter_sync(self, items: Iterable[T]) -> Iterator[T]:
        queued_at = time.monotonic()
        _executor, admission, tokens = self._get_executor()
        if not self._acquire_worker(admission, queued_at, tokens):
            raise ImageWorkerRejected(
                "image workers are busy, please retry later",
                self._queue_diagnostics(queued_at, tokens),
            )
        wait_ms = self._queue_ms(queued_at)
        logger.debug({
            "event": "image_worker_acquired",
            "queue_ms": wait_ms,
            "image_worker_concurrency": tokens,
            "stream": True,
        })
        started = time.monotonic()
        try:
            yield from items
        finally:
            logger.info({
                "event": "image_worker_finished",
                "run_ms": int((time.monotonic() - started) * 1000),
                "total_ms": int((time.monotonic() - queued_at) * 1000),
                "image_worker_concurrency": tokens,
                "stream": True,
            })
            admission.release()


image_executor_service = ImageExecutorService()
