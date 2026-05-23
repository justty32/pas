#!/usr/bin/env python3
"""提案原型：放寬版 ``--metadata`` 攔截 + subcommand-scoped metadata（解 Gap A / B）。

⚠️ 這是 try_implement 內的【提案原型】，不是正式 library。
真正的 ``ai_core.register()`` 位在 ``src/ai_core/_core.py``，本檔【完全不修改它】，
只在它之上加一層分派邏輯。此處示範「若要把 Gap A 的修法扶正進規範，介面與行為
可以長這樣」，供使用者評估後再決定是否 promote 進 ``src/``。

================== 解決的問題 ==================
**Gap A（阻塞級）**：``src/ai_core/_core.py`` 的 ``_intercept()`` 要求 ``--metadata``
必須是 argv 唯一引數，否則 exit 1。但 git-style CLI 的 ``prog <subcommand> --metadata``
（thinking_sfc.md 明文要求）此時 ``--metadata`` 並非唯一引數 → 被攔截報錯。結果每個
dispatcher 都得自己繞過 library，違背「library 統一處理 metadata」的初衷。

**Gap B（順帶解）**：單一執行檔含多種 lifecycle 的子命令（``sfc`` 是 one_shot dispatch、
``sfc forge`` 是 persistent server）。原 ``register()`` 只能宣告一個頂層 lifecycle。
本原型用 ``register_subcommand()`` 讓每個子命令各自宣告 scoped metadata，頂層描述
dispatcher 預設行為，子命令各自覆寫。

================== 介面 ==================
- ``register(**top_metadata)``              宣告程式「頂層」metadata（dispatcher 預設行為）
- ``register_subcommand(name, **metadata)`` 宣告「靜態子命令」的 scoped metadata
- ``register_subcommand_resolver(fn)``      註冊「動態子命令」解析器：``fn(name, ctx) -> dict|None``
                                            （SFC 的 tiny function 名稱來自 store，非寫死在程式裡）
- ``intercept(argv=None) -> None``          放寬版攔截；非 metadata 查詢時 return 交還控制權

================== 攔截規則（放寬後）==================
（先吃掉可選的前導 ``--store DIR``，使 ``prog --store DIR <sub> --metadata`` 也成立）
1. ``argv == ["--metadata"]``          → 印頂層 metadata，exit 0
2. ``argv == [<name>, "--metadata"]``  → 依序查 靜態子命令登記 → 動態 resolver；
                                          命中印該 scoped metadata exit 0；查無 → stderr 報錯 exit 1
3. 其餘                                 → return（一般 dispatch，交回 caller）

欄位驗證沿用既有 library 的 ``_validate``（no wheel-remake）：只擴充攔截/分派層，
不重造欄位驗證。``_validate`` 目前是 private——若扶正本提案，應在 ``_core.py`` 把它
（或等價的公開驗證入口）公開。
"""

from __future__ import annotations

import json
import sys
from typing import Any, Callable

from _common import ensure_ai_core_importable

ensure_ai_core_importable()
from ai_core._core import _validate  # noqa: E402  # 重用既有欄位驗證（reach into private）

_top: dict[str, Any] = {}
_subcommands: dict[str, dict[str, Any]] = {}
_resolver: Callable[[str, str | None], dict[str, Any] | None] | None = None


def register(**kwargs: Any) -> None:
    """宣告頂層 metadata（dispatcher 的預設行為）。"""
    global _top
    _top = _validate(kwargs)


def register_subcommand(name: str, **kwargs: Any) -> None:
    """宣告某個靜態子命令的 scoped metadata（可與頂層不同 lifecycle）。"""
    _subcommands[name] = _validate(kwargs)


def register_subcommand_resolver(fn: Callable[[str, str | None], dict[str, Any] | None]) -> None:
    """註冊動態子命令解析器。``fn(name, store_override) -> metadata dict | None``。

    用於 SFC 這類「子命令名稱來自外部資料」的情形：靜態登記查不到時，
    再交給 resolver 去 store / DB 查。
    """
    global _resolver
    _resolver = fn


def _emit(md: dict[str, Any]) -> None:
    print(json.dumps(md, ensure_ascii=False))
    sys.exit(0)


def intercept(argv: list[str] | None = None) -> None:
    """放寬版攔截。命中 metadata 查詢則輸出並 ``sys.exit``；否則 return 交還控制權。"""
    if argv is None:
        argv = sys.argv[1:]

    work = list(argv)
    store_override: str | None = None
    if len(work) >= 2 and work[0] == "--store":
        store_override = work[1]
        work = work[2:]

    # 規則 1：頂層 metadata
    if work == ["--metadata"]:
        _emit(_top)

    # 規則 2：subcommand-scoped metadata
    if len(work) == 2 and work[1] == "--metadata":
        name = work[0]
        if name in _subcommands:
            _emit(_subcommands[name])
        if _resolver is not None:
            md = _resolver(name, store_override)
            if md is not None:
                _emit(md)
        print(f"--metadata：未知的子命令/函式 {name!r}", file=sys.stderr)
        sys.exit(1)

    # 規則 3：非 metadata 查詢 → 交還控制權
    return
