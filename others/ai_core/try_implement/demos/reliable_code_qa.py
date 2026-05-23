#!/usr/bin/env python3
"""端到端示範：可靠的程式碼問答函式（docs/llm_taming_framework.md §5 落地）。

把馴化框架的多層串成**一個**可靠函式，全用 lib/ 的零件 + ScriptedBackend 模擬 LLM 的
「同輸入不同輸出」隨機性，證明整套東西串起來真的能動：

  L0 契約   bind(system=…)         綁定角色，要求輸出帶 ```python 區塊
  L2 驗證   retry_until_valid       沒有程式碼區塊就重抽（拒絕採樣）
  L2 修復   guard                   有區塊但語法錯 → 交給 repair（另一次 LLM 呼叫）修
  L1 確定化 memoize                 同一問題不重算（命中完全不碰 backend）

執行：python3 demos/reliable_code_qa.py
（本檔同時是 demo 與自我測試：跑完會 assert 每層都如預期生效。）
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from lib import compose, llm_call, memoize


def _extract_code(text: str) -> str:
    m = re.search(r"```python\n(.*?)```", text, re.S)
    return m.group(1) if m else text


def _syntax_ok(text: str) -> bool:
    try:
        compile(_extract_code(text), "<demo>", "exec")
        return True
    except SyntaxError:
        return False


def build_reliable_qa(base: str):
    """組裝五層，回傳 (qa_fn, backends) 供 demo 觀察各層觸發。"""
    # 模擬一個「會抽到壞答案」的 LLM：第一抽沒程式碼、第二抽有區塊但語法錯
    answer_backend = llm_call.ScriptedBackend([
        "這是你要的答案：用 sorted()。",            # 無 ```python → retry 拒
        "```python\nsorted([3, 1, 2]\n```",          # 有區塊但少了右括號（語法錯）
    ])
    # 修復用的 LLM：回正確版本
    repair_backend = llm_call.ScriptedBackend([
        "```python\nsorted([3, 1, 2])\n```",
    ])

    # L0：綁定角色 + 要求帶程式碼區塊
    ask = llm_call.bind(
        system="你是資深工程師，回答務必包含一段 ```python 程式碼區塊",
        backend=answer_backend,
    )
    # L2 驗證：沒有程式碼區塊就重抽
    ask = compose.retry_until_valid(ask, validate=lambda o: "```python" in o, retries=3)
    # L2 修復：語法錯就請另一個 LLM 修
    repair = llm_call.bind(prefix="以下程式碼有語法錯，只回修正後版本：\n",
                           backend=repair_backend)
    ask = compose.guard(ask, validate=_syntax_ok, repair=repair)

    # L1 確定化：同問題不重算
    mz = memoize.Memoizer("code_qa", base=base)

    def qa(question: str) -> tuple[str, bool]:
        return mz.cached_call(lambda: ask(question), stdin=question)

    return qa, answer_backend, repair_backend


def run() -> dict:
    base = tempfile.mkdtemp(prefix="code_qa_")
    qa, answer_backend, repair_backend = build_reliable_qa(base)

    q = "如何把 [3,1,2] 排序？"
    out1, hit1 = qa(q)               # 第一次：retry + guard 修復都會跑
    calls_after_first = answer_backend.i
    out2, hit2 = qa(q)               # 第二次：memoize 命中，完全不碰 backend
    calls_after_second = answer_backend.i

    return {
        "answer": out1,
        "first_hit": hit1,
        "second_hit": hit2,
        "answer_backend_calls_after_first": calls_after_first,
        "answer_backend_calls_after_second": calls_after_second,
        "repair_backend_calls": repair_backend.i,
        "syntax_ok": _syntax_ok(out1),
    }


def main() -> int:
    r = run()
    print("=== 可靠程式碼問答 demo ===\n")
    print(f"最終答案：\n{r['answer']}\n")
    print(f"L2 retry：answer backend 被抽了 {r['answer_backend_calls_after_first']} 次"
          f"（第 1 次無程式碼被拒、第 2 次才過）")
    print(f"L2 guard：repair backend 被呼叫 {r['repair_backend_calls']} 次（語法錯被修）")
    print(f"L1 memoize：第一次 hit={r['first_hit']}、第二次 hit={r['second_hit']}")
    print(f"           第二次呼叫後 answer backend 仍是 "
          f"{r['answer_backend_calls_after_second']} 次（命中快取，沒再碰 LLM）")
    print(f"最終語法正確：{r['syntax_ok']}")

    # 自我測試：每層都要如預期生效
    assert r["answer_backend_calls_after_first"] == 2, "retry 應抽 2 次"
    assert r["repair_backend_calls"] == 1, "guard 應觸發 1 次修復"
    assert r["syntax_ok"] is True, "最終輸出應語法正確"
    assert r["first_hit"] is False and r["second_hit"] is True, "memoize 應第二次命中"
    assert r["answer_backend_calls_after_second"] == 2, "命中快取不應再碰 backend"
    print("\n=== 全部層次如預期生效 ✓ ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
