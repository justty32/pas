# DECISIONS — 待你定奪的規範決策（try_implement 回饋彙整）

> 這頁把散在 README / docs / 各 lib 檔頭的「回饋規範」內容，收斂成一份**決策清單**。
> try_implement 的實驗都只是提案 / 原型；**真正的 `src/ai_core/_core.py` 與 `core_nature/`
> 一行都沒動**。下面每項都標明「現況 / 我的建議 / 你要決定什麼」，讓你回來能快速行動。
>
> 分四區：A 已原型待扶正 ／ B 開放方向題 ／ C 候選新軸 ／ D 我已自行拍板待你追認。

---

## ✅ 已收斂（2026-05-26）

這一輪把下列項目**扶正進真正的 `src/ai_core/_core.py` 與 `core_nature/` 規範**（不再只是 try_implement 原型）：

| 項目 | 決策 | 落地處 |
|---|---|---|
| **A1 + A2 + A3** | 採「**宣告／攔截拆分**」模型：`register` / `register_subcommand` / `register_subcommand_resolver` 純宣告、無副作用；`intercept(argv)` 顯式攔截（放寬版，支援 `<sub> --metadata` 與 `--store` 前綴）。一次解掉 A1（subcommand metadata）、A2（單檔多 lifecycle）、A3/F（import 副作用）。 | `src/ai_core/_core.py`、`core_nature/lib_spec.md`「register() 與 intercept()」節、`tests/test_core.py`（65 測試）。`meta_core.py` 原型已刪，sfc 改接真 library。 |
| **C：`nondeterministic` 軸** | **新增第九軸**。`true`＝未認證的隨機環節（開機期）；`{model, test_set, stability}`＝證書（成熟期，可稽核可撤照）。承載 `roadmap.md §3.4` 治理原則。 | `src/ai_core/_core.py`、`lib_spec.md §9`、`axis_spec.md §9`、`execution_forms.md §0` 表、`tests/test_core.py`。 |
| **C：`memoized`** | **不入軸**，維持純 runtime（`lib/memoize.py`）。理由：快取是呼叫方/library 的優化決策，且可由「`nondeterministic` 缺席 + `stateless`」隱含可快取性——不像 `nondeterministic` 那樣無既有軸值可隱含。 | `lib_spec.md`「未入軸的決策：memoized」節。 |

驗證：`smoke_test.py` 72 + `lib_smoke_test.py` 68 + `tests/test_core.py` 65 全綠，三個 demo 正常，各工具 `--metadata` / `<sub> --metadata` 行為端到端正確。

**仍待你定**：A4（組合軸推導）與 B 系列（B1 語意欄位 / B2 共用模組 / B3 沙箱）依 `roadmap.md §7`
**留給 v0 切片去逼出優先序**（見下方各條的「狀態」）；D 區（我自行拍板的 7 項）仍待你追認。

---

## A. 已做原型，待你決定是否扶正進規範

### A1. `--metadata` 攔截 vs subcommand CLI（原 Gap A，阻塞級）— ✅ 已扶正
- **現況**：真 `_core.py` 要求 `--metadata` 必須是唯一引數，與 `sfc <fn> --metadata` 不相容。
  已在 `tools/meta_core.py` 原型化「放寬攔截 + `register_subcommand` + resolver」，sfc 已改用，運作正常。
- **我的建議**：扶正。把 `register_subcommand(name, **meta)` + 放寬版攔截納入 `_core.py`。
- **✅ 決策（2026-05-26）**：採 meta_core 的拆分 API 形狀，扶正進 `_core.py` + `lib_spec.md`。
  `intercept()` 為放寬版（吃 `--store` 前綴、支援 `<sub> --metadata`）。`meta_core.py` 已刪。

### A2. 單一執行檔多種 lifecycle（原 Gap B）— ✅ 已扶正
- **現況**：`sfc` 是 one_shot dispatcher、`sfc forge` 是 persistent。已用 `register_subcommand("forge",
  lifecycle="persistent")` 表達；`sfc forge --metadata` 回 persistent、頂層回 one_shot。
- **我的建議**：採「頂層描述 dispatcher、各 subcommand 各有 scoped metadata」模型（隨 A1 一起）。
- **✅ 決策（2026-05-26）**：採 scoped-metadata 模型（隨 A1 一起扶正）。頂層描述 dispatcher
  預設、各 subcommand 各有 scoped metadata；不強制拆成不同執行檔。

