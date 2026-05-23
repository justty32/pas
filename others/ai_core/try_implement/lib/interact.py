#!/usr/bin/env python3
"""interact — 多函數「交互」的最小模型（黑板 driver）。

對應 docs/multi_function_interaction.md §5。compose.py 處理的是**單向組合**
（資料從輸入流到輸出）；interact 處理更難的**交互**：函式之間來回，需要兩樣
compose 沒有的東西——**共享狀態**與**終止條件**。

== 黑板（blackboard）模型 ==
參與函式輪流讀寫一個共享 state（dict），driver 反覆跑直到終止謂詞成立：

    run(participants, state, until):
        while not until(state) and 未達上限:
            for p in participants:
                state = p(state)
        return state

== 為什麼 max_rounds 是強制的 ==
LLM 交互最容易出事的地方就是**不會停**（actor 與 critic 無限互踢）。所以本模型把
``max_rounds`` 設成**必有的安全閥**（預設給值），即使 ``until`` 永遠不成立也保證收斂。
這呼應 §5「沒有終止條件，交互不會停」。

== 與其他零件的接點 ==
- 參與函式可以是 lib/llm_call.bind 出來的 LLM 函式 → actor-critic、debate。
- 共享 state 可落地到 lib/state_dirs；多輪可中斷恢復接 lib/recovery。
- 輪數 / 成本上限本質上是 lib/singleton 的 consume rate 守門（這裡用 max_rounds 簡化）。
- actor-critic 就是「LLM-as-judge」：critic 是一個驗證/評分用的 LLM 函式
  （見 docs/llm_taming_framework.md §4）——把 L2 驗證從「單次」升級成「來回修」。
"""

from __future__ import annotations

from typing import Any, Callable

# 參與函式：讀一個 state dict，回（可為新的）state dict
Participant = Callable[[dict], dict]


def run(
    participants: list[Participant],
    state: dict,
    until: Callable[[dict], bool],
    max_rounds: int = 8,
) -> dict:
    """黑板 driver：每一輪讓每個 participant 依序讀寫 state，直到 until 成立或達上限。

    回傳最終 state；state 內可放 ``_rounds``（已跑輪數）與 ``_stopped``（停因）。
    """
    rounds = 0
    while rounds < max_rounds:
        if until(state):
            state["_stopped"] = "until"
            break
        for p in participants:
            state = p(state)
        rounds += 1
    else:
        state["_stopped"] = "max_rounds"
    state.setdefault("_stopped", "until" if until(state) else "max_rounds")
    state["_rounds"] = rounds
    return state


# --------------------------------------------------------------------------
# actor-critic：一個生成、一個批評，來回修到驗收或用盡輪數
# --------------------------------------------------------------------------

def actor_critic(
    task: str,
    actor: Callable[[str, str | None], str],
    critic: Callable[[str, str], tuple[bool, str]],
    max_rounds: int = 3,
) -> dict:
    """actor 生成草稿、critic 批評，反覆修正。

    - ``actor(task, feedback) -> draft``：feedback 為 None 表示第一稿。
    - ``critic(task, draft) -> (accepted, feedback)``：accepted=True 即驗收。
    回傳 ``{"draft", "accepted", "rounds", "history"}``。

    這是「LLM 生成 + LLM 評審」的最小骨架，比單次生成可靠得多
    （把驗證從一次性的 pass/fail 升級成「不過就帶著理由重修」）。
    """
    feedback: str | None = None
    history: list[dict] = []
    draft = ""
    accepted = False
    rounds = 0
    for rounds in range(1, max_rounds + 1):
        draft = actor(task, feedback)
        accepted, feedback = critic(task, draft)
        history.append({"round": rounds, "draft": draft, "accepted": accepted,
                        "feedback": feedback})
        if accepted:
            break
    return {"draft": draft, "accepted": accepted, "rounds": rounds, "history": history}


# --------------------------------------------------------------------------
# debate：多個 debater 各出一版，judge 選 / 合成
# --------------------------------------------------------------------------

def debate(
    task: str,
    debaters: list[Callable[[str], str]],
    judge: Callable[[str, list[str]], str],
    rounds: int = 1,
) -> dict:
    """多方各出 argument，judge 收斂成裁決。rounds>1 時每輪把上一輪裁決回灌給 debaters。

    回傳 ``{"verdict", "rounds", "arguments"}``（arguments 為最後一輪各方論點）。
    """
    context = task
    arguments: list[str] = []
    verdict = ""
    for _ in range(max(1, rounds)):
        arguments = [d(context) for d in debaters]
        verdict = judge(task, arguments)
        context = f"{task}\n\n（上一輪裁決：{verdict}）"  # 回灌給下一輪
    return {"verdict": verdict, "rounds": max(1, rounds), "arguments": arguments}
