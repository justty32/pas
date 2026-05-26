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

## `register()` 與 `intercept()`（宣告／攔截拆分）

> **設計演進**：早期版本的 `register()` 在呼叫時就**同時**做「宣告 metadata」與「攔截
> `--metadata`」兩件事，且攔截要求 `--metadata` 必須是唯一引數。這在三種情境下出問題：
> (A) git-style dispatcher 的 `prog <sub> --metadata` 不相容；(B) 單一執行檔含多種 lifecycle
> 的子命令無法各自宣告；(F) 在 module 頂層 `register()` 會在 import 時就讀 `sys.argv` / 攔截 /
> `sys.exit`，使工具無法被當 library 重用。現行規範把**宣告**與**攔截**拆成兩個動作。

### 介面

| 函式 | 職責 | 副作用 |
|---|---|---|
| `register(**kwargs)` | 宣告程式**頂層** metadata（dispatcher 的預設行為） | 無——只寫入內部登記，不讀 argv、不攔截、不 exit |
| `register_subcommand(name, **kwargs)` | 宣告某個**靜態子命令**的 scoped metadata（可與頂層不同 lifecycle） | 無 |
| `register_subcommand_resolver(fn)` | 註冊**動態子命令**解析器 `fn(name, store_override) -> dict \| None`（子命令名稱來自外部資料，如 store） | 無 |
| `intercept(argv=None)` | 顯式攔截 `--metadata`；命中則輸出 JSON 並 `sys.exit`，否則 **return 交還控制權** | 命中 metadata 查詢時 `sys.exit` |

### 規則

1. **`register*` 系列純宣告、無副作用**：可安全地在 import 時或 `main()` 內呼叫，import 不再有
   讀 argv / 攔截 / exit 的副作用（解 F）。
2. **`register()` 可重複呼叫**（last-write-wins，覆寫頂層 metadata）；不再因二次呼叫而 crash。
   慣例上每個程式只在自己以 `__main__` 身分執行時宣告一次。
3. **攔截由 `intercept()` 顯式負責**，須在 `argparse.parse_args()` 之前呼叫。葉子工具的典型形態
   是 `register(...)` 後緊接 `intercept()`。
4. **register 應在 `__main__` / `main()` 內呼叫**（見下方「import-time 副作用」節）。

### `intercept()` 攔截規則

先吃掉可選的前導 `--store DIR`（使 `prog --store DIR <sub> --metadata` 也成立），再依序判斷：

| argv（去掉 `--store DIR` 後） | 行為 |
|---|---|
| `["--metadata"]` | 印**頂層** metadata，`sys.exit(0)` |
| `[<name>, "--metadata"]` | 依序查「靜態子命令登記」→「動態 resolver」；命中印該 **scoped** metadata `exit(0)`；皆查無 → stderr 報錯 `exit(1)` |
| 其餘 | **return**（非 metadata 查詢，交回 caller 走一般 dispatch） |

> 與舊規範的差異：`prog <sub> --metadata` 由「報錯」變成「**合法的 scoped metadata 查詢**」
> （解 A）。`--metadata` 夾在一般引數中間（如 `prog --foo --metadata`）不再特別報錯——除非它
> 落入上表前兩列的形狀，否則一律視為一般引數交還 caller。

### 輸出格式

純 JSON 到 stdout，無 header / wrapper（`ensure_ascii=False`，metadata 可含非 ASCII）：

```json
{"lifecycle": "one_shot"}
```

### 範例

**葉子工具**（單一行為）：

```python
import ai_core

def main():
    ai_core.register(lifecycle="one_shot")
    ai_core.intercept()          # 命中 --metadata 則輸出並 exit；否則往下走

    parser = argparse.ArgumentParser()
    # ...

if __name__ == "__main__":
    sys.exit(main())
```

**dispatcher（含多種 lifecycle 子命令，解 A/B）**：

```python
def main():
    ai_core.register(lifecycle="one_shot", state="stateless")          # 頂層＝dispatcher 預設
    ai_core.register_subcommand("forge", lifecycle="persistent")       # forge 子命令是 server
    ai_core.register_subcommand_resolver(resolve_from_store)           # 動態子命令查 store
    ai_core.intercept()          # 處理 prog --metadata / prog <sub> --metadata 各變體
    # ... 一般 dispatch
```

`prog --metadata` 回頂層 `one_shot`、`prog forge --metadata` 回 `persistent`——同一執行檔不同
子命令各報自己的 lifecycle。

### register 的 import-time 副作用（慣例）

`register*` 系列已設計成純宣告，但**仍建議在 `main()` / `__main__` 區塊內呼叫**，不要放在 module
頂層。理由：頂層 metadata 是 module-global 的單例，若工具 A 在頂層 `register()`、又被工具 B
`import A` 來重用其函式，A 的頂層宣告會在 import 時就寫入全域、與 B 自己的宣告互相覆寫。把
`register()` 留在「確定以腳本身分執行」的 `main()` 內，import 重用時就完全無副作用。

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

