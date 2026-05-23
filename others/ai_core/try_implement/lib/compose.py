#!/usr/bin/env python3
"""compose — 多函數合作/交互的組合子（八軸之外的「組合維度」）。

== 為什麼需要這一層 ==
現有八軸（lifecycle/state/interruptible/guarantee…）描述的是【單一函式】的執行本性。
但 ai_core 真正的價值在於把很多函式【組合】起來。組合本身是另一個正交維度——
不是「這個函式是什麼」，而是「這些函式怎麼一起動」。compose 把常見的合作/交互模式
做成一等公民的組合子。

每個組合子吃若干個 ``f(str)->str``（或更廣的 callable），回傳一個新的 ``f(str)->str``。
因為輸入輸出型別不變，組合子可以無限疊套（pipe 裡套 vote、vote 裡套 retry…）。

== 組合子分類 ==
順序合作：  pipe（管線，= 調用鏈）
並聯合作：  fanout（同輸入多分支）、fanout_reduce（多分支再彙整）
條件合作：  route（依條件分派，= Switch 的組合子化）、with_fallback（主備）
分治合作：  decompose（拆 → 各自處理 → 合）

== 與「馴化 LLM 隨機性」的關係（重點）==
LLM 是唯一的非確定性函式。下面這幾個組合子正是把它馴化成可靠複合函式的工具：
  retry_until_valid  拒絕採樣：一直重抽到輸出通過驗證為止（把「偶爾對」變「保證對」）
  vote               自一致：同輸入抽 N 次取多數（把方差換成穩定）
  best_of            抽 N 次取最高分（用 scorer 把「好壞」可計算化）
  guard              驗證→修復：壞輸出交給另一個函式（可以是另一次 LLM 呼叫）修
這些對「任何吵的函式」都適用——LLM 只是最典型的那個。詳見 docs/llm_taming_framework.md。
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Iterable

Fn = Callable[[str], str]


# --------------------------------------------------------------------------
# 順序合作
# --------------------------------------------------------------------------

def pipe(*fns: Fn) -> Fn:
    """管線：把前一個的輸出餵給下一個。pipe(f, g, h)(x) == h(g(f(x)))。

    這是「調用鏈」的純函式版（lib/trace 負責它的可觀測性）。
    """
    def composed(x: str) -> str:
        for f in fns:
            x = f(x)
        return x
    return composed


# --------------------------------------------------------------------------
# 並聯合作
# --------------------------------------------------------------------------

def fanout(*fns: Fn) -> Callable[[str], list[str]]:
    """同一輸入餵給多個函式，回傳各自輸出的 list。"""
    def run(x: str) -> list[str]:
        return [f(x) for f in fns]
    return run


def fanout_reduce(fns: Iterable[Fn], reducer: Callable[[list[str]], str]) -> Fn:
    """多分支跑完後，用 reducer 把 list 收成單一輸出（map → reduce）。"""
    fns = list(fns)

    def run(x: str) -> str:
        return reducer([f(x) for f in fns])
    return run


# --------------------------------------------------------------------------
# 條件合作
# --------------------------------------------------------------------------

def route(selector: Callable[[str], str], table: dict[str, Fn],
          default: Fn | None = None) -> Fn:
    """依 selector(input) 算出的 key 分派到 table[key]（Switch 的組合子化）。"""
    def run(x: str) -> str:
        key = selector(x)
        fn = table.get(key, default)
        if fn is None:
            raise KeyError(f"route：無對應分支 {key!r} 且無 default")
        return fn(x)
    return run


def with_fallback(primary: Fn, fallback: Fn,
                  is_ok: Callable[[str], bool] | None = None) -> Fn:
    """主函式拋例外、或 is_ok 判定輸出不合格時，改用備援函式。"""
    def run(x: str) -> str:
        try:
            out = primary(x)
        except Exception:  # noqa: BLE001
            return fallback(x)
        if is_ok is not None and not is_ok(out):
            return fallback(x)
        return out
    return run


# --------------------------------------------------------------------------
# 分治合作
# --------------------------------------------------------------------------

def decompose(split: Callable[[str], list[str]], sub: Fn,
              join: Callable[[list[str]], str]) -> Fn:
    """把輸入拆成多塊、各自過 sub、再 join 回來（分而治之）。

    對 LLM 特別有用：大任務拆成小而受限的子任務，每塊更易驗證，整體更穩。
    """
    def run(x: str) -> str:
        return join([sub(part) for part in split(x)])
    return run


# --------------------------------------------------------------------------
# 馴化隨機性
# --------------------------------------------------------------------------

class ValidationError(Exception):
    """retry_until_valid 用盡次數仍無合格輸出時拋出。"""


def retry_until_valid(fn: Fn, validate: Callable[[str], bool],
                      retries: int = 3,
                      on_exhausted: Fn | None = None) -> Fn:
    """拒絕採樣：重複呼叫 fn 直到輸出通過 validate，最多 retries 次。

    用盡仍不過：若給了 on_exhausted 則回 on_exhausted(x)，否則拋 ValidationError。
    把「LLM 偶爾給出格式對的答案」變成「保證格式對，否則明確失敗」。
    """
    def run(x: str) -> str:
        last = None
        for _ in range(max(1, retries)):
            last = fn(x)
            if validate(last):
                return last
        if on_exhausted is not None:
            return on_exhausted(x)
        raise ValidationError(f"retry_until_valid 用盡 {retries} 次仍未通過；最後輸出={last!r}")
    return run


def vote(fn: Fn, n: int = 5, key: Callable[[str], Any] | None = None) -> Fn:
    """自一致（self-consistency）：同輸入跑 n 次，回出現最多次的輸出。

    key 把輸出正規化後再比對（例如只比答案數字、忽略措辭）；預設用整個字串。
    把單次抽樣的方差，換成多次抽樣的眾數穩定性。
    """
    keyf = key or (lambda s: s)

    def run(x: str) -> str:
        outs = [fn(x) for _ in range(max(1, n))]
        counts = Counter(keyf(o) for o in outs)
        winner_key, _ = counts.most_common(1)[0]
        # 回傳第一個 key 命中的原始輸出（保留原貌，不只回 key）
        for o in outs:
            if keyf(o) == winner_key:
                return o
        return outs[0]
    return run


def best_of(fn: Fn, n: int, score: Callable[[str], float]) -> Fn:
    """抽 n 次，回 score 最高者。用 scorer 把「哪個比較好」變成可計算。"""
    def run(x: str) -> str:
        candidates = [fn(x) for _ in range(max(1, n))]
        return max(candidates, key=score)
    return run


def guard(fn: Fn, validate: Callable[[str], bool], repair: Fn) -> Fn:
    """驗證 → 修復：fn 輸出不過驗證時，把它交給 repair（可為另一次 LLM 呼叫）修。"""
    def run(x: str) -> str:
        out = fn(x)
        if validate(out):
            return out
        return repair(out)
    return run
