#!/usr/bin/env python3
"""llm_call — 把 LLM 視為一個（隨機的）函式：``llm_call(str) -> str``。

對應 ai_core/CLAUDE.md 元件 2「LLM Calling Packing」與 thinking.md 的核心隱喻：
把 LLM 呼叫當成函式，再疊 context 與 post-processing 形成更具語意的新函式。

== 兩件事 ==
1. **基底**：``llm_call(prompt) -> text``。背後是可插拔 backend（本地/遠端/mock）。
2. **打包（packing）**：``bind(...)`` 把 system/prefix/suffix/postprocess 疊上去，
   產出一個新的 ``f(str)->str``。這正是 CLAUDE.md 的範例：

       coding_q = bind(system="you are a professor of coding, and...",
                       postprocess=lambda o: o + " -- at 20240505")
       coding_q("how to sort a list?")

== 與「馴化隨機性」的關係 ==
llm_call 是這套系統裡唯一的**非確定性函式**。馴化它的手段不寫在這裡，而是 lib/compose.py
的通用組合子（retry_until_valid 拒絕採樣、vote 自一致投票、memoize 強制確定性…）。
設計上刻意如此：**LLM 只是「一個比較吵的函式」，馴化它用的是組合任意函式的同一套組合子。**
詳見 docs/llm_taming_framework.md。

== Backend ==
本機沒有真 LLM，故預設 EchoBackend；ScriptedBackend / FnBackend 用來在測試裡模擬
「同一輸入、不同輸出」的隨機性，好讓 compose 的馴化組合子有東西可馴。真接 API 時，
實作一個 Backend 子類接上 lib/call.Http 或官方 SDK 即可，上層 bind/compose 完全不變。
"""

from __future__ import annotations

from typing import Any, Callable


class Backend:
    """LLM backend 介面。實作 complete(prompt, **opts) -> str 即可。"""

    def complete(self, prompt: str, **opts: Any) -> str:  # pragma: no cover - 抽象
        raise NotImplementedError


class EchoBackend(Backend):
    """把 prompt 回顯——預設 backend，無 LLM 時用。"""

    def complete(self, prompt: str, **opts: Any) -> str:
        return f"echo: {prompt}"


class ScriptedBackend(Backend):
    """依序吐出預設回應（循環）。用來在測試裡模擬非確定性。

    responses 元素可為字串，或 ``fn(prompt) -> str``。
    """

    def __init__(self, responses: list):
        self.responses = list(responses)
        self.i = 0

    def complete(self, prompt: str, **opts: Any) -> str:
        r = self.responses[self.i % len(self.responses)]
        self.i += 1
        return r(prompt) if callable(r) else r


class FnBackend(Backend):
    """用任意 ``fn(prompt, opts) -> str`` 當 backend（最自由）。"""

    def __init__(self, fn: Callable[[str, dict], str]):
        self.fn = fn

    def complete(self, prompt: str, **opts: Any) -> str:
        return self.fn(prompt, opts)


_default_backend: Backend = EchoBackend()


def set_default_backend(backend: Backend) -> None:
    global _default_backend
    _default_backend = backend


def llm_call(prompt: str, *, backend: Backend | None = None, **opts: Any) -> str:
    """基底：把 prompt 丟給 backend，回文字。

    opts（如 temperature / seed / max_tokens）原樣轉給 backend——是否支援由 backend 決定。
    """
    return (backend or _default_backend).complete(prompt, **opts)


def bind(
    *,
    system: str | None = None,
    prefix: str | None = None,
    suffix: str | None = None,
    postprocess: Callable[[str], str] | None = None,
    backend: Backend | None = None,
    **opts: Any,
) -> Callable[[str], str]:
    """把 context 與 post-processing 疊在 llm_call 之上，產出新的 ``f(str)->str``。

    這就是 CLAUDE.md「在基底上疊加 context 與 post-processing 形成新函式」的落地。
    產出的函式是無狀態 one-shot，可直接餵給 lib/compose 的組合子。
    """
    def f(text: str) -> str:
        parts: list[str] = []
        if system:
            parts.append(system)
        if prefix:
            parts.append(prefix)
        parts.append(text)
        if suffix:
            parts.append(suffix)
        prompt = "\n".join(parts)
        out = llm_call(prompt, backend=backend, **opts)
        if postprocess:
            out = postprocess(out)
        return out

    return f
