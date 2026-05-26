# try_implement — ai_core 概念的探索性實作遊樂場

這是一個**試水溫的原型遊樂場**，把 ai_core 的各種概念「先寫出來跑跑看」。
不是最終定案——目的是讓概念落地成可執行程式碼，並在過程中暴露設計缺口、拓展新概念。
全程只用 **Python 3.11+ 標準庫**（argparse / json / subprocess / pathlib / urllib…），
無任何外部相依，遵守 ai_core 的設計哲學（KISS / Lightweight / No wheel-remake / Least dependency）。

> ⚠️ 範圍：本資料夾下多數東西仍是提案 / 實驗。**例外（2026-05-26 已扶正）**：A1/A2/A3
> （register 的「宣告／攔截拆分」）與 C（`nondeterministic` 第九軸）已**進入** `src/ai_core/_core.py`
> 與 `core_nature/` 規範——見 [`DECISIONS.md`](DECISIONS.md) 頂部「✅ 已收斂」。其餘待扶正項仍由
> 使用者定奪。

涵蓋三大塊：

1. **路由 / 函式管理工具**（`tools/`）：Indexer、Router、Switch、SFC、Hub、LLM Entry Manager。
2. **可重用 library**（`lib/`）：複合規範的參考實作（state_dirs / recovery / memoize）、
   基礎設施（server / singleton / trace / call）、LLM 包裝（llm_call）、以及**八軸之外的
   組合維度**（compose）。
3. **概念拓展文件**（`docs/`）：多函數交互、LLM 隨機性馴化框架。

兩套煙霧測試合計 **140 項斷言全綠**（`smoke_test.py` 72 + `lib_smoke_test.py` 68），外加三個可跑 demo。

> 📋 **回來先讀 [`DECISIONS.md`](DECISIONS.md)** —— 把這裡所有「回饋規範」的發現收斂成一頁
> 決策清單（每項標「待你決定 X 還是 Y」），是對你細調 `core_nature/` 規範最直接有用的入口。

---

## 建了什麼（檔案職責）

| 路徑 | 職責 |
|---|---|
| `tools/indexer.py` | **Indexer**。掃描資料夾的可執行檔，逐一呼叫 `--metadata`，彙整成靜態索引（JSON / markdown）。One-shot、stateless。 |
| `tools/router.py` | **Router**（thinking_sfc Layer 1b）。讀 JSON 設定檔，name → 可執行物 mapping，subprocess dispatch（透傳 stdin/stdout/exit code）。One-shot、stateless。 |
| `tools/switch.py` | **Switch**。有條件邏輯的 router；依「switch 變數值」走規則表分支到不同 target。One-shot、stateless。 |
| `tools/sfc.py` | **SFC（Small Function Center）**。Layer 0（store）/ 1a（intake）/ 1b（router）/ 2（forge server）/ **3（動態 add/remove/persist）/ 4（shell-kind timeout + 標準錯誤封套）**。git-style subcommand CLI。**已改接真 `ai_core`（宣告/攔截拆分，`import ai_core as meta`）解 Gap A/B/F；forge dispatch 已 trace-aware。** |
| ~~`tools/meta_core.py`~~ | **已刪除（2026-05-26）**。其「放寬攔截 + `register_subcommand` + resolver」已扶正進 `src/ai_core/_core.py`，原型功成身退。 |
| `tools/hub.py` | **Function Hub**（規範未定，本版自定義）。掃描函式 → 轉成「給 LLM 的 skill 清單」，含 context budget 逐級收斂。 |
| `tools/llm_entry_manager.py` | **LLM Entry Manager**（CLAUDE.md 元件 1）。singleton 資源 = persistent server（lib/server）+ consume rate（lib/singleton）+ mock backend（lib/llm_call）。 |
| `tools/chain.py` | **chain**（組合維度的 CLI）。用 JSON 宣告 pipeline，stdin 依序流過各 stage；`--derive` 用 compose_meta 從各 stage 的 `--metadata` 推導複合 metadata。串起 call+compose+trace+compose_meta。 |
| `tools/_common.py` | 共用小工具：把 `src/`（`import ai_core`）與 try_implement 根（`from lib import ...`）加進 `sys.path`。 |
| `funcs/upper.py` | 範例「函式」：轉大寫。用 `ai_core.register()` 宣告 metadata。 |
| `funcs/reverse.py` | 範例「函式」：反轉 stdin。chain demo 的第二段。 |
| `funcs/c_linter.sh` / `funcs/py_linter.sh` | 範例 shell「函式」：switch demo 用的假 linter，手寫 `--metadata` JSON。 |
| `routes.json` | router 的路由設定檔範例。 |
| `switch.json` | switch 的條件設定檔範例。 |
| `store/functions.json` + `store/index.json` | SFC Layer 0 的預設 store（已 seed 兩個範例函式 `shout` / `wc_words`）。 |
| `smoke_test.py` | 工具端到端煙霧測試（72 斷言）。純 `assert` + `__main__`，不依賴 pytest。 |
| `lib_smoke_test.py` | lib/ 各模組煙霧測試（68 斷言）。含真實 HTTP round-trip、所有馴化組合子、actor-critic 交互、軸推導、recovery 三模式、incomplete span。 |

