from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RateLimitConfig:
    """從 config.json 的 models.<name> 讀入的速率限制設定（§6.7）。

    未設定的欄位為 None，表示該維度不限制。
    GPU / 電力等欄位在 schema 中預留，第一版不追蹤。
    """

    rpm: int | None = None
    tokens_per_day: int | None = None
    cost_per_day: float | None = None


@dataclass
class UsageCounter:
    """追蹤單一 entry 的累計用量（純 in-memory，重啟後歸零，§6.12）。"""

    tokens_today: int = 0
    cost_today: float = 0.0
    current_minute_requests: int = 0
    last_minute_ts: float = field(default_factory=time.time)


class RateLimitExceeded(Exception):
    """當請求超過 rpm / tokens_per_day / cost_per_day 限制時拋出。

    攜帶 --json-errors 友善欄位，由 server 端直接轉成 429 + JSON error body。
    """

    def __init__(self, error_type: str, message: str, hint: str = "") -> None:
        pass


class RateLimiter:
    """根據 RateLimitConfig 與 UsageCounter 判斷請求是否可放行（§6.7）。

    超限拋 RateLimitExceeded，請求不入 queue（§5.2）。
    """

    def __init__(self, config: RateLimitConfig) -> None:
        """初始化計數器與設定。"""
        pass

    def check(self, estimated_tokens: int = 0, estimated_cost: float = 0.0) -> None:
        """檢查 rpm / tokens_per_day / cost_per_day 是否已超限。

        超限拋 RateLimitExceeded；通過則靜默返回。
        estimated_tokens / estimated_cost 是 caller 的預估值，僅用於 cost_per_day 預檢；
        實際用量在 record_usage() 才更新。
        """
        pass

    def record_usage(self, tokens_used: int, cost: float) -> None:
        """LLM 呼叫完成後更新累計計數。由 worker 呼叫。"""
        pass

    def get_remaining(self) -> dict:
        """回傳各維度的剩餘配額 dict。

        供 GET /entries/<name> 的 current_usage 欄位使用（§6.5 entrydata 範例）。
        """
        pass
