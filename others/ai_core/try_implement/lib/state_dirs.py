#!/usr/bin/env python3
"""state_dirs — 「標準狀態目錄慣例」的參考實作。

對應 core_nature/composite_spec.md §「標準狀態目錄慣例（Standard State Directory
Convention）」。當程式宣告 ``state: "stateful_external"`` 且在 terminal 環境執行時，
其外部狀態存放在工作目錄下這四個位置之一：

    .config/<name>/  或 .config/<name>.json   程式不修改的設定（人類/外部工具寫入）
    .cache/<name>/   或 .cache/<name>.json    可隨時刪除，程式不依賴其存在
    .state/<name>/   或 .state/<name>.json    程式目前所在 stage，可重置
    .data/<name>/    或 .data/<name>.json     累積成果，不可隨意刪除，需備份

本 library 把「路徑解析 + 單檔 JSON 讀寫 + 目錄建立」收斂成一個小物件，讓遵守此
慣例的程式不必各自硬編路徑字串。

== 設計決策（理由附後）==
1. 四種角色用 enum 字串 "config"/"cache"/"state"/"data" 指稱，與 register() 的
   state_dirs 欄位允許值一致（_core.py `_STATE_DIR_VALUES`）。
2. 同一角色同時提供「資料夾」與「單檔」兩種路徑：``dir_path(kind)`` / ``file_path(kind)``。
   慣例規定單檔必須是 .json 且內容為 JSON object——故只有單檔形式提供 read_json/write_json。
3. base 預設為 cwd（Path(".")）。慣例明說是「工作目錄下」，不是 $HOME/.config。
   這點與 XDG 不同，是刻意的：ai_core 的狀態目錄綁在「呼叫時的工作目錄」，
   讓 hub / 呼叫方能預期副作用範圍落在當前目錄。
4. 不強制四個目錄都存在——按語意選用。建立採 lazy（呼叫 ensure_dir / write 時才 mkdir）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# 與 src/ai_core/_core.py 的 _STATE_DIR_VALUES 對齊
KINDS = ("config", "cache", "state", "data")


class StateDirs:
    """某程式在某 base 目錄下的標準狀態目錄存取器。"""

    def __init__(self, program_name: str, base: str | Path | None = None):
        if not program_name:
            raise ValueError("program_name 不可為空")
        self.name = program_name
        self.base = Path(base) if base is not None else Path(".")

    # ---- 路徑解析 ----

    def _check_kind(self, kind: str) -> None:
        if kind not in KINDS:
            raise ValueError(f"kind 必須是 {KINDS} 之一，got {kind!r}")

    def dir_path(self, kind: str) -> Path:
        """資料夾形式：``.<kind>/<name>/``（資料夾內子檔格式不限）。"""
        self._check_kind(kind)
        return self.base / f".{kind}" / self.name

    def file_path(self, kind: str) -> Path:
        """單檔形式：``.<kind>/<name>.json``（慣例規定必須是 .json，內容為 JSON object）。"""
        self._check_kind(kind)
        return self.base / f".{kind}" / f"{self.name}.json"

    # ---- 資料夾形式：建立 / 子檔路徑 ----

    def ensure_dir(self, kind: str) -> Path:
        """確保資料夾存在並回傳其路徑（lazy 建立）。"""
        p = self.dir_path(kind)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def child(self, kind: str, *parts: str) -> Path:
        """資料夾形式下的子檔路徑：``.<kind>/<name>/<parts...>``。"""
        return self.dir_path(kind).joinpath(*parts)

    # ---- 單檔形式：JSON 讀寫 ----

    def read_json(self, kind: str, default: Any = None) -> Any:
        """讀單檔 ``.<kind>/<name>.json``；不存在時回 default。"""
        p = self.file_path(kind)
        if not p.is_file():
            return default
        return json.loads(p.read_text(encoding="utf-8"))

    def write_json(self, kind: str, obj: Any) -> Path:
        """寫單檔 ``.<kind>/<name>.json``（慣例：內容應為 JSON object）。"""
        p = self.file_path(kind)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return p

    # ---- 給 register() 用的宣告 ----

    def declared(self, *kinds: str) -> dict:
        """產出可餵給 register(state_dirs=...) 的片段。

        例：``StateDirs("foo").declared("state", "data")`` →
            ``{"state": "stateful_external", "state_dirs": ["state", "data"]}``
        """
        for k in kinds:
            self._check_kind(k)
        return {"state": "stateful_external", "state_dirs": list(kinds)}