### A3. `register()` 的 import-time 副作用（原 Gap F，新發現）— ✅ 已扶正
- **現況**：`register()` 放 module 頂層 → 一 import 就讀 argv / 攔截 / 佔旗標 → 工具無法被當
  library 重用（hub 想 import indexer 時撞到）。已把 indexer 的 register 移進 `main()` 修掉。
- **我的建議**：規範明訂「register 的副作用應延遲到確定以腳本身分執行」——只在 `__main__` 呼叫，
  或 library 提供 lazy 模式。與 A1/A2 同源（都是 register 的 import-time 行為）。
- **✅ 決策（2026-05-26）**：由拆分模型**根治**——`register*` 系列改為純宣告、零副作用，import 即安全；
  並去掉「只能 register 一次」的全域旗標（last-write-wins）。`lib_spec.md` 補「register 應在
  `__main__`/`main()` 呼叫」的慣例（解 module-global 單例的覆寫問題），但不再硬性 enforce。

### A4. 組合的軸推導規則（候選新概念）— ⏸ 暫緩至 v0
- **現況**：`lib/compose_meta.py` 原型化「從成員八軸推導複合函式 metadata」：guarantee 取最弱、
  state/state_dirs 取聯集、persistent 成員列 `requires_persistent`、fanout 寫衝突偵測；
  `mretry` 把「retry 要求被包函式 ≥ idempotent」做成執行期檢查。
- **我的建議**：列為複合規範家族議題。若成立，hub 能對臨時組起來的複合函式**自動算 metadata**。
- **你要決定**：(1) 要不要正式收？(2) 推導範圍——只 guarantee/state，還是含 interruptible 等全軸？
  (3) guarantee 強度序（none<idempotent<transactional）是否接受這個簡化？
- **⏸ 狀態（2026-05-26）**：依 `roadmap.md §7` **暫緩**——「優先序待 v0 驗證後再定」。等 v0 真的把
  資產組成調用鏈、需要複合 metadata 時，再決定推導範圍與是否正式收。原型續留 `lib/compose_meta.py`。

---

## B. 開放方向題（還沒有明確最佳解，需你定方向）

> **⏸ 本輪未動，留給 v0 切片逼出優先序**（`roadmap.md §7`）：B1（語意欄位）與 B3（沙箱）在
> roadmap §7 表中被列為「v0 一定會撞到」——生資產必撞 B1、跑碼驗證必撞 B3，到時它們從「憑空猜」
> 變「擋路、得解」。B2（共用模組）現況有可用暫定解（各工具單檔自足）。故本輪刻意不決，避免在
> 沒有目標壓力時憑空定標準（方法論翻轉，`roadmap.md §4`）。

### B1. metadata 缺語意用途欄位（原 Gap C）
- **現況**：八軸只描述執行特性，沒有「這函式做什麼/吃什麼參數」。`hub` 想產 LLM skill 清單，
  只能用 `_synthesize_summary()` 從軸值硬湊「一次性、無副作用」——對 LLM 幾乎沒用。
- **選項**：(a) 新增 `description`/`summary`/`parameters` 語意軸；(b) 明訂由 Indexer 升級版用 AI
  補摘要、工具自身不報；(c) 接受 skill 清單只能粗略。
- **你要決定**：走 a / b / c 哪條？（影響 thinking_routing「Indexer 升級版」與 hub 的可行性。）

### B2. 共用模組 vs 單檔自足（原 Gap D）
- **現況**：`resolve_command()`（path→argv）在 router / switch / chain **重複了三份**。
- **選項**：(a) 抽成 `lib/exec_target.py` 共用（DRY）；(b) 維持各工具單檔自足（shell 一等公民取向）。
- **你要決定**：DRY 還是單檔自足優先？（三份重複已是該抽的訊號，但抽了就破壞單檔可獨立執行。）

### B3. in-process 的資源隔離（原 Gap E）
- **現況**：python-kind tiny function 是真 in-process（`exec`），標準庫無法乾淨設記憶體/時間上限。
  Layer 4 的 `--call-timeout` 因此**只對 shell-kind 生效**。
- **選項**：(a) 資源上限只承諾 shell-kind；(b) python-kind 要限制時退回 subprocess（失去 in-process 速度）;
  (c) 引入非標準庫沙箱（違背 least dependency）。
- **你要決定**：Layer 2「真 in-process」與 Layer 4「資源上限」如何取捨？

