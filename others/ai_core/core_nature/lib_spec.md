# lib_spec.md

ai_core Python library 的 API 設計細節。

---

## §1 I/O 出入口（entries）

### metadata field

| key | 型別 | 說明 |
|---|---|---|
| `entries` | object | key 為自由命名的語意名稱，value 為該 entry 的屬性物件 |

**預設值**：若 `entries` 缺席，等同宣告單一 stdio entry（batch、text、雙向）。

---

### entry 屬性規格

每個 entry 的 value 為一個物件，包含以下欄位：

#### `able_in` / `able_out`

| key | 型別 | 說明 |
|---|---|---|
| `able_in` | bool | 此 entry 是否接收外部資料（輸入方向）|
| `able_out` | bool | 此 entry 是否向外輸出資料（輸出方向）|

兩者可同時為 `true`（雙向，如互動式 entry）。

#### `mode`

描述資料流動形式。可為字串或物件。

**字串形式：**

| 值 | 語意 |
|---|---|
| `"batch"` | 一次性交換：輸入讀完後才開始處理，輸出一次寫完 |
| `"streaming"` | 持續性流動：資料逐筆產生或消費 |
| `"interactive"` | 執行途中需要對方即時介入（如 stdin prompt） |

**物件形式（用於 streaming 需要描述速率）：**

```json
"mode": {
  "type": "streaming",
  "rate": "20b/s"
}
```

```json
"mode": {
  "type": "streaming",
  "chunk_size": "4kb",
  "interval": "500ms"
}
```

物件形式中 `type` 為必填，其餘速率欄位為選填。

#### `type`

描述資料的內容格式。可為字串或物件。

**字串形式：**

| 值 | 語意 |
|---|---|
| `"text"` | 純文字，編碼未指定（呼叫方自行假設） |
| `"binary"` | 二進位資料 |

**物件形式（需要指定編碼或 MIME）：**

```json
"type": {"base": "text", "encoding": "utf-8"}
"type": {"base": "binary", "mime": "image/png"}
```

#### `channel_constraint`（選填）

宣告此 entry 對可接受 channel 的品質下限。mapping 層依此過濾。

| 值 | 語意 |
|---|---|
| `"stable"` | 只接受穩定通道（file、stdio）；不接受 http / socket 等有延遲或中斷風險的通道 |
| 缺席 | 無限制，任何通道皆可 |

#### `terminal_binding`（選填）

僅在 terminal 環境下有意義。描述此 entry 在 CLI 中如何被接線。

```json
"terminal_binding": {
  "argflag": "--input",
  "default": "stdin"
}
```

| key | 型別 | 說明 |
|---|---|---|
| `argflag` | string | 對應的 argparse flag（如 `"--input"`） |
| `default` | string | 未指定 flag 時的預設接線（如 `"stdin"`、`"./data.txt"`） |

換環境時，`terminal_binding` 整塊忽略即可，entry 語意不受影響。

---

### 完整範例

```python
ai_core.register(
    lifecycle="persistent",
    state="stateful_external",
    entries={
        "entry_states": {
            "able_in": False,
            "able_out": True,
            "mode": {"type": "streaming", "rate": "20b/s"},
            "type": "text",
        },
        "entry_trigger": {
            "able_in": True,
            "able_out": False,
            "mode": "batch",
            "type": "text",
            "channel_constraint": "stable",
        },
        "entry_content": {
            "able_in": True,
            "able_out": False,
            "mode": "batch",
            "type": "binary",
            "terminal_binding": {
                "argflag": "--content",
                "default": "./data.bin",
            },
        },
    },
)
```

`--metadata` 輸出：

```json
{
  "lifecycle": "persistent",
  "state": "stateful_external",
  "entries": {
    "entry_states": {
      "able_in": false,
      "able_out": true,
      "mode": {"type": "streaming", "rate": "20b/s"},
      "type": "text"
    },
    "entry_trigger": {
      "able_in": true,
      "able_out": false,
      "mode": "batch",
      "type": "text",
      "channel_constraint": "stable"
    },
    "entry_content": {
      "able_in": true,
      "able_out": false,
      "mode": "batch",
      "type": "binary",
      "terminal_binding": {"argflag": "--content", "default": "./data.bin"}
    }
  }
}
```

---

### Terminal 環境預定義 entry 名稱

