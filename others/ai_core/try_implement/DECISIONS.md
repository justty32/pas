# DECISIONS — 待你定奪的規範決策（try_implement 回饋彙整）

> 這頁把散在 README / docs / 各 lib 檔頭的「回饋規範」內容，收斂成一份**決策清單**。
> try_implement 的實驗都只是提案 / 原型；**真正的 `src/ai_core/_core.py` 與 `core_nature/`
> 一行都沒動**。下面每項都標明「現況 / 我的建議 / 你要決定什麼」，讓你回來能快速行動。
>
> 分四區：A 已原型待扶正 ／ B 開放方向題 ／ C 候選新軸 ／ D 我已自行拍板待你追認。

---

## A. 已做原型，待你決定是否扶正進規範

### A1. `--metadata` 攔截 vs subcommand CLI（原 Gap A，阻塞級）
- **現況**：真 `_core.py` 要求 `--metadata` 必須是唯一引數，與 `sfc <fn> --metadata` 不相容。
  已在 `tools/meta_core.py` 原型化「放寬攔截 + `register_subcommand` + resolver」，sfc 已改用，運作正常。
- **我的建議**：扶正。把 `register_subcommand(name, **meta)` + 放寬版攔截納入 `_core.py`。
- **你要決定**：採 meta_core 的 API 形狀？還是只放寬攔截條件（不加 register_subcommand）？

### A2. 單一執行檔多種 lifecycle（原 Gap B）
- **現況**：`sfc` 是 one_shot dispatcher、`sfc forge` 是 persistent。已用 `register_subcommand("forge",
  lifecycle="persistent")` 表達；`sfc forge --metadata` 回 persistent、頂層回 one_shot。
- **我的建議**：採「頂層描述 dispatcher、各 subcommand 各有 scoped metadata」模型（隨 A1 一起）。
- **你要決定**：接受 scoped-metadata 模型？還是規定「不同 lifecycle 必須拆成不同執行檔」？

### A3. `register()` 的 import-time 副作用（原 Gap F，新發現）
- **現況**：`register()` 放 module 頂層 → 一 import 就讀 argv / 攔截 / 佔旗標 → 工具無法被當
  library 重用（hub 想 import indexer 時撞到）。已把 indexer 的 register 移進 `main()` 修掉。
- **我的建議**：規範明訂「register 的副作用應延遲到確定以腳本身分執行」——只在 `__main__` 呼叫，
  或 library 提供 lazy 模式。與 A1/A2 同源（都是 register 的 import-time 行為）。
- **你要決定**：是否把「register 僅在 `__main__`」寫成慣例 / 由 library 強制？

### A4. 組合的軸推導規則（候選新概念）
- **現況**：`lib/compose_meta.py` 原型化「從成員八軸推導複合函式 metadata」：guarantee 取最弱、
  state/state_dirs 取聯集、persistent 成員列 `requires_persistent`、fanout 寫衝突偵測；
  `mretry` 把「retry 要求被包函式 ≥ idempotent」做成執行期檢查。
- **我的建議**：列為複合規範家族議題。若成立，hub 能對臨時組起來的複合函式**自動算 metadata**。
- **你要決定**：(1) 要不要正式收？(2) 推導範圍——只 guarantee/state，還是含 interruptible 等全軸？
  (3) guarantee 強度序（none<idempotent<transactional）是否接受這個簡化？

---

## B. 開放方向題（還沒有明確最佳解，需你定方向）

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

| 候選 | 來源 | 為何可能需要 | 你要決定 |
|---|---|---|---|
| `nondeterministic: true` | docs/llm_taming_framework | 標記「這函式是隨機的」是整套馴化框架的**觸發根**；八軸無此概念 | 加嗎？這是 LLM 馴化慣例的入口 |
| `memoized: {version, ttl}` | session_resume 決策3 / lib/memoize | memoized 沒有既有軸值可隱含（不像中斷恢復有 interruptible/guarantee）→ 可能**真的需要**新欄位 | 加欄位，還是接受 memoized 純屬 runtime、不入 metadata？ |
| lifecycle 變體「依賴外部 server」 | compose_meta requires_persistent | 含 persistent 成員的複合函式，其呼叫本身 one_shot 但需 server 在線；八軸無此值 | 加這個 lifecycle 值/欄位嗎？ |
| 交互終止條件 | docs/multi_function_interaction §5 | 多函數交互需要標準化的終止語意（否則無限互踢） | 要不要像 interruptible 那樣標準化成一個概念？ |

> 共同模式：`nondeterministic` 與 `memoized` 都處於「**沒有既有軸值可隱含觸發**」的處境——
> 這與「中斷恢復慣例」當初選擇「不加欄位」的根本不同。是否新增欄位，是這兩條的核心抉擇。

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

## 建議的處理順序（若你問我先動哪個）

1. **A1+A2+A3**（register 的三個 import-time 問題）一起處理——同源，且 A1 是阻塞級。
2. **C 的 `memoized` / `nondeterministic`**——直接卡住你正在寫的複合規範家族下一條。
3. **A4 組合軸推導**——決定組合維度要不要進規範。
4. B 系列（方向題）可以最後，因為現況都有可用的暫定解。
