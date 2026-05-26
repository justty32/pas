#!/usr/bin/env python3
"""SFC — Small Function Center（依 thinking_sfc.md 的分層架構落地）。

涵蓋 Layer 0 ~ Layer 2，Layer 3/4 留 stub + TODO。

==================== 待設計決策：Layer 0 設定檔格式 ====================
thinking_sfc.md 把 Layer 0 標為「待設計」，只給了概念：
``functions.json``（定義 array/object）+ ``index.json``（name → 位置）。

本 spike 的具體格式選擇（理由附後）：

  store/functions.json   ← object，key 為函式名，value 為函式定義
  store/index.json       ← {"index": {"<name>": "<name>"}}（name → store 內的 key）

函式定義（functions.json 內每個 value）：

    {
      "name": "greet",
      "kind": "python",                 # "python" | "shell"
      "body": "...",                    # python：函式體原始碼；shell：一行 pipe 指令
      "description": "打招呼",
      "metadata": {                     # 沿用 ai_core 軸；tiny function 多為 one_shot/stateless
        "lifecycle": "one_shot",
        "state": "stateless"
      }
    }

兩種 kind 的 body 約定（呼叫介面細節，thinking_sfc.md 另一個待設計項）：
- kind="python"：body 是一個函式體，簽名固定為 ``def _fn(stdin: str, args: dict) -> str``。
  ``stdin`` 為標準輸入文字，``args`` 為剩餘 CLI flag 轉成的 dict。回傳字串即 stdout。
  Layer 2 真正 in-process 執行（compile + exec 到一個受限 namespace）。
- kind="shell"：body 是一段 shell 指令，stdin 餵進去、stdout 收回來。
  SFC 內部開 ``bash -c`` subprocess（thinking_sfc.md：shell pipe 由 SFC 管理 subprocess）。

為何「object（而非 array）+ 獨立 index.json」：
  1. object 以 name 為 key，本身就是 O(1) 查找——index.json 在這個最小格式下其實是
     恆等映射，看似冗餘。但 thinking_sfc.md 明確要求 Layer 0 有 index，且未來 index 會
     擴充（tags / summary / category，見 thinking_routing.md「Indexer 升級版」）。故保留
     index.json 作為「可被獨立擴充的查找層」，functions.json 只存定義本體。spike 先讓
     index 維持恆等映射，但結構上預留升級空間。
  2. 全 JSON、純標準庫可解析，符合 data_format.md §3「JSON 為通用格式」。

==================== 待設計決策：forge server 對外介面 ====================
選用 **stdin/stdout 的「一行一個 JSON request」行協議**（newline-delimited JSON, NDJSON）。
理由：
  - 最 KISS：不需 socket 綁定、不需 http.server、不需 port 管理，純標準庫的
    sys.stdin/sys.stdout 即可。
  - 符合 thinking_pending.md §3「persistent 建議設計成 server」，同時保留升級到 HTTP 的空間
    （該節指出 stdin/stdout JSON-RPC 選項需重新評估——故此處標為 spike 暫定，回報給使用者）。
  - 對外契約：每行一個 ``{"call": "<name>", "stdin": "...", "args": {...}}``；
    server 回一行 ``{"ok": true, "stdout": "..."}`` 或 ``{"ok": false, "error": "..."}``。
  - Layer 3 管理 API（執行期動態操作）：
      {"cmd": "list"}                     列出目前載入的函式
      {"cmd": "add", "defn": {...}}        動態編譯並加入一個 tiny function
      {"cmd": "remove", "name": "..."}     從記憶體移除
      {"cmd": "persist"}                   把目前記憶體中的定義寫回 Layer 0 store
      {"cmd": "shutdown"}                  關閉 server

==================== git-style subcommand CLI ====================
    sfc <funcname> [args]      # 呼叫某 tiny function（Layer 1b：讀檔查表執行）
    sfc --metadata             # SFC 自身 metadata
    sfc <funcname> --metadata  # 該 tiny function 的 metadata（subcommand-scoped）
    sfc intake ...             # Layer 1a：把片段納入 store
    sfc list                   # 列出 store 內所有函式
    sfc forge                  # Layer 2：啟動 persistent server（NDJSON 行協議）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _common import ensure_ai_core_importable, ensure_lib_importable

ensure_ai_core_importable()
ensure_lib_importable()
import ai_core as meta  # noqa: E402  # Gap A/B/F 已扶正進 _core.py：宣告/攔截拆分 + subcommand-scoped
from lib import trace  # noqa: E402  # forge dispatch 的調用鏈追蹤


# ====== Gap A/B/F 的修法（已扶正進 src/ai_core/_core.py）======
# 原本 register() 的 --metadata 攔截要求「--metadata 必須是唯一引數」，與 git-style 的
# `sfc <fn> --metadata` 不相容（Gap A）；register 又在 import 時就讀 argv/攔截/exit（Gap F）。
# 現在 ai_core 已採「宣告/攔截拆分」模型，sfc 直接用真 library（上方 `import ai_core as meta`）：
#   - meta.register(...)              宣告 SFC 頂層 metadata（dispatcher，預設 one_shot）
#   - meta.register_subcommand(...)   讓 forge 宣告成 persistent（解 Gap B：單檔多 lifecycle）
#   - meta.register_subcommand_resolver(...)  tiny function 名稱來自 store → 動態解析
#   - meta.intercept(argv)            純宣告後顯式攔截所有 --metadata 變體；非查詢則交還控制權
# meta_core.py 原型已功成身退並刪除。


def _resolve_tiny_metadata(name: str, store_override: str | None) -> dict | None:
    """動態子命令解析器：tiny function 的 metadata 存在 store，不寫死在程式。"""
    store_dir = Path(store_override) if store_override else DEFAULT_STORE_DIR
    defn = Store(store_dir).get(name)
    return None if defn is None else defn.get("metadata", {})


def _setup_metadata() -> None:
    # 頂層：dispatcher 預設行為
    meta.register(lifecycle="one_shot", state="stateless")
    # 靜態子命令各自的 scoped metadata（forge 是 persistent → 解 Gap B）
    meta.register_subcommand("forge", lifecycle="persistent", state="stateless")
    meta.register_subcommand("intake", lifecycle="one_shot", state="stateful_external")
    meta.register_subcommand("list", lifecycle="one_shot", state="stateless")
    meta.register_subcommand("admin", lifecycle="one_shot", state="stateless")
    # 動態子命令（tiny function 名稱）：交給 resolver 去 store 查
    meta.register_subcommand_resolver(_resolve_tiny_metadata)


# ---------------------------------------------------------------------------
# Layer 0：純資料存取
# ---------------------------------------------------------------------------

DEFAULT_STORE_DIR = Path(__file__).resolve().parents[1] / "store"


class Store:
    """Layer 0 的讀寫封裝：functions.json + index.json。"""

    def __init__(self, store_dir: Path):
        self.dir = store_dir
        self.functions_path = store_dir / "functions.json"
        self.index_path = store_dir / "index.json"

    def load(self) -> tuple[dict, dict]:
        funcs = {}
        index = {}
        if self.functions_path.is_file():
            funcs = json.loads(self.functions_path.read_text(encoding="utf-8"))
        if self.index_path.is_file():
            index = json.loads(self.index_path.read_text(encoding="utf-8")).get("index", {})
        return funcs, index

    def save(self, funcs: dict, index: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.functions_path.write_text(
            json.dumps(funcs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        self.index_path.write_text(
            json.dumps({"index": index}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def get(self, name: str) -> dict | None:
        funcs, index = self.load()
        key = index.get(name, name)
        return funcs.get(key)


# ---------------------------------------------------------------------------
# Layer 4：錯誤處理（標準錯誤封套）+ 資源（timeout）
# ---------------------------------------------------------------------------

class ToolTimeout(Exception):
    """shell-kind tiny function 超過 timeout 時拋出（Layer 4 資源上限）。"""


# 標準錯誤型別（封套的 type 欄位）：
#   bad_json / bad_request / unknown_function / compile_error / runtime_error / timeout
def _err(etype: str, message: str, function: str | None = None) -> dict:
    """產出標準錯誤封套：``{"ok": false, "error": {"type", "message", "function"?}}``。

    取代原本扁平的 ``{"ok": false, "error": "<字串>"}``，讓程式 caller 能依 type 分流
    （例如 timeout 可重試、bad_request 不該重試）。
    """
    err: dict = {"type": etype, "message": message}
    if function is not None:
        err["function"] = function
    return {"ok": False, "error": err}


# ---------------------------------------------------------------------------
# 執行：把一個 tiny function 定義轉成「可呼叫物件」
# ---------------------------------------------------------------------------

def compile_function(defn: dict, shell_timeout: float | None = None):
    """把函式定義編譯成 Python callable：``fn(stdin: str, args: dict) -> str``。

    Layer 2 forge 啟動時對每個函式呼叫一次，存進記憶體 dict。
    Layer 1b 也用它，只是每次呼叫都即時編譯（無快取）。

    ``shell_timeout``（Layer 4）：shell-kind 的 subprocess 逾時秒數；超時拋 ToolTimeout。
    ⚠ python-kind 是真正 in-process（缺口 E），標準庫無法乾淨地設記憶體/時間上限，
    故 timeout **只對 shell-kind 生效**；python-kind 不受保護（這是 Layer 2「真 in-process」
    與 Layer 4「資源上限」的根本張力，見 README 缺口 E）。
    """
    kind = defn.get("kind")
    body = defn.get("body", "")

    if kind == "python":
        # 真正 in-process：把 body 包成函式體，exec 到受限 namespace。
        # 受限：只給少量 builtins，避免 tiny function 亂搞（spike 等級的薄防護，非沙箱）。
        body_lines = ["    " + line for line in body.splitlines()]
        # 邊界：空 body 或只有註解 → 包成 def 後會是 IndentationError（cryptic）。
        # 在這裡明確攔截，給可讀錯誤（intake/forge 都靠 compile 驗證，會看到這訊息）。
        if not any(ln.strip() and not ln.strip().startswith("#") for ln in body_lines):
            raise ValueError("python tiny function 的 body 不可為空（需至少一條語句）")
        src = "\n".join(["def _fn(stdin, args):", *body_lines])
        namespace: dict = {"__builtins__": {
            "len": len, "str": str, "int": int, "float": float,
            "range": range, "list": list, "dict": dict, "sum": sum,
            "sorted": sorted, "min": min, "max": max, "enumerate": enumerate,
            "split": str.split, "print": print,
        }}
        exec(compile(src, f"<tiny:{defn.get('name')}>", "exec"), namespace)
        fn = namespace["_fn"]

        def runner(stdin: str, args: dict) -> str:
            result = fn(stdin, args)
            return "" if result is None else str(result)

        return runner

    if kind == "shell":
        import subprocess

        def runner(stdin: str, args: dict) -> str:
            # SFC 內部開 bash -c subprocess（thinking_sfc.md：shell pipe 由 SFC 管理）
            try:
                proc = subprocess.run(
                    ["bash", "-c", body],
                    input=stdin,
                    capture_output=True,
                    text=True,
                    timeout=shell_timeout,   # Layer 4：超時即殺
                )
            except subprocess.TimeoutExpired:
                raise ToolTimeout(f"shell function 超過 {shell_timeout}s timeout")
            if proc.returncode != 0:
                raise RuntimeError(
                    f"shell tiny function 失敗 (exit {proc.returncode}): {proc.stderr.strip()}"
                )
            return proc.stdout

        return runner

    raise ValueError(f"未知的 kind：{kind!r}（只支援 python / shell）")


# ---------------------------------------------------------------------------
# Layer 1a：intake — 把片段納入 store
# ---------------------------------------------------------------------------

def cmd_intake(args: argparse.Namespace, store: Store) -> int:
    funcs, index = store.load()

    if args.from_json:
        defn = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
    else:
        if not args.name or not args.kind or args.body is None:
            print("錯誤：intake 需要 --name / --kind / --body（或用 --from-json）",
                  file=sys.stderr)
            return 1
        defn = {
            "name": args.name,
            "kind": args.kind,
            "body": args.body,
            "description": args.description or "",
            "metadata": {"lifecycle": "one_shot", "state": "stateless"},
        }

    name = defn["name"]
    # 收進來前先驗證能編譯（fail fast，避免存進壞掉的定義）；給乾淨錯誤而非 traceback
    try:
        compile_function(defn)
    except Exception as exc:  # noqa: BLE001
        print(f"錯誤：{name!r} 編譯失敗，未納入：{exc}", file=sys.stderr)
        return 1

    funcs[name] = defn
    index[name] = name  # 恆等映射（見檔頭格式說明）
    store.save(funcs, index)
    print(f"已納入 {name}（kind={defn['kind']}），store 現有 {len(funcs)} 個函式",
          file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# Layer 1b：Router — 讀檔查表執行單一函式
# ---------------------------------------------------------------------------

def call_function(store: Store, name: str, rest_args: list[str]) -> int:
    defn = store.get(name)
    if defn is None:
        funcs, _ = store.load()
        print(f"錯誤：找不到函式 {name!r}；可用：{sorted(funcs)}", file=sys.stderr)
        return 1

    # 注意：subcommand-scoped --metadata（sfc <name> --metadata）現在由 meta.intercept()
    # 在 main() 最前面就處理掉了（走動態 resolver 查 store），不會走到這裡。

    fn = compile_function(defn)
    stdin_data = "" if sys.stdin.isatty() else sys.stdin.read()
    args_dict = _rest_to_dict(rest_args)
    try:
        out = fn(stdin_data, args_dict)
    except Exception as exc:  # noqa: BLE001
        print(f"函式 {name!r} 執行失敗：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(out)
    if out and not out.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def _rest_to_dict(rest: list[str]) -> dict:
    """把剩餘的 ``--key value`` / ``--flag`` 轉成 dict（Lisp keyword pair → dict，cli_spec §2.0）。"""
    result: dict = {}
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok.startswith("--"):
            key = tok[2:]
            if i + 1 < len(rest) and not rest[i + 1].startswith("--"):
                result[key] = rest[i + 1]
                i += 2
            else:
                result[key] = True  # store_true 風格
                i += 1
        else:
            # bare positional：累積到 "_positional" list
            result.setdefault("_positional", []).append(tok)
            i += 1
    return result


# ---------------------------------------------------------------------------
# Layer 2：forge — persistent server（NDJSON 行協議）
# ---------------------------------------------------------------------------

def cmd_forge(args: argparse.Namespace, store: Store) -> int:
    """啟動時把所有 tiny function 編譯成 callable 存進記憶體 dict，之後純記憶體查表執行。"""
    timeout = getattr(args, "call_timeout", None)  # Layer 4：shell-kind 逾時上限
    funcs, index = store.load()
    compiled: dict = {}
    defns: dict = {}  # name -> 原始定義（Layer 3 persist 要寫回 store，故需保留原始 defn）
    for name in index:
        defn = funcs.get(index[name], funcs.get(name))
        if defn is None:
            continue
        try:
            compiled[name] = (compile_function(defn, shell_timeout=timeout), defn.get("metadata", {}))
            defns[name] = defn
        except Exception as exc:  # noqa: BLE001
            print(f"[forge] 跳過 {name}：編譯失敗 {exc}", file=sys.stderr)

    # ready 訊號（thinking_pending.md §3：server lifecycle 啟動/就緒，spike 用一行 stderr 表示）
    print(f"[forge] ready：載入 {len(compiled)} 個函式 {sorted(compiled)}", file=sys.stderr)
    sys.stderr.flush()

    # 整個 serve 迴圈包在一個 trace span 內 → 成為調用樹的 root；每次 call 是其 child。
    # trace 事件走 stderr（與 [forge] ready/shutdown 同一條），Collector 會略過非 JSON 行。
    with trace.span("forge.serve", stderr=sys.stderr):
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError as exc:
                _respond(_err("bad_json", str(exc)))
                continue

            # 管理 API（Layer 3）：list / add / remove / persist / shutdown
            cmd = req.get("cmd")
            if cmd == "list":
                _respond({"ok": True, "functions": sorted(compiled)})
                continue
            if cmd == "add":
                # 執行期動態載入並編譯新 tiny function，加入記憶體 dict
                defn = req.get("defn")
                if not isinstance(defn, dict) or "name" not in defn:
                    _respond(_err("bad_request", "add 需要 defn（含 name/kind/body）"))
                    continue
                try:
                    nm = defn["name"]
                    compiled[nm] = (compile_function(defn, shell_timeout=timeout),
                                    defn.get("metadata", {}))
                    defns[nm] = defn
                    _respond({"ok": True, "added": nm, "functions": sorted(compiled)})
                except Exception as exc:  # noqa: BLE001
                    _respond(_err("compile_error", str(exc), defn.get("name")))
                continue
            if cmd == "remove":
                nm = req.get("name")
                existed = compiled.pop(nm, None) is not None
                defns.pop(nm, None)
                _respond({"ok": True, "removed": nm, "existed": existed,
                          "functions": sorted(compiled)})
                continue
            if cmd == "persist":
                # 把目前記憶體中的函式定義寫回 Layer 0 store（與 intake 對稱：收進來 vs 存回去）
                store.save(defns, {nm: nm for nm in defns})
                _respond({"ok": True, "persisted": sorted(defns)})
                continue
            if cmd == "shutdown":
                _respond({"ok": True, "shutdown": True})
                break

            name = req.get("call")
            if name not in compiled:
                _respond(_err("unknown_function", f"unknown function: {name}", name))
                continue
            fn, _meta = compiled[name]
            try:
                with trace.span(f"forge.call:{name}", stderr=sys.stderr):
                    out = fn(req.get("stdin", ""), req.get("args", {}))
                _respond({"ok": True, "stdout": out})
            except ToolTimeout as exc:
                _respond(_err("timeout", str(exc), name))       # Layer 4：可重試類錯誤
            except Exception as exc:  # noqa: BLE001
                _respond(_err("runtime_error", f"{type(exc).__name__}: {exc}", name))

    print("[forge] shutdown", file=sys.stderr)
    return 0


def _respond(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Layer 3 / Layer 4：stub
# ---------------------------------------------------------------------------

def cmd_admin(args: argparse.Namespace, store: Store) -> int:
    # Layer 3 動態管理 API 已實作於 forge 的 NDJSON 協議（list / add / remove / persist）。
    # 這個 sfc admin 子命令只是個指路牌——管理操作請對 running 的 forge server 發 NDJSON。
    # TODO(Layer 4): 資源管理（記憶體/時間上限）、錯誤處理標準化、retry 機制——仍未做。
    print("Layer 3 動態管理 API 在 forge：對 `sfc forge` 發 "
          '{"cmd":"add"|"remove"|"persist"|"list"}。Layer 4（資源/錯誤處理）仍為 TODO。',
          file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# CLI 進入點：git-style subcommand
# ---------------------------------------------------------------------------

# 保留字（內建子命令）；其餘字串視為 tiny function 名稱
_BUILTIN_SUBCOMMANDS = {"intake", "list", "forge", "admin"}


def main() -> int:
    argv = sys.argv[1:]

    # 先設定 metadata 登記，再讓 meta_core 統一攔截所有 --metadata 變體：
    #   sfc --metadata / sfc <builtin> --metadata / sfc <tinyfn> --metadata
    # 命中則輸出並 exit；非 metadata 查詢則 return，往下走一般 dispatch。
    _setup_metadata()
    meta.intercept(argv)

    if not argv:
        print("用法：sfc <funcname|intake|list|forge|admin> [args]", file=sys.stderr)
        print("      sfc --metadata / sfc <funcname> --metadata", file=sys.stderr)
        return 1

    # store 目錄可由 SFC_STORE 環境變數或 --store 覆寫；簡化起見先支援 --store（須在最前）
    store_dir = DEFAULT_STORE_DIR
    if argv and argv[0] == "--store":
        store_dir = Path(argv[1])
        argv = argv[2:]
    store = Store(store_dir)

    sub = argv[0]
    rest = argv[1:]

    if sub == "intake":
        return _dispatch_intake(rest, store)
    if sub == "list":
        funcs, index = store.load()
        print(json.dumps({"functions": sorted(index or funcs)}, ensure_ascii=False))
        return 0
    if sub == "forge":
        return cmd_forge(_parse_forge(rest), store)
    if sub == "admin":
        return cmd_admin(_parse_empty(rest), store)

    # 否則視為 tiny function 名稱（Layer 1b）
    return call_function(store, sub, rest)


def _dispatch_intake(rest: list[str], store: Store) -> int:
    p = argparse.ArgumentParser(prog="sfc intake")
    p.add_argument("--name")
    p.add_argument("--kind", choices=["python", "shell"])
    p.add_argument("--body")
    p.add_argument("--description")
    p.add_argument("--from-json", dest="from_json")
    return cmd_intake(p.parse_args(rest), store)


def _parse_forge(rest: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="sfc forge")
    p.add_argument("--call-timeout", type=float, default=None,
                   help="shell-kind tiny function 的逾時秒數（Layer 4；超時回 timeout 錯誤）")
    return p.parse_args(rest)


def _parse_empty(rest: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="sfc admin")
    return p.parse_args(rest)


if __name__ == "__main__":
    sys.exit(main())