> 此節專屬 terminal（CLI / shell）環境。在其他環境中，這些名稱無特殊意義。

使用以下預定義名稱時，其屬性應符合標準定義：

| 名稱 | `able_in` | `able_out` | `mode` | `type` | 說明 |
|---|---|---|---|---|---|
| `stdin` | `true` | `false` | `"batch"` 或 `"interactive"` | `"text"` | 標準輸入流 |
| `stdout` | `false` | `true` | `"batch"` 或 `"streaming"` | `"text"` | 標準輸出流 |
| `stderr` | `false` | `true` | `"streaming"` | `"text"` | 標準錯誤輸出 |

規則：

- `mode` 的具體值仍需在 entry 中明確宣告
- `stderr` 通常不需要出現在 entries 中（屬程式內部的診斷輸出，呼叫方無需感知）
- 檔案型入出口（如 `--input file.txt`）使用自訂名稱，並搭配 `channel_constraint: "stable"` 及 `terminal_binding`；無預定義名稱
- 其他環境（http、socket 等）的預定義名稱留待各環境規範定義

---

## `register()`

### 介面

```python
ai_core.register(**kwargs)
```

### 規則

1. **只能呼叫一次**；第二次呼叫直接 crash（`RuntimeError`）
2. 必須在 `argparse.parse_args()` 之前呼叫
3. 呼叫後自動攔截 `--metadata` flag

### `--metadata` 攔截行為

| 情況 | 行為 |
|---|---|
| `sys.argv[1] == "--metadata"` | 將所有 metadata 以 JSON 輸出到 stdout，`sys.exit(0)` |
| `--metadata` 出現在 `sys.argv` 其他位置 | 報錯到 stderr，`sys.exit(1)` |
| `--metadata` 不存在 | 儲存 metadata，正常 return |

`--metadata` 只能單獨使用，不得與其他引數混用。

### 輸出格式

純 JSON 到 stdout，無 header / wrapper：

```json
{"lifecycle": "one_shot"}
```

### 範例

```python
import ai_core

def main():
    ai_core.register(lifecycle="one_shot")

    parser = argparse.ArgumentParser()
    # ...
```

---

## §2 生命週期

### metadata field

| key | 型別 | 允許值 |
|---|---|---|
| `lifecycle` | string | `"one_shot"` \| `"persistent"` |

### 說明

描述程式從啟動到結束的持續模式。

| 值 | 語意 |
|---|---|
| `"one_shot"` | 啟動 → 執行 → 結束。程序存活時間與任務等長 |
| `"persistent"` | 啟動後持續存活，等待請求或持續產出，直到被顯式終止 |

**預設值**：若此 key 不存在、為 `null`、或為 `false`，等同於 `"one_shot"`。只有明確需要 `"persistent"` 時才需宣告。

---

## §3 跨呼叫狀態

### metadata fields

| key | 型別 | 說明 |
|---|---|---|
| `state` | string | `"stateless"` \| `"stateful_external"` |
| `state_dirs` | array | 遵守標準目錄慣例時使用的目錄子集；見 [`composite_spec.md`](composite_spec.md) |

### 說明

描述程式在多次執行之間是否保有、影響或累積狀態。

| 值 | 語意 |
|---|---|
| `"stateless"` | 每次執行互相獨立，輸出完全由當次輸入決定。可安全重試、平行執行。 |
| `"stateful_external"` | 狀態存於程式外部。呼叫方需知悉此程式會對外部狀態產生讀寫副作用。 |

**預設值**：若此 key 不存在、為 `null`、或為 `false`，等同於 `"stateless"`。只有明確需要 `"stateful_external"` 時才需宣告。

> `"stateful_internal"`（狀態存於程序記憶體）理論上存在，但程序結束後記憶體釋放，實務上等同於每次 one-shot 都從外部重載狀態，故不列為獨立值。

### 標準狀態目錄慣例（Terminal 實作）

`state: "stateful_external"` 在 terminal 環境下的標準路徑慣例（`.config`、`.cache`、`.state`、`.data`），以及其對 §1 / §5 / §6 的跨軸影響，定義於 [`composite_spec.md`](composite_spec.md)。

### 與 §2 的關聯

