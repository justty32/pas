from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MetadataView:
    """函式 --metadata 的標準化視圖。

    原始 JSON 通過容錯解析後產生此物件；缺欄位一律用合理預設填補，
    永遠不拋 KeyError / AttributeError 給 caller（§4.6）。
    """

    name: str = ""
    summary: str = "(no description)"
    description: str = "(no description)"
    usage: str = ""
    tags: list[str] = field(default_factory=list)
    io: dict[str, Any] = field(default_factory=dict)
    examples: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    has_entries: bool = False
    entry_interface: dict[str, Any] = field(default_factory=dict)
    server: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    absent: bool = False
    # True 表示函式不支援 --metadata、exit non-0 或輸出非合法 JSON
    warnings: list[str] = field(default_factory=list)
    # 容錯降級時累積的警告訊息，供 hub 列印給使用者看


def fetch_metadata(path: Path) -> MetadataView:
    """對 path 執行 `<path> --metadata`，解析後回傳 MetadataView。

    §4.6 容錯規則全部在此函式處理：
    - 函式不支援 --metadata（exit non-0 / FileNotFoundError / TimeoutError）
      → absent=True，warnings 加一條說明
    - stdout 非合法 JSON
      → absent=True，stderr 印警告
    - 缺 io
      → 預設 {"input": "stdin", "output": "stdout", "format": {"input": "text", "output": "text"}}
      → warnings 加「io contract unknown」
    - 缺 summary / description
      → 用 "(no description)" 替代，warnings 加提示
    - 缺 examples
      → 空 list（dry-run 退化為只驗執行不 crash）
    永遠不丟例外給 caller；subprocess 例外一律被捕捉收進 warnings。
    """
    pass


def make_json_error(
    error_type: str,
    message: str,
    hint: str = "",
    retriable: bool = False,
) -> str:
    """產生符合 §5.1 規範的單行 JSON 錯誤字串（寫到 stderr 用）。

    格式：{"type": ..., "message": ..., "hint": ..., "retriable": ...}
    """
    pass


def print_json_error(
    error_type: str,
    message: str,
    hint: str = "",
    retriable: bool = False,
) -> None:
    """把 make_json_error 結果印到 stderr。不額外換行（JSON 本身已含 newline）。"""
    pass


def should_use_json_errors(args: list[str]) -> bool:
    """檢查 args 裡是否含 --json-errors 旗標。

    供各 CLI 在 argparse 之前就決定錯誤輸出格式，
    避免 argparse 自己的 error() 先用人類格式噴出去。
    """
    pass
