#!/usr/bin/env python3
"""compose_meta — 「組合的軸推導規則」原型（候選新概念）。

對應 docs/multi_function_interaction.md §3。compose.py 只組合**行為**；本模組多做一件事：
從成員函式的八軸 metadata，**推導出複合函式的 metadata**。若這套規則成立，hub 就能對
「臨時組起來的複合函式」自動算 metadata，不必人工標註——這是把「組合維度」接回八軸的橋。

== 核心物件 ==
``MetaFn`` = 一個 callable + 它的八軸 metadata。組合 MetaFn 會同時得到新行為與**推導後的 meta**。

== 推導規則（本原型實作的部分）==
- **guarantee**：強度序 none < idempotent < transactional。
  - `pipe`：取**最弱**（一條鏈只要有一段不能安全重試，整條就不能）。
  - `fanout`：分支間若共用 state_dir → 並發寫衝突 → 退化為 none；否則取最弱。
- **state**：聯集——任一成員 stateful_external，整體就是 stateful_external。
- **state_dirs**：聯集（讓 hub 能算出複合函式會碰哪些目錄）。
- **lifecycle**：複合呼叫本身回 one_shot；若有 persistent 成員，加 `requires_persistent`
  列出相依——八軸**沒有**「依賴外部 server」這個 lifecycle 值，這個推導正好把該缺口
  暴露出來（見 §3「有外部 server 相依的 lifecycle 變體」）。

== 組合對被組合者的契約（額外示範）==
`mretry` 要求被包函式至少 idempotent，否則拒絕組裝——這把 docs §3 的
「retry 的前置條件」變成可執行的檢查，而非紙上規則。

== 簡化與保留 ==
- guarantee 的強度序是簡化（transactional 與 idempotent 嚴格說是不同性質，非全序）；
  此處為了能算 min 而定序，附此說明。
- interruptible 的推導較微妙（pipe 在段與段之間最安全 = 天然 checkpoint，非簡單格），
  本原型先不推導，列為後續。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from lib import compose

_GUARANTEE_RANK = {"none": 0, "idempotent": 1, "transactional": 2}
_RANK_GUARANTEE = {0: "none", 1: "idempotent", 2: "transactional"}


@dataclass
class MetaFn:
    """callable + 八軸 metadata。可被 compose_meta 的組合子組合並推導出新 meta。"""

    fn: Callable[[str], str]
    meta: dict = field(default_factory=dict)
    name: str = ""

    def __call__(self, x: str) -> str:
        return self.fn(x)


# ---- 推導小工具 ----

def _guarantee(meta: dict) -> str:
    return meta.get("guarantee", "none")


def _weakest_guarantee(metas: list[dict]) -> str:
    if not metas:
        return "none"
    return _RANK_GUARANTEE[min(_GUARANTEE_RANK.get(_guarantee(m), 0) for m in metas)]


def _union_state(metas: list[dict]) -> str:
    return ("stateful_external"
            if any(m.get("state") == "stateful_external" for m in metas)
            else "stateless")


def _union_state_dirs(metas: list[dict]) -> list[str]:
    out: list[str] = []
    for m in metas:
        for d in m.get("state_dirs", []):
            if d not in out:
                out.append(d)
    return out


def _requires_persistent(metafns: list[MetaFn]) -> list[str]:
    return [mf.name or "?" for mf in metafns if mf.meta.get("lifecycle") == "persistent"]


def _shared_state_dir(metafns: list[MetaFn]) -> bool:
    seen: set[str] = set()
    for mf in metafns:
        dirs = set(mf.meta.get("state_dirs", []))
        if seen & dirs:
            return True
        seen |= dirs
    return False


# ---- 推導 + 組合 ----

def derive_pipe(metafns: list[MetaFn]) -> dict:
    metas = [mf.meta for mf in metafns]
    out: dict = {
        "lifecycle": "one_shot",
        "state": _union_state(metas),
        "guarantee": _weakest_guarantee(metas),
    }
    dirs = _union_state_dirs(metas)
    if dirs:
        out["state_dirs"] = dirs
    req = _requires_persistent(metafns)
    if req:
        out["requires_persistent"] = req  # 八軸無此值——示範缺口
    return out


def mpipe(*metafns: MetaFn) -> MetaFn:
    """meta-aware pipe：組合行為 + 推導 meta。"""
    fn = compose.pipe(*[mf.fn for mf in metafns])
    name = "pipe(" + ",".join(mf.name or "?" for mf in metafns) + ")"
    return MetaFn(fn=fn, meta=derive_pipe(list(metafns)), name=name)


def derive_fanout(metafns: list[MetaFn]) -> dict:
    metas = [mf.meta for mf in metafns]
    conflict = _shared_state_dir(metafns)
    out: dict = {
        "lifecycle": "one_shot",
        "state": _union_state(metas),
        "guarantee": "none" if conflict else _weakest_guarantee(metas),
    }
    dirs = _union_state_dirs(metas)
    if dirs:
        out["state_dirs"] = dirs
    if conflict:
        out["_warning"] = "分支共用 state_dir，並發寫衝突風險 → guarantee 退化為 none"
    return out


def mfanout_reduce(metafns: list[MetaFn], reducer: Callable[[list[str]], str]) -> MetaFn:
    fn = compose.fanout_reduce([mf.fn for mf in metafns], reducer)
    name = "fanout(" + ",".join(mf.name or "?" for mf in metafns) + ")"
    return MetaFn(fn=fn, meta=derive_fanout(list(metafns)), name=name)


def mretry(metafn: MetaFn, validate: Callable[[str], bool], retries: int = 3) -> MetaFn:
    """meta-aware retry：強制檢查「被包函式至少 idempotent」這個前置契約。"""
    if _guarantee(metafn.meta) == "none":
        raise ValueError(
            f"retry_until_valid 要求被包函式至少 idempotent（否則重試會累積副作用）；"
            f"{metafn.name or '<匿名>'} 的 guarantee=none"
        )
    fn = compose.retry_until_valid(metafn.fn, validate, retries)
    return MetaFn(fn=fn, meta=dict(metafn.meta), name=f"retry({metafn.name})")