| 組合 | 常見形態 |
|---|---|
| `lifecycle: "one_shot"` + `state: "stateless"` | 最典型的 CLI 工具：給定輸入 → 產出輸出 → 結束（兩者皆為預設，可省略宣告） |
| `lifecycle: "one_shot"` + `state: "stateful_external"` | 資料庫更新腳本、append log 工具：每次執行都改動外部狀態 |
| `lifecycle: "persistent"` + `state: "stateless"` | 無記憶的 stateless server（每個請求獨立處理，無跨請求狀態） |
| `lifecycle: "persistent"` + `state: "stateful_external"` | 有狀態的 server（e.g., session 管理、累積計數器，狀態寫入外部） |

### 對呼叫方的影響

- `"stateless"`：呼叫方可自由重試或並行，無須考慮副作用。
- `"stateful_external"`：呼叫方應確認狀態路徑（由 `--help` 或標準目錄慣例推斷）；並行執行需自行處理競爭條件（race condition）。

### register() 範例

```python
import ai_core

def main():
    ai_core.register(
        lifecycle="one_shot",
        state="stateful_external",
    )

    parser = argparse.ArgumentParser()
    # ...
```

`--metadata` 輸出：

```json
{"lifecycle": "one_shot", "state": "stateful_external"}
```

---

## §5 可中斷性

### metadata field

| key | 型別 | 允許值 |
|---|---|---|
| `interruptible` | string \| object | 見下表 |

**預設值**：若此 key 缺席、為 `null` 或 `false`，等同 `"unsafe"`（最保守）。

---

### 說明

描述程式對中斷（強制退出、外部 kill、環境切換）的承受能力，以及中斷後對外部狀態的影響。此軸為跨環境的抽象描述，不依賴具體的 OS 信號或平台機制。

> **設計備註**：「損毀外部狀態」的定義是廣義的——不只是寫到一半造成資料損毀，也包括「程式被中斷、任務未正常完成，因此外部狀態未達到預期結果」。後者屬於任務層面的不完整，同樣是呼叫方需要知道的風險。相關定義之後可能需要精心深挖與設計。

**字串形式（標準值）：**

| 值 | 語意 |
|---|---|
| `"safe"` | 可隨時中斷；無副作用，中斷後外部狀態不受影響 |
| `"unsafe"` | 中斷可能損毀外部狀態，或任務未完成導致狀態未達預期（預設值） |
| `"resettable"` | 中斷損毀狀態，但程式提供重置機制可恢復至某個安全狀態（不保證回到原始狀態） |
| `"rollback"` | 中斷損毀狀態，但程式提供回滾機制可撤銷所有未完成的修改，完整還原至呼叫前的原始狀態 |
| `"resumable"` | 可中斷，且程式支援從斷點繼續執行；中斷不損毀狀態，下次呼叫從中斷處接續，而非從頭開始 |
| `"graceful"` | 可中斷，但不能直接 kill；需給程式時間完成 cleanup 後正常退出 |

**物件形式（需補充細節，或非標準情形）：**

```json
{"type": "resettable", "reset_hint": "--reset"}
```

```json
{"type": "graceful", "timeout": "5s"}
```

```json
{"type": "conditional", "condition": "llm_entry 正常運作時可隨時中斷"}
```

物件形式中 `type` 為必填，其餘選填。`"conditional"` 及其他非標準型別屬自定義，value 格式不受限制。

---

### 與 §3 / §6 的關係

| 軸 | 職責 |
|---|---|
| §3 跨呼叫狀態 | 描述程式有無跨執行的外部狀態 |
| §5 可中斷性 | 描述中斷對當次執行與外部狀態的影響 |
| §6 執行保證 | 描述中斷後如何恢復（idempotent / transactional） |

`"safe"` 通常與 `state: "stateless"` 搭配；但兩者獨立——stateless 程式執行途中仍可能有未提交的外部寫入，此時 `interruptible` 應為 `"unsafe"` 或 `"graceful"`。

---

### register() 範例

```python
ai_core.register(
    lifecycle="persistent",
    state="stateful_external",
    interruptible={"type": "resettable", "reset_hint": "--reset"},
)
```

`--metadata` 輸出：

```json
{
  "lifecycle": "persistent",
  "state": "stateful_external",
  "interruptible": {"type": "resettable", "reset_hint": "--reset"}
}
```

---

## §4 資源特性

