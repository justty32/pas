from __future__ import annotations

from pathlib import Path

from ai_core.protocol.metadata import MetadataView, fetch_metadata


def scan_functions(
    path: Path,
    *,
    ext: list[str] | None = None,
    recursive: bool = False,
) -> list[MetadataView]:
    """掃描 path 下的可執行檔（或符合 ext 的檔案），逐一呼叫 fetch_metadata。

    掃描策略（§7.5）：
    - 預設：os.access(f, os.X_OK) 判可執行
    - ext 給定時：改用副檔名過濾，不再要求可執行位元
    - recursive=False（預設）：只掃頂層；recursive=True：遞迴子目錄

    回傳的 list 包含所有候選，含 absent=True 的項目（hub 仍列出並標警告）。
    遇到 SFC（MetadataView.raw 有 --list 支援的線索）時呼叫 expand_sfc() 展開。
    """
    pass


def expand_sfc(path: Path, sfc_meta: MetadataView) -> list[MetadataView]:
    """對支援 --list 的 SFC，呼叫 `<path> --list` 取子函式名稱，再各自查 metadata（§9.4）。

    若 SFC 不支援 --list（指令回傳 non-0 exit）：
    → 只回傳含 sfc_meta 自身的 list，並在 raw 中標 "type": "sfc"。

    子函式 metadata 查詢用 `<path> <dispatch-flag> <name> --metadata`；
    dispatch-flag 從 sfc_meta.raw 中讀取（無則預設 --call）。
    """
    pass


def _is_candidate(path: Path, ext: list[str] | None) -> bool:
    """判斷 path 是否為掃描候選（可執行位元 or 副檔名過濾）。"""
    pass