### `lib/`（可重用 library）

| 路徑 | 對應規範 / 概念 | 職責 |
|---|---|---|
| `lib/state_dirs.py` | composite_spec「標準狀態目錄慣例」 | 解析 `.config`/`.cache`/`.state`/`.data` 路徑、單檔 JSON 讀寫、`declared()` 產 register 片段。 |
| `lib/recovery.py` | composite_spec「中斷恢復慣例」 | `recovery.json` manifest、resume/rollback/reset 偵測、標準啟動演算法、`session()` context manager。 |
| `lib/memoize.py` | session_resume「記憶化慣例」（**尚未定案**） | `.cache/<name>/<hash>` 輸入→輸出快取；自行拍板 key 組成 / 失效策略，附決策理由。 |
| `lib/server.py` | thinking_pending §3 | persistent server 標準 lifecycle（NDJSON）；forge 的迴圈泛化版。 |
| `lib/singleton.py` | thinking_pending §4 | singleton 資源：RateMeter（多維 consume）+ RequestQueue（enqueue/dequeue/cancel）+ SingletonResource。 |
| `lib/trace.py` | thinking_pending §5 | 調用鏈：結構化 stderr log + trace id 經 env 傳遞 + Collector 重建調用樹。 |
| `lib/call.py` | thinking_pending §6 / thinking_oop | 跨邊界統一呼叫：InProcess / Subprocess / Http 同一個 `call(text)->text`。 |
| `lib/llm_call.py` | CLAUDE.md 元件 2 | `llm_call(str)->str` 基底 + `bind()` context packing；可插拔 backend（預設 mock）。 |
| `lib/compose.py` | **八軸之外的組合維度** | 多函數合作組合子：pipe / fanout / route / decompose + 馴化隨機性的 retry_until_valid / vote / best_of / guard。 |
| `lib/interact.py` | **多函數交互**（組合維度的「來回」版） | 黑板 driver（`run`）+ actor_critic（LLM-as-judge）+ debate；`max_rounds` 強制安全閥防無限互踢。 |
| `lib/compose_meta.py` | **組合的軸推導規則**（候選新概念） | `MetaFn` + `mpipe`/`mfanout_reduce`：從成員八軸推導複合函式 metadata（guarantee 取最弱、state/dirs 聯集、persistent 相依、fanout 寫衝突偵測）；`mretry` 強制 idempotent 前置契約。 |

### `docs/`（概念拓展）+ `demos/`

