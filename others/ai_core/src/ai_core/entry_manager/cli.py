"""ai-core-server 的 CLI 入口點。"""
from __future__ import annotations


def main() -> None:
    """解析 CLI 旗標後啟動 ai-core-server（FastAPI + uvicorn）。

    支援旗標：
    --host          綁定 host（預設讀 AI_CORE_SERVER_HOST env 或 127.0.0.1）
    --port          綁定 port（預設讀 AI_CORE_SERVER_PORT env 或 5577）
    --log-file      同時把 log 寫到指定路徑（§6.11）
    --log-level     debug | info | warning | error，預設 info（§6.11）
    --metadata      印 server wrapper 自身的 metadata JSON 後 exit 0
    --json-errors   stderr 改輸出 JSON 格式錯誤
    """
    pass
