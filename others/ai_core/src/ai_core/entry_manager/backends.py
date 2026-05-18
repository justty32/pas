from __future__ import annotations

from typing import Any, AsyncIterator


async def call_backend(
    entry_config: dict,
    messages: list[dict],
    options: dict[str, Any],
    stream: bool = False,
) -> str | AsyncIterator[str]:
    """透過 litellm 呼叫對應後端（ollama / lm-studio / gemini 等）。

    stream=False：等待完整回應後回傳字串。
    stream=True：回傳 async generator，逐塊 yield delta token（§6.9）。
    後端連線失敗時拋例外，由 worker 捕捉寫進 task.error。
    """
    pass


def build_litellm_params(entry_config: dict, options: dict) -> dict:
    """把 ai_core config 格式的 entry_config 轉換成 litellm.acompletion 所需的參數 dict。

    處理細節：
    - api_key_env：從環境變數讀 API key（避免 key 寫死在 config 檔）
    - base_url：ollama / lm-studio 的本地 endpoint
    - model name 前綴（litellm 格式，如 "ollama/llama3"）
    """
    pass
