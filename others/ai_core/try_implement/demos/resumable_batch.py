#!/usr/bin/env python3
"""端到端示範：可續傳的批次處理器（lib/recovery + lib/state_dirs 落地）。

驗證「標準狀態目錄慣例」+「中斷恢復慣例」的參考實作真能扛中斷：
  - 成果寫進 .data/<name>/results.json（累積成果，不可隨意刪）
  - 進度（offset）寫進 .state/<name>/recovery/offset.json + recovery.json manifest
  - 第一次跑到一半「崩潰」（拋例外，recovery 停在 in_progress）
  - 第二次重跑：startup 偵測到 in_progress + mode=resume → 從斷點接續，不重做已完成的

執行：python3 demos/resumable_batch.py
（自我測試：第二次從正確 offset 接續、最終全部完成、已完成項目沒被重算。）
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_TRY = _HERE.parent
if str(_TRY) not in sys.path:
    sys.path.insert(0, str(_TRY))

from lib import recovery, state_dirs


def run_batch(items: list[str], base: str, crash_at: int | None = None) -> tuple[list[str], int]:
    """處理 items（範例處理 = 轉大寫）。crash_at 指定在第幾個 item 前模擬崩潰。

    回傳 (results, resumed_from)；resumed_from 是這次從哪個 index 開始（0 = 全新）。
    """
    sd = state_dirs.StateDirs("batch", base)
    rm = recovery.RecoveryManager("batch", base, mode="resume")
    results_path = sd.child("data", "results.json")     # .data：累積成果
    offset_path = rm.payload_path("offset.json")          # .state/batch/recovery/offset.json

    # ---- 啟動恢復：先 detect，再決定從哪開始 ----
    start = 0
    results: list[str] = []
    action, _rec = rm.detect()
    if action == "resume" and offset_path.is_file():
        start = json.loads(offset_path.read_text(encoding="utf-8"))["next"]
        if results_path.is_file():
            results = json.loads(results_path.read_text(encoding="utf-8"))

    rm.begin(payload="recovery/offset.json")              # 標記 in_progress
    offset_path.parent.mkdir(parents=True, exist_ok=True)

    for i in range(start, len(items)):
        if crash_at is not None and i == crash_at:
            raise RuntimeError(f"模擬崩潰於 item {i}（recovery 將停在 in_progress）")
        results.append(items[i].upper())                  # 處理
        # 落地成果 + checkpoint 進度（每筆都存，確保中斷可恢復）
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
        offset_path.write_text(json.dumps({"next": i + 1}), encoding="utf-8")
        rm.checkpoint(payload="recovery/offset.json")

    rm.complete()                                          # 標記 done
    return results, start


def run() -> dict:
    base = tempfile.mkdtemp(prefix="batch_")
    items = ["a", "b", "c", "d", "e"]

    # 第一次：跑到 item 2 前崩潰（item 0、1 已完成）
    crashed = False
    try:
        run_batch(items, base, crash_at=2)
    except RuntimeError:
        crashed = True

    rm = recovery.RecoveryManager("batch", base, mode="resume")
    mid_action, mid_rec = rm.detect()

    # 第二次：重跑，從斷點接續
    results, resumed_from = run_batch(items, base)
    final_action, _ = rm.detect()

    return {
        "crashed": crashed,
        "mid_action": mid_action,
        "mid_status": (mid_rec or {}).get("status"),
        "resumed_from": resumed_from,
        "results": results,
        "final_action": final_action,
    }


def main() -> int:
    r = run()
    print("=== 可續傳批次處理 demo ===\n")
    print(f"第一次跑：在 item 2 模擬崩潰 → crashed={r['crashed']}")
    print(f"崩潰後 recovery 狀態：detect={r['mid_action']}, status={r['mid_status']}")
    print(f"第二次跑：從 index {r['resumed_from']} 接續（前 2 個已完成，不重做）")
    print(f"最終成果：{r['results']}")
    print(f"完成後 recovery：detect={r['final_action']}")

    assert r["crashed"] is True, "第一次應崩潰"
    assert r["mid_action"] == "resume" and r["mid_status"] == "in_progress", "崩潰後應停在 in_progress/resume"
    assert r["resumed_from"] == 2, f"應從 index 2 接續，得到 {r['resumed_from']}"
    assert r["results"] == ["A", "B", "C", "D", "E"], f"最終應全部完成，得到 {r['results']}"
    assert r["final_action"] == "clean", "完成後應為 clean"
    print("\n=== 中斷恢復如預期：從斷點接續、不重算、最終完成 ✓ ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
