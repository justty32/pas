#!/usr/bin/env python3
"""端到端示範：把 sfc forge 的 dispatch 調用鏈重建成樹（lib/trace 落地）。

sfc forge 現在 dispatch 時會發 trace span（forge.serve 為 root，每次 forge.call:<name>
為其 child），事件走 stderr。本 demo：
  1. 以 subprocess 跑 sfc forge，餵幾個 call 請求，收集它的 stderr
  2. 用 trace.Collector 把 stderr 裡的 trace 事件重組成調用樹並印出
  3. 自我測試：樹根是 forge.serve，子節點含 forge.call:shout / forge.call:wc_words

執行：python3 demos/call_chain_trace.py

（另：router dispatch 也已用 trace.child_env() 把 trace id 帶給子 process——若被路由的
目標也是 trace-aware，其 span 會接上同一棵樹。跨 process 的樹組裝需由外層收集子 process
的 stderr，與此處同理。）
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_TRY = _HERE.parent
if str(_TRY) not in sys.path:
    sys.path.insert(0, str(_TRY))

from lib import trace

TOOLS = _TRY / "tools"


def run() -> dict:
    requests = "\n".join([
        json.dumps({"call": "shout", "stdin": "hi"}),
        json.dumps({"call": "wc_words", "stdin": "a b c"}),
        json.dumps({"cmd": "shutdown"}),
    ]) + "\n"
    proc = subprocess.run(
        [sys.executable, str(TOOLS / "sfc.py"), "forge"],
        input=requests, capture_output=True, text=True, cwd=str(_TRY),
    )
    col = trace.Collector()
    col.add_text(proc.stderr)        # forge 的 trace 事件都在 stderr
    return {"tree": col.tree(), "rendered": col.render(),
            "responses": [json.loads(l) for l in proc.stdout.splitlines() if l.strip()]}


def main() -> int:
    r = run()
    print("=== sfc forge 調用鏈重建 demo ===\n")
    print("forge 處理了這些請求並回應：")
    for resp in r["responses"]:
        print(f"  {json.dumps(resp, ensure_ascii=False)}")
    print("\n從 forge stderr 的 trace 事件重建的調用樹：\n")
    print(r["rendered"])

    tree = r["tree"]
    assert len(tree) == 1, f"應只有一個 root，得到 {len(tree)}"
    root = tree[0]
    assert root["name"] == "forge.serve", f"root 應為 forge.serve，得到 {root['name']}"
    child_names = {c["name"] for c in root["children"]}
    assert {"forge.call:shout", "forge.call:wc_words"} <= child_names, \
        f"子節點應含兩次 call，得到 {child_names}"
    assert all(c["complete"] for c in root["children"]), "每次 call 都應有完整 start/end"
    print("\n=== 調用樹重建正確 ✓ ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
