#!/usr/bin/env python3
"""memoize — 「記憶化慣例（Memoization Convention）」原型。

⚠️ 這條慣例在 core_nature/ 中【尚未定案】。session_resume.md 把它列為「狀態恢復家族
的第二條」，並留了三個開放決策。使用者外出期間授權我自行拍板——以下是我的決定與理由，
供使用者回來後評估。本檔是 try_implement 的提案，未動 src/ai_core。

== 觸發 ==
用 .cache/<name>/<input-hash> 做「輸入 → 輸出」快取。目的是 **效能**（避免重算），
不是正確性。與 idempotent 的區別（execution_forms 4.13）：
  - idempotent = 正確性（重跑不累積副作用）
  - memoized   = 效能（重跑直接取快取，不再算）

== 開放決策 1：cache key 的「輸入」包含哪些？==
【我的決定】key = sha256( canonical_json({version, stdin, args, file_digests, extra}) )。
  - 預設納入 stdin + args（最常見的純函式輸入）。
  - 可選納入 input 檔內容的 digest（檔大時存 digest 而非全文，省記憶體）。
  - 由呼叫方明確指定哪些參與——不臆測。理由：cli_spec §2.0 已把 CLI 呼叫定義成
    Lisp 風格函式呼叫 (program args...)，純函式的輸入就是 stdin + args (+ 指定的檔)，
    三者組合涵蓋絕大多數 one-shot 包裝函式。

== 開放決策 2：失效策略 ==
【我的決定】預設靠 .cache「可隨時刪除」語意即可（無 TTL，KISS）。但提供兩個 opt-in：
  - version：揉進 key。bump version 等於整批失效（對應「邏輯改了，舊快取作廢」）。
  - ttl：每筆存 ts，讀取時若超時視為 miss。對應「結果會隨時間過期」的函式。
  兩者都選填，預設關閉，符合「.cache 可隨時刪」的最小語意。

== 開放決策 3：metadata 欄位（關鍵差異）==
這是 memoized 與「中斷恢復」的根本不同：中斷恢復有既有軸值（interruptible/guarantee）
可隱含觸發，所以選了「不加欄位」；但 **memoized 沒有對應軸值可隱含**。guarantee enum
是 {none, idempotent, transactional}，塞不進 memoized。
【我的決定/建議】memoized 很可能【需要】一個新的頂層 metadata 欄位（如下方 declared()
的形狀）。但這會動到 lib_spec 的軸層（使用者禁區），故此處只示範「提案的欄位形狀」，
不塞進真 register()——真 register() 目前會以 unknown field 拒收它。這正是給使用者
決策 3 的具體證據：要嘛新增 memoized 欄位，要嘛接受「memoized 純屬 runtime、不在
metadata 宣告」。
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

from lib.state_dirs import StateDirs


def _canonical(obj: Any) -> str:
    """穩定序列化：sort_keys + 緊湊分隔，確保同輸入得同字串。"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def file_digest(path: str | Path) -> str:
    """檔內容的 sha256（大檔只存 digest，不把全文揉進 key）。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class Memoizer:
    """.cache/<name>/ 上的輸入→輸出快取。"""

    def __init__(
        self,
        program_name: str,
        base: str | Path | None = None,
        version: str = "1",
        ttl: float | None = None,
    ):
        self.version = version
        self.ttl = ttl
        self._sd = StateDirs(program_name, base)

    @property
    def cache_dir(self) -> Path:
        return self._sd.dir_path("cache")

    # ---- key 計算 ----

    def key(
        self,
        *,
        stdin: str | None = None,
        args: dict | None = None,
        files: list[str | Path] | None = None,
        extra: Any = None,
    ) -> str:
        material = {
            "v": self.version,
            "stdin": stdin,
            "args": args or {},
            "files": [file_digest(f) for f in (files or [])],
            "extra": extra,
        }
        return hashlib.sha256(_canonical(material).encode("utf-8")).hexdigest()

    def _entry_path(self, key: str) -> Path:
        return self.cache_dir / key

    # ---- 讀 / 寫 ----

    def get(self, key: str) -> str | None:
        """命中回快取輸出字串；miss（含過期）回 None。"""
        p = self._entry_path(key)
        if not p.is_file():
            return None
        try:
            env = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if self.ttl is not None and (time.time() - env.get("ts", 0)) > self.ttl:
            p.unlink(missing_ok=True)  # 過期即清，符合 .cache 語意
            return None
        return env.get("output")

    def put(self, key: str, output: str) -> Path:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        p = self._entry_path(key)
        env = {"ts": time.time(), "v": self.version, "output": output}
        p.write_text(json.dumps(env, ensure_ascii=False), encoding="utf-8")
        return p

    def invalidate(self, key: str) -> None:
        self._entry_path(key).unlink(missing_ok=True)

    def clear(self) -> int:
        """清掉本程式所有快取（回清掉幾筆）。.cache 語意：可隨時刪。"""
        if not self.cache_dir.is_dir():
            return 0
        n = 0
        for p in self.cache_dir.iterdir():
            if p.is_file():
                p.unlink()
                n += 1
        return n

    # ---- 高階：包住一次計算 ----

    def cached_call(
        self,
        compute: Callable[[], str],
        *,
        stdin: str | None = None,
        args: dict | None = None,
        files: list[str | Path] | None = None,
    ) -> tuple[str, bool]:
        """命中則回快取，否則跑 compute() 存起來再回。

        回 ``(output, hit)``；hit=True 表示來自快取。
        """
        k = self.key(stdin=stdin, args=args, files=files)
        cached = self.get(k)
        if cached is not None:
            return (cached, True)
        out = compute()
        self.put(k, out)
        return (out, False)

    # ---- 提案的 metadata 欄位形狀（決策 3 的證據；真 register() 目前拒收）----

    def declared(self) -> dict:
        """回傳【提案中】的 memoized metadata 形狀。

        ⚠️ 真正的 ai_core.register() 目前會以 "unknown metadata fields" 拒收 memoized。
        這裡只示範若新增此欄位，形狀可以長這樣，作為使用者決策 3 的具體素材。
        """
        d: dict[str, Any] = {"memoized": {"version": self.version}}
        if self.ttl is not None:
            d["memoized"]["ttl"] = self.ttl
        # memoized 用 .cache，故順帶宣告 state_dirs 含 cache
        d["state"] = "stateful_external"
        d["state_dirs"] = ["cache"]
        return d
