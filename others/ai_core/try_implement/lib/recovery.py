#!/usr/bin/env python3
"""recovery — 「中斷恢復慣例」的參考實作。

對應 core_nature/composite_spec.md §「中斷恢復慣例（Interruption Recovery
Convention）」。當程式宣告 §5 ``interruptible ∈ {resumable, rollback, resettable}``
或 §6 ``guarantee: "transactional"``，恢復能力的落地形式統一為：

    .state/<name>/recovery.json   恢復記錄 manifest（程式間的真正合約）
    .state/<name>/recovery/        opaque payload（進度資料 / journal，程式自訂，選填）

recovery.json 最小欄位：
    status   "in_progress"（執行中／被中斷）｜ "done"（正常完成）
    mode     "resume" ｜ "rollback" ｜ "reset"
    ts       上次寫入的時間戳（ISO 8601）
    payload  指向 recovery/ 內檔案的相對路徑（選填）

三種恢復模式（對半完成進度的處置）：
    resume    從斷點接續（§5 resumable）          → 不還原，往前推進
    rollback  撤銷未提交修改（§5 rollback / §6 transactional）→ 還原至呼叫前
    reset     重置到安全點（§5 resettable）        → 安全狀態（不保證原始）

== 設計決策 ==
1. 偵測為 auto：``startup()`` 啟動時自動讀記錄，不需任何 flag（合規範）。
2. 不新增 metadata 欄位：恢復能力由 §5/§6 既有欄位宣告，本 library 只承擔 on-disk
   合約（recovery.json）。這呼應 composite_spec §「為何不新增 metadata 欄位」。
3. ``session()`` context manager：進入時 begin（status=in_progress），正常離開時
   complete（status=done）；若途中拋例外或被 kill，記錄停在 in_progress，下一輪
   startup() 即可偵測到並恢復。這把「崩潰留下半完成記錄」變成預設行為。
"""

from __future__ import annotations

import datetime as _dt
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from lib.state_dirs import StateDirs

MODES = ("resume", "rollback", "reset")
_STATUS_IN_PROGRESS = "in_progress"
_STATUS_DONE = "done"


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RecoveryManager:
    """管理 .state/<name>/recovery.json 與 recovery/ payload。"""

    def __init__(self, program_name: str, base: str | Path | None = None, mode: str = "resume"):
        if mode not in MODES:
            raise ValueError(f"mode 必須是 {MODES} 之一，got {mode!r}")
        self.mode = mode
        self._sd = StateDirs(program_name, base)

    # ---- 路徑 ----

    @property
    def manifest_path(self) -> Path:
        return self._sd.child("state", "recovery.json")

    @property
    def payload_dir(self) -> Path:
        return self._sd.child("state", "recovery")

    def payload_path(self, *parts: str) -> Path:
        return self.payload_dir.joinpath(*parts)

    # ---- manifest 讀寫 ----

    def read(self) -> dict | None:
        """讀 recovery.json；不存在回 None。"""
        p = self.manifest_path
        if not p.is_file():
            return None
        import json
        return json.loads(p.read_text(encoding="utf-8"))

    def _write(self, status: str, payload: str | None, extra: dict | None) -> None:
        import json
        rec: dict[str, Any] = {"status": status, "mode": self.mode, "ts": _now()}
        if payload is not None:
            rec["payload"] = payload
        if extra:
            rec.update(extra)
        p = self.manifest_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def begin(self, payload: str | None = None, **extra: Any) -> None:
        """開始實際工作前呼叫：status=in_progress。"""
        self._write(_STATUS_IN_PROGRESS, payload, extra)

    def checkpoint(self, payload: str | None = None, **extra: Any) -> None:
        """工作途中更新進度（仍 in_progress，刷新 ts / payload）。"""
        self._write(_STATUS_IN_PROGRESS, payload, extra)

    def complete(self, delete: bool = False) -> None:
        """正常完成：status=done（或 delete=True 直接刪掉記錄）。"""
        if delete:
            self.manifest_path.unlink(missing_ok=True)
            return
        rec = self.read() or {}
        self._write(_STATUS_DONE, rec.get("payload"), None)

    # ---- 標準啟動恢復流程 ----

    def detect(self) -> tuple[str, dict | None]:
        """偵測啟動時該做什麼。

        回傳 ``(action, manifest)``：
          ("clean",  None)        記錄不存在或已 done → 乾淨開始
          ("resume", manifest)    上次被中斷，本程式採 resume
          ("rollback", manifest)  上次被中斷，本程式採 rollback
          ("reset",  manifest)    上次被中斷，本程式採 reset
        """
        rec = self.read()
        if rec is None or rec.get("status") == _STATUS_DONE:
            return ("clean", None)
        # in_progress：依記錄裡的 mode（記錄的 mode 是上次寫入時的策略）
        return (rec.get("mode", self.mode), rec)

    def startup(
        self,
        on_resume: Callable[[dict], None] | None = None,
        on_rollback: Callable[[dict], None] | None = None,
        on_reset: Callable[[dict], None] | None = None,
    ) -> str:
        """執行 composite_spec 的「啟動恢復流程（標準演算法）」。

        讀記錄 → 乾淨則直接回 "clean"；否則依 mode 呼叫對應 handler 後回該 mode。
        handler 收到 manifest dict。handler 缺席時僅回報 action，由 caller 自理。
        """
        action, rec = self.detect()
        if action == "clean":
            return "clean"
        if action == "resume" and on_resume:
            on_resume(rec or {})
        elif action == "rollback" and on_rollback:
            on_rollback(rec or {})
        elif action == "reset" and on_reset:
            on_reset(rec or {})
        return action

    @contextmanager
    def session(self, payload: str | None = None, **extra: Any):
        """包住一次工作：進入 begin(in_progress)，正常離開 complete(done)。

        若途中拋例外（或被 kill 繞過），記錄停在 in_progress，下一輪 startup() 可偵測。
        """
        self.begin(payload, **extra)
        yield self
        self.complete()
