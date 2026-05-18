"""ai-core-call 的 CLI 入口點（LLM Entry Manager 的 shell wrapper）。"""
from __future__ import annotations


def main() -> None:
    """解析 CLI 旗標，翻譯成 HTTP 呼叫送給 ai-core-server。

    必填旗標：
    --entry <name>      指定要用的 LLM entry
    --input <file>      輸入檔，內容包成 user message（§6.10）

    輸出旗標：
    --output <file>     結果寫入檔案（非 stream 模式必填；stream 可選）

    模式旗標：
    --async             非同步模式，立刻回傳 task_id 到 stdout
    --task <id>         搭配 --output，收取 async task 結果
    --stream            逐 token 吐到 stdout（與 --async 不相容，§6.9）
    --wait <ms>         queue 等待逾時毫秒數（§6.8）

    可選 sugar 旗標（§6.10）：
    --system <text|@file>   prepend system message
    --messages <file>       直接送完整 messages JSON，跳過單訊息包裝
    --append <file>         把 input 接到既有 messages 後面

    Metadata 旗標：
    --metadata                  印 wrapper 自身 metadata 後 exit
    --entry-metadata            印所有 entry 的 entrydata 後 exit
    --entry-metadata --entry X  印單一 entry 的 entrydata 後 exit

    --json-errors   stderr 改輸出 JSON 格式錯誤
    """
    pass


def build_self_metadata() -> dict:
    """產生 ai-core-call 自身的 --metadata JSON。

    包含 has_entries: true、entry_interface（§4.7）、
    server.activation 與 activation_hint（§4.8）。
    """
    pass


def fetch_entry_metadata(entry_name: str | None) -> dict:
    """向 ai-core-server 發 GET /entries 或 GET /entries/<name> 取得 entrydata。

    server 未啟動時 stderr 報錯 + exit 1（§5.2）。
    """
    pass
