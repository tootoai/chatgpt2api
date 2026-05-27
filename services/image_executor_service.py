from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

from services.config import config
from utils.log import logger

T = TypeVar("T")


class ImageWorkerRejected(RuntimeError):
    pass


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

    def _acquire_worker(self, admission: threading.BoundedSemaphore, queued_at: float, tokens: int) -> bool:
        wait_timeout = config.image_worker_queue_timeout_secs
        acquired = admission.acquire(timeout=wait_timeout) if wait_timeout > 0 else admission.acquire()
        if not acquired:
            logger.warning({
                "event": "image_worker_queue_timeout",
                "queue_ms": int((time.monotonic() - queued_at) * 1000),
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
                    "queue_ms": int((time.monotonic() - queued_at) * 1000),
                    "image_worker_concurrency": tokens,
                })
                return False
            await asyncio.sleep(0.05)

    def run_sync(self, func: Callable[..., T], *args) -> T:
        queued_at = time.monotonic()
        executor, admission, tokens = self._get_executor()
        if not self._acquire_worker(admission, queued_at, tokens):
            raise ImageWorkerRejected("image workers are busy, please retry later")

        def wrapped_call() -> T:
            wait_ms = int((time.monotonic() - queued_at) * 1000)
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
            raise ImageWorkerRejected("image workers are busy, please retry later")

        def wrapped_call() -> T:
            wait_ms = int((time.monotonic() - queued_at) * 1000)
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


image_executor_service = ImageExecutorService()