| 路徑 | 內容 |
|---|---|
| `docs/multi_function_interaction.md` | 把「組合」提為與八軸正交的維度；含「組合的軸推導規則」（已實作於 `lib/compose_meta.py`）、組合 vs 交互、blackboard 交互模型（已實作於 `lib/interact.py`）。 |
| `docs/llm_taming_framework.md` | 把整個 ai_core 重讀成「馴化 LLM 隨機性」的機器；五層框架（契約/確定化/驗證/聚合/編排）對應到已實作零件。 |
| `demos/reliable_code_qa.py` | **端到端 demo**：把馴化框架五層串成一個「可靠程式碼問答函式」，自我測試證明每層生效（retry/guard/memoize）。`python3 demos/reliable_code_qa.py`。 |
| `demos/call_chain_trace.py` | **端到端 demo**：跑 `sfc forge`、收集其 stderr 的 trace 事件、用 `trace.Collector` 重建調用樹（forge.serve → forge.call:*）。`python3 demos/call_chain_trace.py`。 |
| `demos/resumable_batch.py` | **端到端 demo**：批次處理器跑到一半「崩潰」，重跑時靠 `recovery`+`state_dirs` 從斷點接續、不重算已完成項。驗證兩個複合規範參考實作真能扛中斷。`python3 demos/resumable_batch.py`。 |

> `router.py` / `sfc.py`（forge）的 dispatch 現在都是 trace-aware：forge 在每次 call 開 span、
> router 用 `trace.child_env()` 把 trace id 傳給子 process。即 lib/trace 已實際接進工具，
> 不只是獨立 library。

---

## 怎麼跑

```bash
cd try_implement

# 兩套煙霧測試（合計 140 斷言）
python3 smoke_test.py        # 工具：indexer/router/switch/sfc/hub/entry_manager（72）
python3 lib_smoke_test.py    # lib：…/compose/interact/compose_meta（68）

# --- 各工具單獨玩 ---

# Indexer：掃 funcs/ 產出索引
python3 tools/indexer.py --dir funcs --format md
python3 tools/indexer.py --dir tools --format json     # 也能索引工具自己

# Router：查表後 dispatch
echo "hello" | python3 tools/router.py --routes routes.json upper
python3 tools/router.py --routes routes.json --list

# Switch：依 --lang 條件分支
echo "int main(){}" | python3 tools/switch.py --config switch.json --lang c
echo "print(1)"     | python3 tools/switch.py --config switch.json --lang python
python3 tools/switch.py --config switch.json --lang rust --explain   # 只看決策

# SFC（git-style subcommand）
python3 tools/sfc.py list
echo "hello there" | python3 tools/sfc.py shout         # python in-process
echo "a b c d"     | python3 tools/sfc.py wc_words      # shell subprocess
python3 tools/sfc.py shout --metadata                   # subcommand-scoped metadata
python3 tools/sfc.py --metadata                         # SFC 自身 metadata

# SFC intake（Layer 1a）：把新函式收進 store
python3 tools/sfc.py intake --name rev --kind python --body "return stdin.strip()[::-1]"

# SFC forge（Layer 2/3）：persistent server，NDJSON 行協議（從 stdin 餵 request）
printf '%s\n%s\n' '{"cmd":"list"}' '{"call":"shout","stdin":"hi"}' '{"cmd":"shutdown"}' \
  | python3 tools/sfc.py forge

# SFC Layer 3 動態管理：執行期 add / remove / persist 回 store
printf '%s\n%s\n%s\n' \
  '{"cmd":"add","defn":{"name":"rev","kind":"python","body":"return stdin.strip()[::-1]"}}' \
  '{"call":"rev","stdin":"abc"}' \
  '{"cmd":"persist"}' '{"cmd":"shutdown"}' \
  | python3 tools/sfc.py forge

# Hub：把函式生態轉成給 LLM 的 skill 清單，可設 budget 收斂
python3 tools/hub.py --scan funcs
python3 tools/hub.py --scan funcs --budget 60        # 過小預算 → 自動收斂並標註省略
python3 tools/hub.py --scan funcs --format json

# LLM Entry Manager：singleton 資源，consume rate 守門（NDJSON server）
printf '%s\n%s\n%s\n' \
  '{"cmd":"complete","prompt":"hello world"}' \
  '{"cmd":"usage"}' \
  '{"cmd":"shutdown"}' \
  | python3 tools/llm_entry_manager.py --limit-token 50

# chain：宣告式管線（組合維度的 CLI）
echo hi | python3 tools/chain.py --spec chain_demo.json   # upper→reverse → IH
python3 tools/chain.py --spec chain_demo.json --derive    # 從各 stage --metadata 推導複合 metadata
```

