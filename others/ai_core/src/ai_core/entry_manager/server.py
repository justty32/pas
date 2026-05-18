from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI(title="ai-core-server")

# 全域狀態（server 生命週期內存活）
_queues: dict = {}       # entry_name → EntryQueue
_limiters: dict = {}     # entry_name → RateLimiter
_tasks: dict = {}        # task_id → Task
_config: dict = {}
_token: str = ""


def load_config() -> dict:
    """從 platformdirs.user_config_dir("ai_core")/config.json 讀入設定。

    檔案不存在時回傳空 dict（server 可以 0 個 entry 狀態啟動）。
    """
    pass


def init_queues(config: dict) -> None:
    """根據 config["models"] 建立每個 entry 的 EntryQueue 與 RateLimiter。

    結果寫入模組層級的 _queues / _limiters dict。
    """
    pass


def get_or_create_token() -> str:
    """首次啟動時產生 token 並寫入 user_config_dir/ai_core/token（0600）；

    檔案已存在時直接讀取，不重新產生（§6.13）。
    Windows 用 ACL 限制當前使用者讀取，Unix 用 chmod 0600。
    """
    pass


def verify_token(request: Request) -> None:
    """從 Authorization: Bearer <token> header 驗證 token。

    驗證失敗拋 HTTPException 401。
    """
    pass


@app.on_event("startup")
async def startup() -> None:
    """server 啟動時執行：讀 config、初始化 queue、啟動 worker、載入 token。"""
    pass


@app.on_event("shutdown")
async def shutdown() -> None:
    """server 關閉時執行：優雅停止所有 worker。"""
    pass


@app.post("/call")
async def create_task(request: Request):
    """建立 LLM 呼叫 task（§6.4）。

    流程：驗 token → 驗 entry 存在 → rate limit 檢查 → 入 queue。
    body: {model, messages, options?, async?, time_to_wait_ms?, stream?}
    同步模式：等待完成後回傳結果；async 模式：立刻回傳 task_id。
    stream 模式：回傳 StreamingResponse（chunked transfer encoding，§6.9）。
    """
    pass


@app.get("/tasks/{task_id}")
async def get_task(task_id: str, request: Request):
    """查詢 task 狀態（pending / running / done / error / timeout）。"""
    pass


@app.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str, request: Request):
    """取得已完成 task 的結果。task 未完成時 404；重啟後所有 task id 失效（§6.12）。"""
    pass


@app.get("/status")
async def get_status(request: Request):
    """回傳所有 entry 的 queue 狀態與 rate limit 剩餘量。"""
    pass


@app.get("/entries")
async def list_entries(request: Request):
    """列出所有已設定 entry 的 entrydata 陣列（給 --entry-metadata 用，§6.5）。"""
    pass


@app.get("/entries/{name}")
async def get_entry(name: str, request: Request):
    """回傳單一 entry 的 entrydata（特性、限制、目前用量）。名稱不存在時 404。"""
    pass
