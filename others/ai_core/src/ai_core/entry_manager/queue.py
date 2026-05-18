from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class Task:
    """代表一個進入 queue 的 LLM 呼叫請求（in-memory only，重啟後丟失，§6.12）。"""

    task_id: str
    entry_name: str
    messages: list[dict]
    options: dict[str, Any]
    time_to_wait_ms: int | None
    enqueue_ts: float
    is_async: bool = False
    stream: bool = False
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    error: dict | None = None
    stream_queue: asyncio.Queue | None = None
    # stream 模式時 worker 把 delta token 推進此 queue，wrapper 從另一端讀


class EntryQueue:
    """管理單一 LLM entry 的 FIFO asyncio queue + worker pool（§6.6）。

    concurrency=1 退化為串行（本地模型 / GPU 受限資源標準場景）；
    concurrency>1 讓多個 worker 並行消費同一 queue（雲端 API）。
    concurrency 為靜態配置，改值需重啟 server（KISS，不支援 runtime 動態調整）。
    """

    def __init__(self, entry_name: str, concurrency: int = 1) -> None:
        """初始化 asyncio.Queue 與 worker task list。"""
        pass

    async def enqueue(self, task: Task) -> None:
        """把 task 放入 queue。

        Rate limit 應在呼叫此方法前由 RateLimiter.check() 完成；
        此方法只負責入隊，不做任何業務檢查。
        """
        pass

    async def start_workers(
        self,
        backend_caller: Callable[[Task], Awaitable[None]],
    ) -> None:
        """啟動 concurrency 個 asyncio worker task。

        每個 worker 持續從 queue 取 task，先檢查 time_to_wait_ms 是否已到期（§6.8），
        未到期才真正呼叫 backend_caller；
        worker 例外不終止 worker 自身，錯誤寫進 task.error，task.status = ERROR。
        """
        pass

    async def stop_workers(self) -> None:
        """送 sentinel 讓每個 worker 優雅結束，等待所有 worker task 完成。"""
        pass

    def get_status(self) -> dict:
        """回傳此 queue 的即時狀態（queue 長度、active workers 數等）。

        供 GET /status 端點彙總使用。
        """
        pass