`forge --metadata` 現在會回 `persistent`、頂層 `sfc --metadata` 回 `one_shot`
（同一執行檔不同 lifecycle，Gap B 的修法效果）。

每個工具都實作 `--metadata`（跨元件契約）：

```bash
python3 tools/indexer.py --metadata   # {"lifecycle": "one_shot", "state": "stateless"}
python3 tools/router.py  --metadata
python3 tools/switch.py  --metadata
python3 tools/sfc.py     --metadata
```

---

## 「待設計」項目上做的決策（附理由）

### 1. Layer 0 設定檔格式（thinking_sfc.md 標為待設計）

**決策**：兩個 JSON 檔。

```
store/functions.json   ← object，key=函式名，value=函式定義
store/index.json       ← {"index": {"<name>": "<store 內 key>"}}
```

函式定義欄位：`name` / `kind`（`python`｜`shell`）/ `body` / `description` / `metadata`（沿用 ai_core 軸）。

**理由**：
- 用 **object（而非 array）**：以 name 為 key 本身就是 O(1) 查找。
- 仍保留**獨立的 `index.json`**：thinking_sfc.md 明確要求 Layer 0 有 index，且
  thinking_routing.md「Indexer 升級版」預告 index 未來會擴充 tags / summary / category。
  故 index.json 作為「可被獨立擴充的查找層」存在；spike 階段它先是恆等映射
  （`name → name`），但結構上預留升級空間，functions.json 只存定義本體。
- 全 JSON、純標準庫可解析，符合 `data_format.md §3`「JSON 為通用格式」。

### 2. tiny function 的呼叫介面（thinking_sfc.md 待設計）

**決策**：兩種 kind 的 body 約定統一為 `fn(stdin: str, args: dict) -> str`。
- `kind="python"`：body 是函式體原始碼，`compile`+`exec` 到**受限 namespace**（只放少量
  builtins）後**真正 in-process** 執行（符合 thinking_sfc.md「Python 真正 in-process」）。
- `kind="shell"`：body 是 shell 指令，SFC 內部開 `bash -c` subprocess，stdin 餵進、stdout 收回
  （符合 thinking_sfc.md「shell pipe 由 SFC 管理 subprocess」）。
- 剩餘 CLI flag 由 `_rest_to_dict()` 依 `cli_spec.md §2.0`（Lisp keyword pair → dict）轉成 `args`。

**理由**：單一固定簽名讓 dispatcher 不必為每個函式客製，最 KISS。受限 namespace 是
spike 等級的薄防護（非沙箱），明示「tiny function 不該亂搞」。

### 3. Switch 的條件表達方式（thinking_routing.md 待設計）

**決策**：純資料的**規則表（rule list）**，每條規則做「key 的值 == 常數」字串相等比較，
命中即路由。switch 變數的值來源支援 `arg`（取自 CLI flag）與 `ext`（取自輸入檔副檔名）。

```json
{"switch": {"on": "lang", "source": "arg",
  "rules": [{"equals": "c", "target": {...}}, {"equals": "python", "target": {...}}],
  "default": {...}}}
```

