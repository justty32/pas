"""ai-core-sfc CLI 入口點（Small Function Center dispatcher，§9.1）。"""
from __future__ import annotations


def main() -> None:
    """解析 CLI 旗標，dispatch 給 FuncRegistry 對應的子函式。

    支援旗標（dispatch-flag 為 --call，可由實作者改名）：
    --call <name> [--input <file>] [--output <file>]
        呼叫指定子函式，I/O 慣例同全系統標準（§5）

    --list
        列出所有已登記子函式名稱到 stdout（一行一個）

    --call <name> --metadata
        查詢指定子函式的 metadata（pass-through 或 SFC 自管，§9.2）

    --metadata
        印 SFC 自身的 metadata JSON 後 exit 0

    --json-errors
        stderr 改輸出 JSON 格式錯誤
    """
    pass
