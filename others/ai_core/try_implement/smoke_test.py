#!/usr/bin/env python3
"""smoke_test.py — 跑通 indexer → router → switch → sfc 的端到端煙霧測試。

不依賴 pytest：純 ``assert`` + ``__main__`` 入口。實際造範例 tiny function、
實際以 subprocess 呼叫各工具，驗證它們能動。

執行：
    python3 smoke_test.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE / "tools"
PY = sys.executable

_passed = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global _passed
    assert cond, f"[FAIL] {label}\n  {detail}"
    _passed += 1
    print(f"[PASS] {label}")


def run(cmd: list[str], stdin: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, input=stdin, capture_output=True, text=True, env=env, cwd=str(HERE)
    )


# ---------------------------------------------------------------------------
# 0. 各工具的 --metadata 契約
# ---------------------------------------------------------------------------

def test_metadata_contract() -> None:
    for tool in ("indexer.py", "router.py", "switch.py", "sfc.py"):
        proc = run([PY, str(TOOLS / tool), "--metadata"])
        check(
            f"{tool} --metadata 回傳合法 JSON 且 exit 0",
            proc.returncode == 0,
            f"rc={proc.returncode} stderr={proc.stderr}",
        )
        meta = json.loads(proc.stdout)
        check(
            f"{tool} metadata 含 lifecycle",
            "lifecycle" in meta,
            f"meta={meta}",
        )


# ---------------------------------------------------------------------------
# 1. Indexer：掃 funcs/ 並彙整 metadata
# ---------------------------------------------------------------------------

def test_indexer() -> None:
    proc = run([PY, str(TOOLS / "indexer.py"), "--dir", "funcs", "--format", "json"])
    check("indexer 掃描 funcs/ exit 0", proc.returncode == 0, proc.stderr)
    index = json.loads(proc.stdout)
    names = set(index["functions"])
    # funcs/ 內有 upper.py / c_linter.sh / py_linter.sh
    check("indexer 找到 upper.py", "upper.py" in names, f"names={names}")
    check("indexer 找到 c_linter.sh", "c_linter.sh" in names, f"names={names}")
    check(
        "indexer 抓到 upper.py 的 lifecycle=one_shot",
        index["functions"]["upper.py"]["metadata"]["lifecycle"] == "one_shot",
        f"{index['functions']['upper.py']}",
    )
    # markdown 格式也要能跑
    proc_md = run([PY, str(TOOLS / "indexer.py"), "--dir", "funcs", "--format", "md"])
    check("indexer markdown 格式 exit 0", proc_md.returncode == 0, proc_md.stderr)
    check("indexer markdown 含標題", "# 函式索引" in proc_md.stdout, proc_md.stdout[:80])


# ---------------------------------------------------------------------------
# 2. Router：查表後 dispatch
# ---------------------------------------------------------------------------

def test_router() -> None:
    proc = run(
        [PY, str(TOOLS / "router.py"), "--routes", "routes.json", "upper"],
        stdin="hello world",
    )
    check("router 路由 upper 並執行 exit 0", proc.returncode == 0, proc.stderr)
    check("router→upper 把輸入轉大寫", proc.stdout.strip() == "HELLO WORLD", repr(proc.stdout))

    # --list
    proc_list = run([PY, str(TOOLS / "router.py"), "--routes", "routes.json", "--list"])
    routes = json.loads(proc_list.stdout)["routes"]
    check("router --list 列出 upper/c_lint/py_lint",
          {"upper", "c_lint", "py_lint"} <= set(routes), f"routes={routes}")

    # 不存在的 name → exit 1
    proc_miss = run([PY, str(TOOLS / "router.py"), "--routes", "routes.json", "nonexistent"])
    check("router 對不存在的 name 回 exit 1", proc_miss.returncode == 1, proc_miss.stderr)


# ---------------------------------------------------------------------------
# 3. Switch：依條件分支
# ---------------------------------------------------------------------------

def test_switch() -> None:
    # lang=c → c_linter
    proc_c = run(
        [PY, str(TOOLS / "switch.py"), "--config", "switch.json", "--lang", "c"],
        stdin="int main(){}",
    )
    check("switch lang=c exit 0", proc_c.returncode == 0, proc_c.stderr)
    check("switch lang=c → c_linter", "[c_linter]" in proc_c.stdout, repr(proc_c.stdout))

    # lang=python → py_linter
    proc_py = run(
        [PY, str(TOOLS / "switch.py"), "--config", "switch.json", "--lang", "python"],
        stdin="print('hi')",
    )
    check("switch lang=python → py_linter", "[py_linter]" in proc_py.stdout, repr(proc_py.stdout))

    # --explain 顯示路由決策
    proc_x = run(
        [PY, str(TOOLS / "switch.py"), "--config", "switch.json", "--lang", "python", "--explain"]
    )
    decision = json.loads(proc_x.stdout)
    check("switch --explain 顯示 value=python", decision["value"] == "python", str(decision))

    # default 分支（lang=未知）
    proc_d = run(
        [PY, str(TOOLS / "switch.py"), "--config", "switch.json", "--lang", "rust", "--explain"]
    )
    dec_d = json.loads(proc_d.stdout)
    check("switch 未知 lang 走 default", dec_d["target"]["path"] == "funcs/c_linter.sh", str(dec_d))


# ---------------------------------------------------------------------------
# 4. SFC：Layer 0 / 1a intake / 1b call / 2 forge
# ---------------------------------------------------------------------------

def test_sfc() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="sfc_store_"))
    try:
        sfc = [PY, str(TOOLS / "sfc.py"), "--store", str(tmp)]

        # 4a. intake 一個 python tiny function（轉大寫 + 驚嘆號）
        py_body = "return stdin.strip().upper() + '!'"
        proc = run(sfc + ["intake", "--name", "shout", "--kind", "python",
                          "--body", py_body, "--description", "大吼"])
        check("sfc intake python func exit 0", proc.returncode == 0, proc.stderr)
        check("store/functions.json 已建立", (tmp / "functions.json").is_file())
        check("store/index.json 已建立", (tmp / "index.json").is_file())

        # 邊界（自我審查發現的 bug）：空 body 應被乾淨拒絕，而非 cryptic IndentationError traceback
        proc = run(sfc + ["intake", "--name", "empty", "--kind", "python", "--body", ""])
        check("sfc intake 拒絕空 body（exit 1）", proc.returncode == 1, proc.stderr)
        check("空 body 給可讀錯誤（非 traceback）",
              "不可為空" in proc.stderr and "Traceback" not in proc.stderr, proc.stderr)

        # 4b. intake 一個 shell tiny function（wc -w 數字數）
        proc = run(sfc + ["intake", "--name", "wc_words", "--kind", "shell",
                          "--body", "wc -w | tr -d ' '", "--description", "數字數"])
        check("sfc intake shell func exit 0", proc.returncode == 0, proc.stderr)

        # 4c. list
        proc = run(sfc + ["list"])
        funcs = json.loads(proc.stdout)["functions"]
        check("sfc list 含 shout / wc_words",
              {"shout", "wc_words"} <= set(funcs), f"funcs={funcs}")

        # 4d. Layer 1b 呼叫 python tiny function（in-process）
        proc = run(sfc + ["shout"], stdin="hello")
        check("sfc shout（python in-process）exit 0", proc.returncode == 0, proc.stderr)
        check("sfc shout 輸出 HELLO!", proc.stdout.strip() == "HELLO!", repr(proc.stdout))

        # 4e. Layer 1b 呼叫 shell tiny function（subprocess）
        proc = run(sfc + ["wc_words"], stdin="one two three four")
        check("sfc wc_words（shell subprocess）exit 0", proc.returncode == 0, proc.stderr)
        check("sfc wc_words 數出 4", proc.stdout.strip() == "4", repr(proc.stdout))

        # 4f. subcommand-scoped --metadata（動態 resolver 查 store → Gap A 修法）
        proc = run(sfc + ["shout", "--metadata"])
        check("sfc shout --metadata exit 0（Gap A 修法：不再被 register 攔截）",
              proc.returncode == 0, proc.stderr)
        meta = json.loads(proc.stdout)
        check("sfc shout --metadata 回傳該函式 metadata",
              meta.get("lifecycle") == "one_shot", str(meta))

        # 4f2. 頂層 --metadata（dispatcher 預設 one_shot）
        proc = run(sfc + ["--metadata"])
        check("sfc --metadata（頂層）exit 0", proc.returncode == 0, proc.stderr)
        check("sfc 頂層 metadata = one_shot dispatcher",
              json.loads(proc.stdout).get("lifecycle") == "one_shot", proc.stdout)

        # 4f3. forge 子命令 scoped metadata = persistent（Gap B：單檔多 lifecycle）
        proc = run(sfc + ["forge", "--metadata"])
        check("sfc forge --metadata exit 0", proc.returncode == 0, proc.stderr)
        check("sfc forge metadata = persistent（與頂層 one_shot 不同）",
              json.loads(proc.stdout).get("lifecycle") == "persistent", proc.stdout)

        # 4f4. intake 子命令 scoped metadata = stateful_external
        proc = run(sfc + ["intake", "--metadata"])
        check("sfc intake metadata = stateful_external",
              json.loads(proc.stdout).get("state") == "stateful_external", proc.stdout)

        # 4f5. 不存在的子命令/函式 --metadata → exit 1
        proc = run(sfc + ["nope_no_such", "--metadata"])
        check("sfc <未知> --metadata → exit 1", proc.returncode == 1, proc.stderr)

        # 4g. 不存在的函式（一般呼叫）→ exit 1
        proc = run(sfc + ["does_not_exist"])
        check("sfc 對不存在函式回 exit 1", proc.returncode == 1, proc.stderr)

        # 4h. Layer 2 forge：persistent server，NDJSON 行協議
        requests = "\n".join([
            json.dumps({"cmd": "list"}),
            json.dumps({"call": "shout", "stdin": "forge"}),
            json.dumps({"call": "wc_words", "stdin": "a b c"}),
            json.dumps({"call": "ghost", "stdin": ""}),  # 不存在
            json.dumps({"cmd": "shutdown"}),
        ]) + "\n"
        proc = run(sfc + ["forge"], stdin=requests)
        check("sfc forge exit 0", proc.returncode == 0, proc.stderr)
        lines = [json.loads(l) for l in proc.stdout.splitlines() if l.strip()]
        # 預期 5 個回應：list / shout / wc_words / ghost / shutdown
        check("forge 回應 5 行", len(lines) == 5, f"lines={lines}")
        check("forge cmd=list 列出函式",
              set(lines[0]["functions"]) >= {"shout", "wc_words"}, str(lines[0]))
        check("forge 記憶體查表呼叫 shout → FORGE!",
              lines[1]["ok"] and lines[1]["stdout"].strip() == "FORGE!", str(lines[1]))
        check("forge 呼叫 shell wc_words → 3",
              lines[2]["ok"] and lines[2]["stdout"].strip() == "3", str(lines[2]))
        check("forge 對不存在函式回 ok=false",
              lines[3]["ok"] is False, str(lines[3]))
        check("forge shutdown 回 shutdown=true",
              lines[4].get("shutdown") is True, str(lines[4]))

        # 4i. Router 也能指向 SFC 的 store 函式嗎？（驗證 router/sfc 職責分離說明）
        # router 只支援 exec；要呼叫 store 函式需透過 sfc。這裡確認 router 對 store 片段
        # 不負責——是預期行為，非 bug。（記錄於 README 缺口回報）

        # 4j. Layer 3 動態管理 API：add / remove / persist（forge NDJSON）
        l3 = "\n".join([
            json.dumps({"cmd": "add", "defn": {
                "name": "rev", "kind": "python", "body": "return stdin.strip()[::-1]",
                "metadata": {"lifecycle": "one_shot", "state": "stateless"}}}),
            json.dumps({"call": "rev", "stdin": "abc"}),       # 用剛加的函式
            json.dumps({"cmd": "remove", "name": "shout"}),    # 移除一個既有的
            json.dumps({"cmd": "list"}),
            json.dumps({"cmd": "persist"}),                    # 寫回 store
            json.dumps({"cmd": "shutdown"}),
        ]) + "\n"
        proc = run(sfc + ["forge"], stdin=l3)
        lines = [json.loads(l) for l in proc.stdout.splitlines() if l.strip()]
        check("forge add 動態加入 rev", lines[0]["ok"] and "rev" in lines[0]["functions"], str(lines[0]))
        check("forge 立刻能呼叫剛加的 rev", lines[1].get("stdout", "").strip() == "cba", str(lines[1]))
        check("forge remove 移除 shout", lines[2]["existed"] is True, str(lines[2]))
        check("forge list 反映增刪（有 rev 無 shout）",
              "rev" in lines[3]["functions"] and "shout" not in lines[3]["functions"], str(lines[3]))
        check("forge persist 回報已存", "rev" in lines[4]["persisted"], str(lines[4]))
        # persist 後讀磁碟上的 store，確認真的寫回了
        on_disk = json.loads((tmp / "functions.json").read_text(encoding="utf-8"))
        check("persist 後磁碟 store 含 rev、不含 shout",
              "rev" in on_disk and "shout" not in on_disk, str(sorted(on_disk)))

        # 4k. Layer 4：shell-kind timeout + 標準錯誤封套
        run(sfc + ["intake", "--name", "slow", "--kind", "shell", "--body", "sleep 2"])
        l4 = "\n".join([
            json.dumps({"call": "slow", "stdin": ""}),       # 會超過 0.3s timeout
            json.dumps({"call": "nope_fn", "stdin": ""}),    # 不存在 → 結構化錯誤
            json.dumps({"cmd": "shutdown"}),
        ]) + "\n"
        proc = run(sfc + ["forge", "--call-timeout", "0.3"], stdin=l4)
        lines = [json.loads(l) for l in proc.stdout.splitlines() if l.strip()]
        check("Layer 4 shell 超時回 timeout 錯誤封套",
              lines[0]["ok"] is False and lines[0]["error"]["type"] == "timeout", str(lines[0]))
        check("Layer 4 錯誤封套含 function 欄位",
              lines[0]["error"].get("function") == "slow", str(lines[0]))
        check("Layer 4 unknown_function 也是結構化封套",
              lines[1]["error"]["type"] == "unknown_function", str(lines[1]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# 5. Hub：掃描 → skill 清單 + budget 收斂
# ---------------------------------------------------------------------------

def test_hub() -> None:
    proc = run([PY, str(TOOLS / "hub.py"), "--metadata"])
    check("hub --metadata exit 0", proc.returncode == 0, proc.stderr)

    proc = run([PY, str(TOOLS / "hub.py"), "--scan", "funcs", "--format", "json"])
    data = json.loads(proc.stdout)
    check("hub 掃出 4 個 skill", data["count"] == 4, str(data))
    names = {s["name"] for s in data["skills"]}
    check("hub skill 含 upper.py / reverse.py", {"upper.py", "reverse.py"} <= names, str(names))

    # budget 收斂：極小預算 → 應出現「未列出」省略說明
    proc = run([PY, str(TOOLS / "hub.py"), "--scan", "funcs", "--budget", "60"])
    check("hub budget 過小時收斂並標註省略", "未列出" in proc.stdout, proc.stdout)


# ---------------------------------------------------------------------------
# 6. LLM Entry Manager：singleton 資源（consume rate 守門）
# ---------------------------------------------------------------------------

def test_entry_manager() -> None:
    em = [PY, str(TOOLS / "llm_entry_manager.py")]
    proc = run(em + ["--metadata"])
    meta = json.loads(proc.stdout)
    check("entry_manager metadata = persistent", meta.get("lifecycle") == "persistent", str(meta))
    check("entry_manager 宣告 singleton 資源",
          meta.get("resources", {}).get("singleton") is True, str(meta))

    requests = "\n".join([
        json.dumps({"cmd": "complete", "prompt": "hello world"}),
        json.dumps({"cmd": "usage"}),
        json.dumps({"cmd": "complete", "prompt": "x" * 80}),  # 會超預算
        json.dumps({"cmd": "shutdown"}),
    ]) + "\n"
    proc = run(em + ["--limit-token", "8"], stdin=requests)
    lines = [json.loads(l) for l in proc.stdout.splitlines() if l.strip()]
    check("entry_manager complete 回 text + usage",
          lines[0]["ok"] and "text" in lines[0] and lines[0]["usage"]["token"] > 0, str(lines[0]))
    check("entry_manager usage 查詢", "limits" in lines[1], str(lines[1]))
    check("entry_manager 超預算 → rate limit exceeded（consume rate 守門）",
          lines[2]["ok"] is False and "rate limit" in lines[2]["error"], str(lines[2]))


# ---------------------------------------------------------------------------
# 7. chain：宣告式管線（組合維度的 CLI）
# ---------------------------------------------------------------------------

def test_chain() -> None:
    proc = run([PY, str(TOOLS / "chain.py"), "--metadata"])
    check("chain --metadata exit 0", proc.returncode == 0, proc.stderr)

    # 跑管線：upper → reverse，"hi" → "HI" → "IH"（stdout 必須乾淨，trace 在 stderr）
    proc = run([PY, str(TOOLS / "chain.py"), "--spec", "chain_demo.json"], stdin="hi")
    check("chain 跑管線 upper→reverse 得 IH", proc.stdout.strip() == "IH", repr(proc.stdout))

    # derive：從各 stage --metadata 推導複合 metadata
    proc = run([PY, str(TOOLS / "chain.py"), "--spec", "chain_demo.json", "--derive"])
    derived = json.loads(proc.stdout)
    check("chain derive 複合 lifecycle=one_shot", derived["lifecycle"] == "one_shot", str(derived))
    check("chain derive 複合 guarantee=none（最弱）", derived["guarantee"] == "none", str(derived))


def main() -> int:
    print("=== try_implement 煙霧測試開始 ===\n")
    test_metadata_contract()
    test_indexer()
    test_router()
    test_switch()
    test_sfc()
    test_hub()
    test_entry_manager()
    test_chain()
    print(f"\n=== 全部通過：{_passed} 項斷言 ===")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
