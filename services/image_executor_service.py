from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError
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
        self._tokens = 0

    def _get_executor(self) -> tuple[ThreadPoolExecutor, int]:
        tokens = config.image_worker_concurrency
        with self._lock:
            if self._executor is None or self._tokens != tokens:
                old_executor = self._executor
                self._executor = ThreadPoolExecutor(max_workers=tokens, thread_name_prefix="image-worker")
                self._tokens = tokens
                if old_executor is not None:
                    old_executor.shutdown(wait=False, cancel_futures=False)
            return self._executor, tokens

    def run_sync(self, func: Callable[..., T], *args) -> T:
        queued_at = time.monotonic()
        executor, tokens = self._get_executor()
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

        future = executor.submit(wrapped_call)
        wait_timeout = config.image_worker_queue_timeout_secs
        try:
            return future.result(timeout=wait_timeout if wait_timeout > 0 else None)
        except TimeoutError as exc:
            if future.cancel():
                logger.warning({
                    "event": "image_worker_queue_timeout",
                    "queue_ms": int((time.monotonic() - queued_at) * 1000),
                    "image_worker_concurrency": tokens,
                })
                raise ImageWorkerRejected("image workers are busy, please retry later") from exc
            return future.result()

    async def run(self, func: Callable[..., T], *args) -> T:
        queued_at = time.monotonic()
        executor, tokens = self._get_executor()
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

        future = executor.submit(wrapped_call)
        wrapped = asyncio.wrap_future(future)
        wait_timeout = config.image_worker_queue_timeout_secs
        if wait_timeout > 0:
            done, _pending = await asyncio.wait({wrapped}, timeout=wait_timeout)
            if done:
                return await wrapped
            if future.cancel():
                logger.warning({
                    "event": "image_worker_queue_timeout",
                    "queue_ms": int((time.monotonic() - queued_at) * 1000),
                    "image_worker_concurrency": tokens,
                })
                raise ImageWorkerRejected("image workers are busy, please retry later")
        return await wrapped


image_executor_service = ImageExecutorService()