> **設計備註**：`resources` 採自由 key-value 結構。標準規範精確定義最常見的具體資源 key（memory / gpu / time / disk / network）；其定義固定。自定義 key 的 value 格式不受限制。

### metadata field

| key | 型別 | 說明 |
|---|---|---|
| `resources` | object | key 為資源名稱，value 為該資源的需求描述 |

**預設值**：若 `resources` 缺席，等同宣告無任何資源需求聲明。

---

### 設計原則

`resources` 為自由 key-value 結構，與 `entries` 同模式：

- key 完全自由命名——可以是顯性的系統資源（`memory`、`gpu`），也可以是抽象的隱性依賴（`llm_entry`、`db`）
- **預定義 key**（見下節）有規範的 value 格式，hub 可直接解析
- **自定義 key** 的 value 格式由撰寫者自訂；hub 讀得到但不一定能理解，至少讓呼叫方知道此依賴存在

---

### 預定義 key

#### `memory`

描述記憶體用量。

字串形式（宣告峰值）：

```json
"memory": "4gb"
```

物件形式（需要區分各階段）：

```json
"memory": {"startup": "2gb", "peak": "8gb", "idle": "500mb"}
```

| 子欄位 | 說明 |
|---|---|
| `startup` | 啟動時立即佔用（e.g., 模型載入後常駐） |
| `peak` | 執行途中的記憶體峰值 |
| `idle` | Persistent 程式閒置時的底線佔用 |

三個子欄位皆選填；`idle` 僅對 `lifecycle: "persistent"` 有意義。

#### `gpu`

布林形式（宣告是否需要 GPU）：

```json
"gpu": true
```

物件形式（需要宣告 VRAM 用量）：

```json
"gpu": {"vram": "6gb"}
```

#### `time`

描述執行時間預估。

字串形式（預期執行時間）：

```json
"time": "30s"
```

物件形式（需要宣告上限）：

```json
"time": {"expected": "30s", "max": "5m"}
```

#### `disk`

執行期間的暫用磁碟空間（結束後清除）。持久性資料（§3 `.data` 目錄）不在此描述。

```json
"disk": "500mb"
```

#### `network`

宣告執行期間是否需要網路存取。

```json
"network": true
```

---

### 單位格式

| 種類 | 單位 | 範例 |
|---|---|---|
| 容量 | `b` / `kb` / `mb` / `gb` | `"512mb"`、`"4gb"` |
| 時間 | `ms` / `s` / `m` / `h` | `"500ms"`、`"30s"`、`"5m"` |

---

### 自定義 key 範例

```json
"resources": {
  "llm_entry": true,
  "db": {"type": "postgres"},
  "render_server": {"port": 7860}
}
```

value 格式無限制，由撰寫者自行定義語意。

---

## §6 執行保證

### metadata fields

| key | 型別 | 說明 |
|---|---|---|
| `guarantee` | string | 程式對執行結果的承諾（狀態一致性） |
| `dry_run` | bool \| object | 是否支援 dry-run 模式（能力宣告） |

**預設值**：
- `guarantee` 缺席或 `null` → `"none"`（呼叫方自行承擔重試或中斷後果）
- `dry_run` 缺席或 `false` → 不支援 dry-run

---

### `guarantee` 說明

描述程式對其執行副作用的承諾，尤其是失敗或中斷後的狀態一致性。

| 值 | 語意 |
|---|---|
| `"none"` | 無承諾（預設值）；重複執行或中途失敗的後果由呼叫方自行承擔 |
| `"idempotent"` | 重複執行與執行一次等效；中斷後安全重試，不會累積額外副作用 |
| `"transactional"` | 全部成功或完全不發生（ACID 語意）；中途失敗自動回滾，不留部分狀態 |

> **與 §3 的關係**：`guarantee` 對 `state: "stateless"` 的程式通常無意義——stateless 程式本身即等同冪等，亦無外部狀態可回滾。有意義的保證宣告限於 `state: "stateful_external"` 的程式。

---

### `dry_run` 說明

宣告程式是否支援 dry-run 模式。開啟時，程式執行完整邏輯但**不實際修改外部狀態**，用於預覽副作用。

布林形式（支援，flag 名稱由程式自訂）：

```json
"dry_run": true
```

物件形式：

```json
"dry_run": {
  "flag": "--dry-run",
  "state_entry": "stdout",
  "error_entry": "stderr"
}
```

