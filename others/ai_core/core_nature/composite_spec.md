# composite_spec.md

`lib_spec.md` 定義各軸的原子性 metadata fields——每個軸描述程式的一個獨立特性。本檔定義**複合式規範（composite conventions）**：橫跨多軸的標準模式，library 為這些模式提供一體化的配套設施。

複合式規範不新增孤立的概念，而是說明「哪些軸的特定組合，在實作層面形成一個具名慣例」，以及這個慣例帶來的附加 metadata fields 與 library 工具。

---

## 複合規範列表

| 慣例 | 觸發條件 | 涵蓋軸 |
|---|---|---|
| 標準狀態目錄慣例 | `state: "stateful_external"` + terminal 環境 | §1、§3、§5、§6 |
| 中斷恢復慣例 | `state: "stateful_external"` + (`interruptible ∈ {resumable, rollback, resettable}` 或 `guarantee: "transactional"`) + terminal | §3、§5、§6 |

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

---

## 中斷恢復慣例（Interruption Recovery Convention）

### 概述

當程式宣告自己在中斷後具備某種恢復能力——§5 `interruptible` 的 `resumable` / `rollback` / `resettable`，或 §6 `guarantee: "transactional"`——這些能力的底層實作機制是同一個：**在 `.state` 留下一份恢復記錄，下一次啟動時偵測該記錄並據以恢復**。

本慣例直接建立在標準狀態目錄慣例之上。上層慣例已定義 `.state` 為「程式目前所在的 stage」；本慣例進一步規定該 stage 內部要存放什麼、新一輪執行如何讀取它、以及據此如何恢復。恢復能力由 §5 / §6 既有欄位宣告，落地形式由本慣例的 on-disk 約定承擔——本慣例不新增 metadata 欄位（見下文）。

### 觸發條件

`state: "stateful_external"` + terminal 環境 + 下列任一：

- `interruptible ∈ {"resumable", "rollback", "resettable"}`
- `guarantee: "transactional"`

### 目錄結構

```
.state/<program_name>/recovery.json    ← 恢復記錄 manifest（標準最小欄位）
.state/<program_name>/recovery/         ← opaque payload（進度資料 / journal，程式自訂，選填）
```

`recovery.json` 是程式間的真正合約；`recovery/` 子目錄存放恢復所需的實際資料，格式由程式自訂。

### 恢復模式

把分散在 §5 / §6 的軸值，統一為「對半完成進度的三種處置」：

| 模式 | 來源軸值 | 偵測到未完成記錄時的行為 | 還原目標 |
|---|---|---|---|
| `resume` | §5 `resumable` | 從斷點接續執行 | 不還原，往前推進 |
| `rollback` | §5 `rollback`、§6 `transactional` | 撤銷所有未提交修改 | 完整還原至呼叫前的原始狀態 |
| `reset` | §5 `resettable` | 重置到某個安全點 | 安全狀態（不保證回到原始） |

> `transactional` 在單次執行內部保證 all-or-nothing；當執行被外部強制終止（kill）繞過保證機制時，下一輪啟動透過 `rollback` 模式補救未提交的殘局。這把 §5 的 `rollback` 與 §6 的 `transactional` 在實作層接了起來——前者描述「中斷後能回滾」的能力，後者描述「執行具事務性」的承諾，兩者共用同一份 journal。

### `recovery.json` 最小欄位

| 欄位 | 型別 | 說明 |
|---|---|---|
| `status` | string | `"in_progress"`（執行中／被中斷）｜ `"done"`（正常完成）|
| `mode` | string | `"resume"` ｜ `"rollback"` ｜ `"reset"`；此程式採用的恢復策略 |
| `ts` | string | 上次寫入此記錄的時間戳 |
| `payload` | string（選填）| 指向 `recovery/` 內進度／journal 檔的相對路徑 |

`status` 與 `mode` 為必填；其餘欄位與 `recovery/` 內 payload 的格式由程式自由擴充。

### 啟動恢復流程（標準演算法）

偵測為 **auto**——程式啟動時自動讀取恢復記錄，呼叫方無需傳入任何 flag。

1. 啟動，讀取 `.state/<program_name>/recovery.json`
2. 記錄不存在，或 `status == "done"` → 視為乾淨開始，正常執行
3. `status == "in_progress"` → 依 `mode`：
   - `resume`：載入 `payload`，從斷點接續
   - `rollback`：依 `payload` 撤銷未提交修改，還原後再正常執行（或退出交由呼叫方重試）
   - `reset`：清除／重置到安全點，再正常執行
4. 開始實際工作前，將 `status` 設為 `"in_progress"`；正常完成後設為 `"done"`（或刪除記錄）

是否額外提供 `--fresh` / `--resume` 之類的覆寫 flag，由程式自行決定，不在本慣例的強制範圍。

### 為何不新增 metadata 欄位

恢復能力已由 §5 `interruptible` 與 §6 `guarantee` 宣告，這正是 hub 排程時真正需要知道的（能否安全重試、能否中斷）。恢復記錄的內部細節屬 runtime 行為，hub 既不需要、也讀不到（要讀得啟動程式）。因此本慣例**不新增頂層 metadata 欄位**——觸發由 `interruptible` / `guarantee` + `state_dirs` 含 `"state"` 隱含，真正的程式間合約是 on-disk 的 `recovery.json`。新增 recovery 欄位只會與 §5 / §6 重疊，違反軸的正交性。

### 跨軸涵蓋

| 軸 | 職責 |
|---|---|
| §3 跨呼叫狀態 | `recovery.json` 與 payload 都是 `.state` 下的外部狀態；`state_dirs` 應包含 `"state"` |
| §5 可中斷性 | `interruptible` 宣告「中斷後能恢復」的能力；本慣例規定「怎麼恢復、記錄在哪」 |
| §6 執行保證 | `guarantee: "transactional"` 的回滾承諾，透過 `rollback` 模式落地 |

### 並發

沿用標準狀態目錄慣例的立場：核心規範不處理多實例並發。若同名程式預期多實例並發，應將恢復記錄以 PID / session 隔離（如 `.state/<program_name>/<pid>/recovery.json`），否則彼此覆蓋。

### 完整範例

一個「可續傳的大檔下載器」：

```python
ai_core.register(
    lifecycle="one_shot",
    state="stateful_external",
    state_dirs=["state", "data"],
    interruptible="resumable",
    guarantee="idempotent",
)
```

被中斷後重跑時，`.state/<name>/recovery.json`：

```json
{
  "status": "in_progress",
  "mode": "resume",
  "ts": "2026-05-23T10:00:00Z",
  "payload": "recovery/offset.json"
}
```

語意解讀：程式重新啟動，自動讀到 `status: "in_progress"` + `mode: "resume"`，從 `payload` 記錄的 offset 接續下載，不重下已完成的部分（`guarantee: "idempotent"` 保證重跑不累積副作用）。完成後 `status` 設為 `"done"`。