---

## C. 候選新 metadata 軸 / 欄位（都牽動軸層，需審慎）

| 候選 | 來源 | 為何可能需要 | 決策 |
|---|---|---|---|
| `nondeterministic` | docs/llm_taming_framework | 標記「這函式是隨機的」是整套馴化框架的**觸發根**；八軸無此概念 | **✅ 扶正（2026-05-26）為第九軸**。`true`＝未認證 / `{model,test_set,stability}`＝證書。落地：`lib_spec.md §9`、`axis_spec.md §9`、`_core.py`。 |
| `memoized: {version, ttl}` | session_resume 決策3 / lib/memoize | memoized 沒有既有軸值可隱含（不像中斷恢復有 interruptible/guarantee）→ 可能**真的需要**新欄位 | **✅ 決策（2026-05-26）：不入軸、純 runtime**。修正先前判斷——可由「`nondeterministic` 缺席 + `stateless`」隱含可快取性，故毋須新欄位。記於 `lib_spec.md`「未入軸的決策」。 |
| lifecycle 變體「依賴外部 server」 | compose_meta requires_persistent | 含 persistent 成員的複合函式，其呼叫本身 one_shot 但需 server 在線；八軸無此值 | ⏸ 暫緩（隨 A4 組合維度一起待 v0）。 |
| 交互終止條件 | docs/multi_function_interaction §5 | 多函數交互需要標準化的終止語意（否則無限互踢） | ⏸ 暫緩（暫由 `lib/interact.py` 的 `max_rounds` runtime 承擔）。 |

> **回顧本輪的核心抉擇**：`nondeterministic` 與 `memoized` 表面同處「**沒有既有軸值可隱含觸發**」，
> 但仔細看其實不同——`nondeterministic`（隨機性）真的無從推斷，故**成軸**；`memoized`（可不可快取）
> 反而可由「`nondeterministic` 缺席 + `stateless`」隱含，故與「中斷恢復慣例」同理**不加欄位**。
> 這正是「能由既有軸推斷的就不膨脹軸層」原則的一次具體裁決。

---

## D. 我外出期間自行拍板的決策（請追認或推翻）

你授權我自行決定，以下是我替你拍的板，理由都寫在對應檔案檔頭：

| 決策 | 我選了什麼 | 檔案 |
|---|---|---|
| 記憶化 cache key 組成 | sha256(version + stdin + args + 檔 digest)，由呼叫方明確指定哪些參與 | `lib/memoize.py` |
| 記憶化失效策略 | 預設靠 `.cache` 可隨時刪（無 TTL）；version / ttl 為 opt-in | `lib/memoize.py` |
| Hub 的定義 | Hub = 把函式生態轉成「給 LLM 的 skill 清單」的透鏡 + context budget 收斂 | `tools/hub.py` |
| forge 對外介面 | stdin/stdout NDJSON 行協議（標為暫定，thinking_pending §3 說要重評） | `tools/sfc.py` |
| Switch 條件表達 | 純資料規則表（equals），值來源 arg/ext，無 DSL/eval | `tools/switch.py` |
| Layer 4 錯誤封套 | `{"ok":false,"error":{"type","message","function"}}`，type 分流可重試性 | `tools/sfc.py` |
| 交互安全閥 | `max_rounds` 強制必有，防 actor↔critic 無限互踢 | `lib/interact.py` |

---

## 建議的處理順序（進度）

1. ~~**A1+A2+A3**（register 的三個 import-time 問題）一起處理——同源，且 A1 是阻塞級。~~ ✅ 完成（2026-05-26）
2. ~~**C 的 `memoized` / `nondeterministic`**~~ ✅ 完成（2026-05-26）：nondeterministic 成軸、memoized 純 runtime。
3. **A4 組合軸推導**——⏸ 暫緩至 v0（roadmap §7：優先序待 v0 驗證後再定）。
4. **B 系列**（方向題）——⏸ 留給 v0 逼出（B1/B3 v0 必撞、B2 有暫定解）。
5. **D 區 7 項**——仍待你追認（都是 try_implement 原型的低風險拍板，未阻塞）。

> 下一步建議：規範地基（A/C 該收的已收）已穩，可轉向 `roadmap.md §6` 的 **v0 垂直切片**——
> 由真實目標去逼出 B1/B3/A4 的優先序，而非繼續在抽象層定標準。