**理由**：純資料、無 DSL、無 `eval`、不造規則引擎（不重造輪子）。LLM 容易生成、人易讀。
範圍/正則等複雜條件留待正式規範，spike 不過度工程化。

### 4. forge server 的對外介面（thinking_sfc.md / thinking_pending.md §3 待設計）

**決策**：**stdin/stdout 的 NDJSON 行協議**（每行一個 JSON request/response）。
- request：`{"call":"<name>","stdin":"...","args":{...}}`；或管理指令 `{"cmd":"list"}` / `{"cmd":"shutdown"}`
- response：`{"ok":true,"stdout":"..."}` 或 `{"ok":false,"error":"..."}`

**理由**：最 KISS——不需 socket bind、不需 http.server、不需 port 管理，純 `sys.stdin`/`sys.stdout`。
保留升級到 HTTP 的空間。**注意**：`thinking_pending.md §3` 指出「stdin/stdout JSON-RPC 選項
需重新評估」，故此選擇標為 spike 暫定，回報給使用者定奪。

---

## 哪些是 stub / 未做

- ~~**SFC Layer 3（完整管理 API）**~~：✅ 已做。forge NDJSON 支援 `list` / `add` / `remove` /
  `persist`（動態增刪 + 寫回 Layer 0 store）。`sfc admin` 改為指路牌，指向 forge 的 API。
- **SFC Layer 4（資源 / 錯誤處理）**：✅ 部分做了——shell-kind 的 `--call-timeout`（超時回
  `timeout` 錯誤）+ 標準錯誤封套 `{"ok":false,"error":{"type","message","function"}}`
  （type ∈ bad_json/bad_request/unknown_function/compile_error/runtime_error/timeout，
  讓 caller 能依型別決定是否重試）。**仍未做**：python-kind 的資源上限（缺口 E：in-process
  無乾淨隔離邊界，stdlib 做不到）、retry 策略。
- **Indexer 升級版**（AI 加 tags / summary / category）：未做（需 LLM，超出本 spike）。
- **Router 升級版**（安全憑證 / 資源管理）：未做。
- **Hub**：原本 spike 刻意不做（定義未定）；後續使用者授權後**做了最小自定義版**
  （`tools/hub.py`：scan → skill 清單 + budget 收斂）。完整定義仍待規範定奪。
- **Router 對 store 片段的執行**：router 只支援 `type=exec`（單檔程式路徑）。SFC store 內的
  腳本片段由 `sfc.py` 自己執行（Layer 1b/2）。兩者職責分離——這是刻意的設計選擇，非缺漏。

---

## 過程中發現的設計缺口 / 與既有規範衝突（最重要，供細調規範）

> **✅ 已扶正進 `_core.py`（2026-05-26）**：放寬版攔截 + subcommand-scoped metadata（採「宣告／
> 攔截拆分」模型）已納入真 `src/ai_core/_core.py` 與 `lib_spec.md`，`meta_core.py` 原型已刪、
> `sfc.py` 改接真 library。`sfc <fn> --metadata`、`sfc forge --metadata` 都正常運作。下方為原始
> 缺口描述，留作脈絡。

### A. `register()` 的 `--metadata` 攔截策略與 git-style subcommand CLI 不相容【阻塞級】

`ai_core._core._intercept()` 的規則是：`--metadata` **必須是唯一引數**（`sys.argv[1:] == ["--metadata"]`），
否則報錯 exit 1。

但 thinking_sfc.md 要求 SFC 支援 **`sfc <funcname> --metadata`**（subcommand-scoped metadata，
見 thinking_sfc.md §4.0 / Layer 4 CLI 範例）。此時 `--metadata` 不是唯一引數，
若在 import 時無條件呼叫 `register()`，會在進到 `main()` 前就被攔截並 exit 1。

**spike 折衷**：`sfc.py` 只在 `sys.argv[1:] == ["--metadata"]` 時才呼叫 `register()`
（交給 library 輸出自身 metadata）；`sfc <funcname> --metadata` 由 SFC 自己處理。