| 子欄位 | 型別 | 說明 |
|---|---|---|
| `flag` | string | 觸發 dry-run 模式的 CLI flag（選填）|
| `state_entry` | string | dry-run 執行時，輸出「若正式執行會發生什麼」的 entry 名稱；引用 `entries` 中的 key（選填） |
| `error_entry` | string | dry-run 執行時，輸出錯誤訊息的 entry 名稱；引用 `entries` 中的 key（選填） |

三個子欄位皆選填；物件形式中至少應填一個有意義的欄位，否則用布林形式即可。

> **注意**：`dry_run` 是能力宣告（程式支援此模式），而非執行時的當前狀態。呼叫方依此決定是否傳入對應 flag。

`dry_run` 與 `guarantee` 正交——兩者可同時存在：
- `guarantee: "transactional"` + `dry_run` → 正式執行具事務保證，且支援預覽
- `guarantee: "none"` + `dry_run` → 正式執行無保證，但可先用 dry-run 確認副作用
- `guarantee: "idempotent"` 無 `dry_run` → 冪等保證，呼叫方可直接重試而無需預覽

---

### 與 §5 可中斷性的關係

§5 描述「程式被中斷時的能力」；§6 描述「程式對執行結果的承諾」。兩軸獨立，但搭配使用時語意更完整：

| §5 `interruptible` | §6 `guarantee` | 中斷後行為 |
|---|---|---|
| `"unsafe"` | `"none"` | 外部狀態可能損毀或未完成；呼叫方需自行決定是否重試 |
| `"unsafe"` | `"idempotent"` | 可安全重試；重跑不會疊加副作用 |
| `"unsafe"` | `"transactional"` | 程式自身錯誤會自動回滾；但外部強制終止（kill）可能繞過回滾機制，外部狀態損毀風險仍存在 |
| `"safe"` | 任意 | 中斷無風險；§6 的承諾在 stateless 程式上意義較小 |
| `"rollback"` | `"transactional"` | 兩軸同向——程式對「中斷能回滾」與「執行具事務性」都做出承諾 |

---

### register() 範例

```python
ai_core.register(
    lifecycle="one_shot",
    state="stateful_external",
    guarantee="transactional",
    dry_run={
        "flag": "--dry-run",
        "state_entry": "stdout",
        "error_entry": "stderr",
    },
)
```

`--metadata` 輸出：

```json
{
  "lifecycle": "one_shot",
  "state": "stateful_external",
  "guarantee": "transactional",
  "dry_run": {
    "flag": "--dry-run",
    "state_entry": "stdout",
    "error_entry": "stderr"
  }
}
```

---

### 完整範例

```python
ai_core.register(
    lifecycle="persistent",
    resources={
        "memory": {"startup": "2gb", "idle": "500mb", "peak": "8gb"},
        "gpu": {"vram": "6gb"},
        "time": {"expected": "30s"},
        "llm_entry": True,
    }
)
```

`--metadata` 輸出：

```json
{
  "lifecycle": "persistent",
  "resources": {
    "memory": {"startup": "2gb", "idle": "500mb", "peak": "8gb"},
    "gpu": {"vram": "6gb"},
    "time": {"expected": "30s"},
    "llm_entry": true
  }
}
```

---

## §7 組合模式

**此軸不在本規範範圍內，不定義 metadata fields。**

組合模式描述的是呼叫鏈（call chain）的結構：fan-out/fan-in、proxy/wrapper、hook/callback、agentic loop 等。這是呼叫方（hub、router）的關切點，不是單一執行單元的屬性——程式本身不需要、也不應該知道自己被如何組合。

> 若日後需要描述呼叫鏈拓撲，應另立文件（如 `call_graph_spec.md`），而非在單一程式的 `--metadata` 中宣告。

---

## §8 環境模式

**此軸不在本規範範圍內，不定義 metadata fields。**

程式本身不管理自己的執行環境。本規範的預設假設為**穩定的 Linux 環境**；容器化、venv、resource limit 等屬於部署/執行層的選擇，不影響程式介面設計。

唯一例外是**包裝程式（wrapper）**——它的職責是修改子程式的執行環境（設置環境變數、切換工作目錄、套用 resource limit 等）。這個包裝程式本身是一個執行單元，其行為用其他軸描述；環境管理只是它的輸出副作用，不需要額外的 metadata field。