## §9 確定性 / 隨機性（nondeterminism）

> 這是繼 §1–§6 之後**新增**的軸。前八軸描述的都是「執行特性」（怎麼跑、有無狀態、能否中斷…），
> 預設假設函式是**確定性**的（同輸入 → 同輸出）。但 ai_core 的核心對象之一是 LLM——一個天生
> **隨機**的函式。這個軸把「此環節是隨機的」標出來，並承載治理原則所需的**證書**。詳細的軸層
> 討論見 [`axis_spec.md` §9](axis_spec.md)。

### metadata field

| key | 型別 | 說明 |
|---|---|---|
| `nondeterministic` | bool \| object | 宣告此函式（或此調用環節）含不可確定性 |

**預設值**：若 `nondeterministic` 缺席、為 `null` 或 `false` → 視為**確定性**函式（同輸入同輸出）。
只有明確含隨機環節（典型是包了 LLM 的函式）時才宣告。

### 說明

| 形式 | 語意 |
|---|---|
| `nondeterministic: true` | **未認證的隨機環節**。只標記「這裡是隨機的」，是 LLM 馴化框架的觸發根，但尚未經測試認證。對應治理的「開機期」——允許存在，但帶著「待認證」的債。 |
| `nondeterministic: {…}` | **證書**。不是含糊的「這裡隨機」，而是「**此環節用模型 X、經測試組 Y、認證穩定度 Z%**」。對應治理的「成熟期」——LLM 不是被信任，是被**認證**，且可被**撤照**。 |

### 證書（object 形式）的建議欄位

沿用 §4 `resources` 的設計——**自由 key-value，預定義 key 有建議語意，自訂 key 不受限**。
validation 只確保它是 dict，不強制特定 key（規範「從粗糙到嚴整」，待 v0 驗證後再收緊）。

| 建議 key | 語意 |
|---|---|
| `model` | 此環節用哪個模型填（如 `"local-8b"`、`"claude-opus"`） |
| `test_set` | 認證所依據的測試組識別 |
| `stability` | 認證穩定度（如 `"92%"` 或 `0.92`）——證書的核心主張 |

### 為何是新軸，而非塞進既有軸

`nondeterministic` 與 `memoized`（見下「未入軸的決策」）共有一個處境：**沒有任何既有軸值可以
隱含它**。中斷恢復慣例之所以「不新增欄位」，是因為它能由 `interruptible` / `guarantee` 隱含觸發；
但「這函式是不是隨機的」在八軸裡完全無從推斷——`lifecycle` / `state` / `guarantee` 都描述不了。
因此它**必須**是一個獨立的宣告。

### 與其他軸的關係（正交）

`nondeterministic` 與所有執行特性軸正交：一個函式可以同時是 `nondeterministic: true` 且
`state: "stateful_external"` 且 `guarantee: "none"`。隨機性是「輸出由何決定」的性質，與「有無副作用」
「能否重試」彼此獨立。

> **與 §6 `guarantee` 的對照**：`guarantee` 講的是「對外部狀態的承諾」；`nondeterministic`
> 講的是「輸出本身可不可預測」。一個 LLM 包裝函式常是 `guarantee: "none"` + `nondeterministic: true`——
> 既不保證副作用冪等，輸出也不可預測。馴化框架（retry / vote / guard …，見 `try_implement/docs/`）
> 正是把後者收斂成「夠穩到能發證書」的機器。

### register() 範例

```python
# 開機期：標記隨機、尚未認證
ai_core.register(nondeterministic=True)

# 成熟期：帶證書
ai_core.register(nondeterministic={
    "model": "local-8b",
    "test_set": "code_qa_v1",
    "stability": "92%",
})
```

`--metadata` 輸出：

```json
{"nondeterministic": {"model": "local-8b", "test_set": "code_qa_v1", "stability": "92%"}}
```

---

## 未入軸的決策：`memoized`（純 runtime）

`memoized`（記憶化 / 輸入→輸出快取）曾與 `nondeterministic` 並列為候選新軸。**決策：不入
metadata 軸，維持純 runtime 行為**（由 `try_implement/lib/memoize.py` 這類 library 在執行期處理）。

理由：快取是**呼叫方 / library 的優化決策**，不是函式對外的語意承諾。一個函式「可不可以被快取」
其實由既有軸隱含——`nondeterministic` 缺席（確定性）＋ `state: "stateless"` 的函式天然可安全
memoize；隨機或有狀態的函式則否。因此 memoize 不像 `nondeterministic` 那樣「無既有軸值可隱含」，
不需要新欄位。這與「中斷恢復慣例不新增欄位」同精神：能由既有軸推斷的，就不膨脹軸層。

> 若日後出現「函式想主動宣告自己的快取版本 / TTL 語意」的真實需求（而非由呼叫方決定），再
> 重新評估是否補欄位。目前 `lib/memoize.py` 的 cache key / 失效策略由呼叫方明確指定，足夠。

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