**回報**：`register()` 的「`--metadata` 只能單獨使用」是針對**葉子工具**設計的，
但對**有 subcommand 樹的 dispatcher**（SFC、未來的 hub）不適用。建議規範補上
「subcommand-scoped metadata」的標準處理方式——例如 library 提供
`register_subcommand(name, **kwargs)`，或攔截邏輯放寬為「`--metadata` 出現在最後且前面只有
subcommand 路徑」。目前每個 dispatcher 都得自己繞過 library，違背「library 統一處理 metadata」的初衷。

> **✅ 已扶正進 `_core.py`（2026-05-26）**：`ai_core.register_subcommand("forge", lifecycle="persistent")`
> 讓 forge 子命令宣告與頂層不同的 lifecycle。`sfc forge --metadata` 回 `persistent`、
> `sfc --metadata` 回 `one_shot`。下方為原始缺口描述。

### B. 單一程式有多種 lifecycle 時，metadata 是單值，難以表達

`sfc.py` 預設用法是 **one_shot dispatch**（`sfc shout`），但 `sfc forge` 子命令是
**persistent server**。`register()` 只能宣告**一個** `lifecycle`。

spike 讓 `sfc --metadata` 報 `one_shot`（反映預設用法），把 forge 的 persistent 性質留給
「forge 子命令自己的 metadata」——但目前 forge 子命令還沒有獨立的 `--metadata` 出口
（會落到 argparse，不是 ai_core）。

**回報**：規範需決定「一個執行檔含多種 lifecycle 子命令」時 metadata 怎麼表達。可能方向：
(1) 頂層 metadata 只描述 dispatcher 本身，各 subcommand 各有 scoped metadata；
(2) 把 forge 拆成獨立執行檔。這牽涉 §2 lifecycle 軸與 subcommand 的關係，需規範定奪。

> **🔬 已被 hub 具體放大**：`tools/hub.py` 想產 skill 清單卻沒有用途欄位可用，只能用
> `_synthesize_summary()` 從軸值硬湊出「一次性、無副作用」這種粗略描述（見 `hub --scan funcs`
> 的實際輸出）。這把缺口暴露得很具體：**沒有語意描述軸，skill 清單對 LLM 幾乎沒用。**

### C. metadata 缺「函式介面 / 參數」描述欄位

八份軸（lib_spec.md）描述的是 lifecycle / state / interruptible / resources / guarantee 等
**執行特性**，但**沒有描述「這個函式做什麼、吃什麼參數、回傳什麼」**的欄位
（`entries` 只描述 I/O 通道的方向 / mode / type，不描述語意參數）。

Indexer 想產出「給 LLM 看的工具清單」（thinking_routing.md「概念上類似 LLM 的 skill 清單」），
但目前 metadata 給不出 `description` / `parameters` / `returns`——LLM 看了索引也不知道工具
**用途**。SFC 的 store 我自行加了 `description` 欄位補這個洞，但那不在 ai_core 軸規範內。

**回報**：依任務指示「不擅自擴充軸層」，此處僅記錄觀察：若 Indexer 升級版要做
tags / summary / category，且要讓 LLM caller 理解工具用途，**規範可能需要一個描述語意用途的軸
**（或明確定義由 Indexer 升級版用 AI 補，而非由工具自報）。這會直接影響 thinking_routing.md
「Indexer 升級版」與 hub「skill 清單」的可行性。

### D. router / switch 的 `resolve_command` 邏輯重複

`router.py`、`switch.py`、`chain.py` 各有一份幾乎相同的 `resolve_command()`/`_resolve()`
（把 `{path, type}` 轉成 argv，依副檔名選 interpreter）——**現在是三份了**。spike 為了
「各工具獨立可執行、不引入共用模組相依」刻意各寫一份；三處重複讓這個訊號更明確。

