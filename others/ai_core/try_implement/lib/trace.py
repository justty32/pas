#!/usr/bin/env python3
"""trace — 調用鏈追蹤（輕量方案）。

對應 thinking_pending.md §5「調用鏈設計」。採該節點名的「輕量方案」：每個工具在
stderr 輸出結構化 JSON log，成本接近零，由最外層 caller 決定是否收集。

調用鏈在 shell 世界 = process 與其子 process / pipeline 前後節點。本 library 提供：
    1. trace id 傳遞：透過環境變數讓整條鏈共享同一個 trace id（§5「待設計」之一）
    2. span 事件：每段工作往 stderr 印 start/end JSON
    3. Collector：把散落的 stderr JSON log 重組成調用樹（§5「收集工具」）

== trace id 傳遞機制 ==
環境變數兩個：
    AI_CORE_TRACE  整條鏈共享的 trace id
    AI_CORE_SPAN   呼叫方的 span id；本工具的 span 以它為 parent
工具啟動時讀 AI_CORE_TRACE（無則自己生一個 = 此工具是鏈頭）。要 spawn 子 process 時，
用 child_env() 把 AI_CORE_TRACE 原樣帶下、AI_CORE_SPAN 設為自己的 span id，子鏈即可
接上同一棵樹。

== 設計決策 ==
1. 純 stderr + env，零外部相依、零協調成本，完全符合 §5「輕量方案，成本接近零」。
2. 事件格式扁平 JSON，一行一個，方便 grep / 串流收集。
3. Collector 容忍亂序與缺漏（被 kill 的 span 可能沒有 end）：以 span/parent 重建樹，
   缺 end 的標 incomplete。
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from contextlib import contextmanager
from typing import Any, TextIO

ENV_TRACE = "AI_CORE_TRACE"
ENV_SPAN = "AI_CORE_SPAN"


def current_trace() -> str:
    """目前的 trace id；環境沒有就生一個新的（= 本 process 是鏈頭）。"""
    tid = os.environ.get(ENV_TRACE)
    if not tid:
        tid = uuid.uuid4().hex[:12]
        os.environ[ENV_TRACE] = tid
    return tid


def parent_span() -> str | None:
    return os.environ.get(ENV_SPAN) or None


def _emit(err: TextIO, event: str, span: str, name: str, **fields: Any) -> None:
    rec = {
        "trace": current_trace(),
        "span": span,
        "parent": parent_span(),
        "name": name,
        "event": event,
        "ts": round(time.time(), 6),
    }
    rec.update(fields)
    print(json.dumps(rec, ensure_ascii=False), file=err)
    err.flush()


@contextmanager
def span(name: str, stderr: TextIO | None = None, **fields: Any):
    """包住一段工作：印 start，離開時印 end（含 duration）。

    在 with 區塊內，本 span 成為 AI_CORE_SPAN，spawn 的子 process（用 child_env）會
    把它當 parent。離開後還原原本的 AI_CORE_SPAN。
    """
    err = sys.stderr if stderr is None else stderr
    sid = uuid.uuid4().hex[:8]
    t0 = time.time()
    _emit(err, "start", sid, name, **fields)
    prev = os.environ.get(ENV_SPAN)
    os.environ[ENV_SPAN] = sid
    try:
        yield sid
    finally:
        if prev is None:
            os.environ.pop(ENV_SPAN, None)
        else:
            os.environ[ENV_SPAN] = prev
        _emit(err, "end", sid, name, duration=round(time.time() - t0, 6))


def child_env(base: dict | None = None) -> dict:
    """產出給 subprocess 的環境：帶上 trace id 與「以目前 span 為 parent」。"""
    env = dict(os.environ if base is None else base)
    env[ENV_TRACE] = current_trace()
    sid = os.environ.get(ENV_SPAN)
    if sid:
        env[ENV_SPAN] = sid
    return env


class Collector:
    """把 stderr JSON log 重組成調用樹。"""

    def __init__(self):
        self._starts: dict[str, dict] = {}
        self._ends: dict[str, dict] = {}

    def add_line(self, line: str) -> None:
        line = line.strip()
        if not line:
            return
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            return  # 非追蹤行（一般 log）直接略過
        if "span" not in rec or "event" not in rec:
            return
        if rec["event"] == "start":
            self._starts[rec["span"]] = rec
        elif rec["event"] == "end":
            self._ends[rec["span"]] = rec

    def add_text(self, text: str) -> None:
        for line in text.splitlines():
            self.add_line(line)

    def tree(self) -> list[dict]:
        """回傳 root 節點列表，每個節點含 name/span/complete/duration/children。"""
        nodes: dict[str, dict] = {}
        for sid, s in self._starts.items():
            end = self._ends.get(sid)
            nodes[sid] = {
                "span": sid,
                "name": s.get("name"),
                "parent": s.get("parent"),
                "complete": end is not None,
                "duration": (end or {}).get("duration"),
                "children": [],
            }
        roots: list[dict] = []
        for sid, node in nodes.items():
            parent = node["parent"]
            if parent and parent in nodes:
                nodes[parent]["children"].append(node)
            else:
                roots.append(node)
        return roots

    def render(self) -> str:
        """把調用樹畫成縮排文字。"""
        lines: list[str] = []

        def walk(node: dict, depth: int) -> None:
            mark = "" if node["complete"] else "  ⚠ incomplete"
            dur = f" ({node['duration']}s)" if node["duration"] is not None else ""
            lines.append("  " * depth + f"- {node['name']}{dur}{mark}")
            for c in node["children"]:
                walk(c, depth + 1)

        for r in self.tree():
            walk(r, 0)
        return "\n".join(lines)
