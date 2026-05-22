# composite_spec.md

`lib_spec.md` 定義各軸的原子性 metadata fields——每個軸描述程式的一個獨立特性。本檔定義**複合式規範（composite conventions）**：橫跨多軸的標準模式，library 為這些模式提供一體化的配套設施。

複合式規範不新增孤立的概念，而是說明「哪些軸的特定組合，在實作層面形成一個具名慣例」，以及這個慣例帶來的附加 metadata fields 與 library 工具。

---

## 複合規範列表

| 慣例 | 觸發條件 | 涵蓋軸 |
|---|---|---|
| 標準狀態目錄慣例 | `state: "stateful_external"` + terminal 環境 | §1、§3、§5、§6 |

---

## 標準狀態目錄慣例（Standard State Directory Convention）

### 概述

當程式宣告 `state: "stateful_external"` 且在 terminal 環境下執行時，其外部狀態的存放位置需要一個標準約定。此慣例規定了程式在**工作目錄**下存取狀態的標準路徑結構，讓 hub、呼叫方與 library 能夠預期程式的副作用範圍。

### 目錄結構

```
.config/<program_name>/     ← 或 .config/<program_name>.json
.cache/<program_name>/      ← 或 .cache/<program_name>.json
.state/<program_name>/      ← 或 .state/<program_name>.json
.data/<program_name>/       ← 或 .data/<program_name>.json
```

`<program_name>` 為程式的識別名稱（通常與執行檔名相同）。

### 四個目錄的語意

| 目錄 | 語意 | 可否刪除 |
|---|---|---|
| `.config` | 程式本身不會修改的設定，由人類或外部工具寫入 | 視情況（刪除後程式使用預設值） |
| `.cache` | 可在程式執行時間之外被任意刪除，程式不依賴其存在 | 可隨時刪除 |
| `.state` | 程式目前所在的 stage——執行進程、跨輪次的階段位置 | 刪除後程式遺忘進度，可重置 |
| `.data` | 程式累積建造出來的成果性資料；重要，不可隨意刪除 | 不可隨意刪除，需備份 |

`.state` 與 `.data` 的分野：清掉 `.state` 只是讓程式遺忘做到哪（可重置）；清掉 `.data` 是真的失去成果（需備份）。

### 檔案格式規則

- 每個位置可以是**資料夾**或**單檔**
- **單檔**（如 `.config/<name>.json`）：必須是 `.json`，且內容為 JSON 物件
- **資料夾內的子檔**（如 `.config/<name>/settings.yaml`）：格式無限制
- 不強制四個目錄都存在，按語意選用即可

---

### 跨軸涵蓋

此慣例同時涉及四個軸，各自職責如下：

**§1 I/O 出入口**

這些目錄是程式的 file I/O 通道——`.config` 是穩定的輸入來源，`.data` 是輸出成果，`.state`/`.cache` 是讀寫兩用的中繼存取點。它們都屬於 §1 的 file I/O 類型，`channel_constraint` 應視為 `"stable"`（file 通道屬穩定通道）。

若程式需要在 `entries` 中暴露這些通道給 hub 感知（例如呼叫方需要知道 config 路徑或 data 輸出位置），應以自訂 entry 名稱 + `channel_constraint: "stable"` + `terminal_binding` 描述。若呼叫方不需要感知具體路徑，則無需在 `entries` 中宣告。

**§3 跨呼叫狀態**

此慣例是 `state: "stateful_external"` 在 terminal 環境下的標準實作形式。程式宣告此 field 且遵守此慣例，呼叫方即可預期狀態的存放位置，而不必額外文件說明。

**§5 可中斷性**

中斷對各目錄的影響取決於該目錄的角色：

| 目錄 | 中斷風險 |
|---|---|
| `.config` | 程式只讀，中斷不影響 |
| `.cache` | 可隨時重建，中斷通常無損 |
| `.state` | 中斷若在寫入途中，可能記錄到半完成的進度；安全性取決於寫入策略 |
| `.data` | 中斷可能導致成果資料不完整，損毀風險最高 |

程式應根據其對 `.state`/`.data` 的寫入方式，宣告對應的 `interruptible` 值（如 `"unsafe"`、`"resettable"`、`"rollback"`）。

**§6 執行保證**

程式對 `.state`/`.data` 的操作是否具備冪等性或事務性，由 `guarantee` 宣告。此慣例不強制特定保證等級，但建議明確宣告，讓 hub 知道重試是否安全。

---

### 附加 metadata field：`state_dirs`

當程式遵守此慣例時，可透過 `state_dirs` 宣告實際使用的目錄子集：

| key | 型別 | 說明 |
|---|---|---|
| `state_dirs` | array of string | 實際使用的目錄列表；允許值為 `"config"`、`"cache"`、`"state"`、`"data"` 的子集 |

**預設值**：若 `state_dirs` 缺席，hub 無法推斷實際使用哪些目錄，但 `state: "stateful_external"` 仍足以通知呼叫方副作用的存在。

`state_dirs` 是資訊性宣告，目的是讓 hub 了解副作用的範圍，而非強制合約。

```python
ai_core.register(
    state="stateful_external",
    state_dirs=["state", "data"],
)
```

```json
{"state": "stateful_external", "state_dirs": ["state", "data"]}
```

---

### 多實例並發

本慣例**核心規範不處理多實例並發**。

若程式預期多個實例以相同 `<program_name>` 並發執行，寫入 `.state/<program_name>` 時建議標註自身 PID（如 `.state/<program_name>/<pid>.json`）；讀寫鎖依賴 OS。具體標註格式與看見他人標註時的行為，由程式撰寫者自行決定，本規範不規定。

若 `<program_name>` 本身含 PID 或 UUID（如 `task_worker_1234`），則資料夾天然隔離，無競爭問題。

---

### 完整 metadata 範例

一個「有狀態的資料處理腳本」，遵守標準目錄慣例：

```python
ai_core.register(
    lifecycle="one_shot",
    state="stateful_external",
    state_dirs=["state", "data"],
    interruptible="unsafe",
    guarantee="idempotent",
)
```

`--metadata` 輸出：

```json
{
  "lifecycle": "one_shot",
  "state": "stateful_external",
  "state_dirs": ["state", "data"],
  "interruptible": "unsafe",
  "guarantee": "idempotent"
}
```

語意解讀：

| field | 語意 |
|---|---|
| `lifecycle: "one_shot"` | 執行完結束 |
| `state: "stateful_external"` | 會讀寫外部目錄 |
| `state_dirs: ["state", "data"]` | 具體使用 `.state/<name>/` 和 `.data/<name>/` |
| `interruptible: "unsafe"` | 被中斷可能使這兩個目錄進入不一致狀態 |
| `guarantee: "idempotent"` | 但若讓它完整執行，重跑不會累積副作用（已寫入的不會重複寫入） |