**回報**：若正式化，這是 thinking.md 提到的「重複實作 → 抽共用模組」訊號。但抽共用模組
會讓每個工具不再是單檔自足——與「shell 為一等公民、單檔程式」的取向有張力。規範需在
「DRY」與「單檔自足」間取捨。

### E. tiny function 的 in-process 執行沒有真正的資源 / 安全隔離

`kind="python"` 用 `exec` 到受限 namespace，但這只是薄防護，不是沙箱（仍可透過各種手段逃逸）。
Layer 4 的「資源管理」若要對 in-process 的 python tiny function 設記憶體 / 時間上限，
標準庫做不到乾淨的隔離（沒有 subprocess 邊界）。

**回報**：Layer 2「Python 真正 in-process」與 Layer 4「資源 / 錯誤處理」在實作上有張力——
in-process 換來速度，卻失去 subprocess 的天然隔離邊界。規範需明確 Layer 4 的資源限制
對 in-process 函式的適用範圍（可能只能對 shell-kind 生效，或 python-kind 需退回 subprocess）。

### F. `register()` 在 module 頂層呼叫，使工具無法被當 library import（新發現）

> **✅ 已根治（2026-05-26）**：拆分模型讓 `register*` 系列變成純宣告、零副作用（不讀 argv、不
> 攔截、不 exit），且去掉「只能 register 一次」的全域旗標——import 即安全。`lib_spec.md` 另補
> 「register 應在 `__main__`/`main()` 呼叫」的慣例。下方為原始缺口描述，留作脈絡。

寫 `hub.py` 時要重用 `indexer.py` 的 `build_index()`，但 `indexer.py` 原本在 module 頂層
呼叫 `ai_core.register(...)`——一 `import indexer` 就會：(1) 跑 `_intercept()` 讀 `sys.argv`、
(2) 佔住「只能 register 一次」的全域旗標。於是第二個工具想 register 就會 `RuntimeError`。

**spike 解法**：把 `indexer.py` 的 `register()` 從頂層移進 `main()`（只在當作腳本跑時才註冊），
import 就無副作用了。`hub.py` 因此能安全重用。

**回報**：「在 import 時就 register + 可能 exit」是針對「工具只會被當腳本執行」的假設。
但 ai_core 鼓勵函式互相組合 / 重用，工具被當 library import 是常態。建議規範 / library
明確：register 的副作用（讀 argv、攔截、佔旗標）應延遲到「確定以腳本身分執行」時——
例如只在 `__main__` 才 register，或 library 提供 lazy 模式。這與 Gap A/B 同源（都是
register 的 import-time 副作用問題）。

---

## 概念拓展（回應「往多函數合作/交互、馴化 LLM 隨機性」的方向）

除了把既有概念寫成可跑的程式碼，這次也往**新概念**走了兩步，記在 `docs/`：

1. **組合維度**（`docs/multi_function_interaction.md` + `lib/compose.py`）：
   主張「函式怎麼一起動」是與八軸正交的維度。最有料的延伸是 **§3 軸推導規則**——
   `pipe` 的 guarantee = 各段最弱、state = 各段聯集…若成立，hub 能對「臨時組起來的
   複合函式」自動算 metadata。**建議列為複合規範家族的候選議題。**

2. **LLM 隨機性馴化框架**（`docs/llm_taming_framework.md`）：
   把整個 ai_core 重讀成「把唯一的非確定性函式（LLM）轉成可靠複合函式」的機器。
   五層（契約 / 確定化 / 驗證 / 聚合 / 編排）各自對應已實作零件（memoize / retry_until_valid
   / vote / best_of / guard / hub / route）。`lib_smoke_test.py` 已逐一驗證這些零件的行為。
   開放問題：是否新增 `nondeterministic: true` 軸（與 memoized 同樣「無既有軸值可隱含」的處境）。

兩份文件在「actor-critic 交互」處交會（LLM 當 validator/scorer → 需要 blackboard 交互模型）。
