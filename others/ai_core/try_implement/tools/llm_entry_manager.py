#!/usr/bin/env python3
"""llm_entry_manager — LLM Entry Manager（CLAUDE.md 元件 1 的具體實作）。

把「LLM 是 singleton 資源」這個立場落地：本地/遠端模型一次只能處理一個請求，且請求者
是多個不認識彼此的 caller → 採 queue（一次一個）+ consume rate（token/錢/算力）管理。

本工具 = persistent server（lib/server 的 NDJSON 行協議）+ singleton 資源（lib/singleton
的 RateMeter 管 consume rate）+ 可插拔 LLM backend（lib/llm_call，預設 mock）。

它同時示範三個 ai_core 概念如何疊起來：
    persistent server（thinking_pending §3）
  + singleton 資源（thinking_pending §4）
  + llm_call 基底（CLAUDE.md 元件 2）
  = LLM Entry Manager（CLAUDE.md 元件 1）

== 用法 ==
    llm_entry_manager                      # 啟動 server，讀 stdin 的 NDJSON 請求
    llm_entry_manager --limit-token 50     # 設 token 預算上限
    llm_entry_manager --metadata           # 自身 metadata

== 對外協議（NDJSON）==
    {"cmd": "complete", "prompt": "...", "opts": {...}}  → {"ok":true,"text":...,"usage":{...}}
    {"cmd": "usage"}                                     → {"ok":true,"usage":{...},"limits":{...}}
    {"cmd": "ping"} / {"cmd": "list"} / {"cmd": "shutdown"}（lib/server 內建）

超出 token 預算時，complete 回 ``{"ok": false, "error": "rate limit exceeded", ...}``，
這正是 singleton 資源「集中管理 consume rate」的職責。
"""

from __future__ import annotations

import argparse
import sys

from _common import ensure_ai_core_importable, ensure_lib_importable

ensure_ai_core_importable()
ensure_lib_importable()

import ai_core  # noqa: E402
from lib import llm_call, server, singleton  # noqa: E402


def _estimate_tokens(text: str) -> int:
    """粗估 token 數（mock：約 4 字元 1 token）。真接 API 時換成 backend 的 usage。"""
    return max(1, len(text) // 4)


# metadata：persistent server + singleton 資源。
# singleton 性質塞進 resources（八軸沒有專門的 singleton 欄位——這是一個觀察，見 README）。
_METADATA = {
    "lifecycle": "persistent",
    "state": "stateless",
    "resources": {"singleton": True, "consume_dimensions": ["token"]},
}

# --metadata（唯一引數時）由 library 攔截輸出
ai_core.register(**_METADATA)


def build_server(limit_token: float | None, backend: llm_call.Backend) -> server.NDJSONServer:
    srv = server.NDJSONServer("llm_entry_manager")
    limits = {"token": limit_token} if limit_token is not None else {}
    resource = singleton.SingletonResource("llm", limits=limits)

    @srv.handler("complete")
    def _complete(req: dict) -> dict:
        prompt = req.get("prompt", "")
        in_tok = _estimate_tokens(prompt)
        # consume rate 守門：先估這次大概多少，超預算就拒（singleton 的核心職責）
        if resource.meter.would_exceed(token=in_tok):
            return {
                "ok": False,
                "error": "rate limit exceeded",
                "usage": resource.meter.usage(),
                "limits": resource.meter.limits,
            }
        out = llm_call.llm_call(prompt, backend=backend, **req.get("opts", {}))
        used = in_tok + _estimate_tokens(out)
        resource.meter.record(token=used)
        return {"text": out, "usage": resource.meter.usage()}

    @srv.handler("usage")
    def _usage(req: dict) -> dict:
        return {"usage": resource.meter.usage(), "limits": resource.meter.limits}

    return srv


def main() -> int:
    p = argparse.ArgumentParser(prog="llm_entry_manager")
    p.add_argument("--limit-token", type=float, default=None,
                   help="token 預算上限；超過後 complete 回 rate limit")
    args = p.parse_args()

    # 真接 API 時把這裡換成接 lib/call.Http 或官方 SDK 的 Backend
    backend = llm_call.EchoBackend()
    srv = build_server(args.limit_token, backend)
    return srv.serve()


if __name__ == "__main__":
    sys.exit(main())
