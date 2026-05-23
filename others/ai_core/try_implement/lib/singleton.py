#!/usr/bin/env python3
"""singleton — singleton 資源模式：queue + consume rate 管理。

對應 thinking_pending.md §4。LLM Entry Manager 是這個模式的具體實例：資源有限
（本地/遠端模型一次只能處理一個請求），且請求者是多個不認識彼此的 caller →
採 queue（一次處理一個）+ consume rate（token/錢/算力多維度）管理。

本 library 把這模式抽成三塊：
    RateMeter        — 多維度用量累計 + 上限檢查（token / money / gpu_sec …）
    RequestQueue     — FIFO，enqueue / dequeue / cancel
    SingletonResource— 綁起來：submit 進 queue，一次 serve 一個，順手記 consume

== 設計決策 ==
1. RateMeter 維度不寫死（不是只有 token）：用 dict 累計任意命名維度，符合 §4
   「token、金錢、算力等不同維度」。上限選填，超限只「回報」不強制 abort——由 caller
   決定停或續（policy 與 mechanism 分離）。
2. queue 是純記憶體單行（singleton 一次處理一個，無需多佇列複雜度）。多個不同 LLM
   entry 各自消費不同 queue 的情境，由「多個 SingletonResource 實例」表達，不在單例內處理。
3. cancel 用 ticket id（submit 時發），對應 §4「Queue 的標準介面 enqueue/dequeue/cancel」。
"""

from __future__ import annotations

import itertools
from collections import deque
from typing import Any, Callable


class RateMeter:
    """多維度用量累計器。limits 選填；超限只回報不強制。"""

    def __init__(self, limits: dict[str, float] | None = None):
        self.limits = dict(limits or {})
        self._used: dict[str, float] = {}

    def record(self, **amounts: float) -> None:
        for dim, amt in amounts.items():
            self._used[dim] = self._used.get(dim, 0) + amt

    def total(self, dim: str) -> float:
        return self._used.get(dim, 0)

    def usage(self) -> dict[str, float]:
        return dict(self._used)

    def remaining(self, dim: str) -> float | None:
        if dim not in self.limits:
            return None
        return self.limits[dim] - self.total(dim)

    def exceeded(self) -> list[str]:
        """回傳已超過上限的維度名稱列表（空 = 都還在額度內）。"""
        return [d for d, lim in self.limits.items() if self.total(d) > lim]

    def would_exceed(self, **amounts: float) -> list[str]:
        """若再記這些量，哪些維度會超限。"""
        over = []
        for d, lim in self.limits.items():
            if self.total(d) + amounts.get(d, 0) > lim:
                over.append(d)
        return over


class RequestQueue:
    """FIFO 請求佇列，支援用 ticket id 取消。"""

    def __init__(self):
        self._q: deque[tuple[int, Any]] = deque()
        self._ids = itertools.count(1)
        self._cancelled: set[int] = set()

    def enqueue(self, payload: Any) -> int:
        tid = next(self._ids)
        self._q.append((tid, payload))
        return tid

    def dequeue(self) -> tuple[int, Any] | None:
        """取下一個未被取消的請求；空或全取消回 None。"""
        while self._q:
            tid, payload = self._q.popleft()
            if tid in self._cancelled:
                self._cancelled.discard(tid)
                continue
            return (tid, payload)
        return None

    def cancel(self, tid: int) -> bool:
        """標記取消；dequeue 時跳過。回是否確實在佇列中。"""
        if any(t == tid for t, _ in self._q):
            self._cancelled.add(tid)
            return True
        return False

    def pending(self) -> int:
        return sum(1 for t, _ in self._q if t not in self._cancelled)


class SingletonResource:
    """一次處理一個請求的有限資源，順手記 consume rate。"""

    def __init__(self, name: str, limits: dict[str, float] | None = None):
        self.name = name
        self.queue = RequestQueue()
        self.meter = RateMeter(limits)

    def submit(self, payload: Any) -> int:
        """把請求排進 queue，回 ticket id。"""
        return self.queue.enqueue(payload)

    def cancel(self, tid: int) -> bool:
        return self.queue.cancel(tid)

    def serve_one(
        self,
        worker: Callable[[Any], Any],
        cost_fn: Callable[[Any, Any], dict] | None = None,
    ) -> tuple[int, Any] | None:
        """取一個請求跑 worker，記 consume；回 (ticket_id, result)，queue 空回 None。"""
        item = self.queue.dequeue()
        if item is None:
            return None
        tid, payload = item
        result = worker(payload)
        if cost_fn is not None:
            self.meter.record(**cost_fn(payload, result))
        return (tid, result)

    def drain(
        self,
        worker: Callable[[Any], Any],
        cost_fn: Callable[[Any, Any], dict] | None = None,
        stop_on_limit: bool = True,
    ) -> list[tuple[int, Any]]:
        """一次處理一個直到 queue 空；stop_on_limit 時一旦超限即停。"""
        results: list[tuple[int, Any]] = []
        while True:
            if stop_on_limit and self.meter.exceeded():
                break
            r = self.serve_one(worker, cost_fn)
            if r is None:
                break
            results.append(r)
        return results
