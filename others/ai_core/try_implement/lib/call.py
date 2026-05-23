#!/usr/bin/env python3
"""call — 跨邊界統一呼叫介面（in-process / subprocess / http）。

對應 thinking_pending.md §6 與 thinking_oop.md。核心立場：

    API 調用（HTTP）、shell 調用（subprocess）、程式內部函數調用，本質上是同一件事
    ——函式呼叫跨越不同的邊界，只是傳遞機制不同。

由於 ai_core 的 I/O 都是文字，三種邊界統一收斂成同一個介面：

    target.call(text_in: str) -> text_out: str

== 三種 target ==
    InProcess(fn)        直接函式呼叫（同 process）
    Subprocess(cmd)      開子 process，text 餵 stdin、收 stdout（跨 process）
    Http(url)            POST text 當 body、收 response body（跨網路）

== 設計決策 ==
1. 統一介面只承諾 str→str（最小公分母，符合「LLM I/O 都是文字」）。需要結構化資料時
   兩端自行 JSON 編解碼——不在本層做型別魔法。
2. Subprocess 自動帶上 trace.child_env()：子 process 接上同一條調用鏈（與 lib/trace 整合）。
3. Http 用標準庫 urllib，不引入 requests（least dependency）。
4. from_spec(dict) 讓 target 可由 JSON 設定描述——router/switch 的 mapping 目標可以是
   任一種邊界，呼叫端不需知道底層是函式、shell 還是 API（呼應 thinking_routing「router
   不在意 mapping 目標是檔案還是資料庫內容」，這裡再擴到網路）。

== 待設計（誠實標記）==
thinking_pending §6 指出跨網路邊界的【分散式狀態】（一致性、失敗恢復、冪等）與本地
調用有本質差異，需專門設計。本 library 只做「呼叫傳遞」，不處理分散式狀態——retry /
冪等請搭配 lib/memoize、§5/§6 軸值，或上層的 compose.retry_until_valid。
"""

from __future__ import annotations

import json
import subprocess
import urllib.request
from typing import Any, Callable

from lib import trace


class InProcess:
    """同 process 的直接函式呼叫。"""

    kind = "in_process"

    def __init__(self, fn: Callable[[str], str]):
        self.fn = fn

    def call(self, text: str) -> str:
        return self.fn(text)


class Subprocess:
    """跨 process：text → stdin，stdout → text。自動帶 trace 環境。"""

    kind = "subprocess"

    def __init__(self, cmd: list[str], check: bool = True):
        self.cmd = cmd
        self.check = check

    def call(self, text: str) -> str:
        proc = subprocess.run(
            self.cmd,
            input=text,
            capture_output=True,
            text=True,
            env=trace.child_env(),  # 子鏈接上同一條 trace
        )
        if self.check and proc.returncode != 0:
            raise RuntimeError(
                f"subprocess {self.cmd} 失敗 (exit {proc.returncode}): {proc.stderr.strip()}"
            )
        return proc.stdout


class Http:
    """跨網路：POST text 當 body，回 response body。標準庫 urllib，無外部相依。"""

    kind = "http"

    def __init__(self, url: str, method: str = "POST", timeout: float = 30.0,
                 headers: dict | None = None):
        self.url = url
        self.method = method
        self.timeout = timeout
        self.headers = headers or {}

    def call(self, text: str) -> str:
        data = text.encode("utf-8")
        req = urllib.request.Request(
            self.url, data=data, method=self.method, headers=self.headers
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return resp.read().decode("utf-8")


def from_spec(spec: dict, registry: dict[str, Callable[[str], str]] | None = None):
    """由 JSON 設定建 target。

    ``{"kind": "subprocess", "cmd": ["echo.sh"]}``
    ``{"kind": "http", "url": "http://..."}``
    ``{"kind": "in_process", "ref": "name"}``  ← 需在 registry 提供 name→callable
    """
    kind = spec.get("kind")
    if kind == "subprocess":
        return Subprocess(spec["cmd"], check=spec.get("check", True))
    if kind == "http":
        return Http(spec["url"], method=spec.get("method", "POST"),
                    timeout=spec.get("timeout", 30.0), headers=spec.get("headers"))
    if kind == "in_process":
        if not registry or spec["ref"] not in registry:
            raise ValueError(f"in_process target 需要 registry 提供 {spec.get('ref')!r}")
        return InProcess(registry[spec["ref"]])
    raise ValueError(f"未知的 target kind：{kind!r}")


def call(target: Any, text: str) -> str:
    """統一呼叫入口：target 是上面三種之一（鴨子型別，有 .call 即可）。"""
    return target.call(text)


def call_json(target: Any, obj: Any) -> Any:
    """便利函式：兩端用 JSON 編解碼，傳結構化資料。"""
    out = call(target, json.dumps(obj, ensure_ascii=False))
    return json.loads(out)
