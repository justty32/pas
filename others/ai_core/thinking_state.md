# thinking_state.md

新想法紀錄（2026-05-21）

---

## Multi-shot 本質定義

**Multi-shot** 是一個抽象描述：**上次執行的結果會影響到下一次執行的程式**。  
當前的標準實現是針對 terminal 狀態（CLI / shell 世界）定義的。

---

## 標準實現規範（Terminal 版）

### 狀態檔位置

程式 `XXX` 執行時，在其**工作目錄**下存取以下路徑：

```
.config/<XXX>/      ← 或 .config/<XXX>.json（單檔形式）
.cache/<XXX>/       ← 或 .cache/<XXX>.json
.state/<XXX>/       ← 或 .state/<XXX>.json
```

四個標準目錄各自語意：

| 目錄 | 語意 |
|---|---|
| `.config` | 程式本身不會修改的設定（由人類或外部工具寫入） |
| `.cache` | 可在程式執行時間之外被任意刪除，程式不依賴其存在 |
| `.state` | 程式目前所在的 stage——執行進程、跨輪次的階段位置 |
| `.data` | 程式累積建造出來的成果性資料；重要、不可隨意刪除 |

`.state` 與 `.data` 的分野：`.state` 清掉只是忘記做到哪（可重置），`.data` 清掉是真的失去成果（需備份）。

沒有硬性規定四者都必須存在；標準實現要求實作者**按語意選用**。

### 檔案格式規則

- 每個位置可以是**資料夾**或**單檔**
- **單檔**（如 `.config/<XXX>.json`）：**必須是 `.json`，且內容為 JSON 物件**
- **資料夾內的檔案**（如 `.config/<XXX>/YYY.json`）：格式無限制

### 版本管理

標準實現規範**不包含版本管理**（刻意省略，保持簡單）。

---

## 本質深究：從 Terminal 到程式內函數

| 邊界 | multi-shot 的實現形式 |
|---|---|
| Terminal（CLI） | 工作目錄下的 `.config`、`.cache`、`.state` 檔案 |
| 程式內函數 | 由程式內部的 global manager 管理等效的 in-memory 結構 |

程式函數被呼叫一次 = terminal 下單一程式被呼叫一次。  
`.config`、`.cache`、`.state` 的概念在程式內部同樣存在，只是形式從檔案變成記憶體中的結構。

Library 提供統一介面，讓使用者不必手動操作檔案或 manager——  
（此處討論尚未完成，訊息中斷）

---

### 並發執行

核心規範不處理。標準實現建議：若 `XXX` 預期多實例並發，寫入 `.state/<XXX>` 時標註自身 PID。讀寫鎖由 OS 處理，具體標註格式與看見他人標註時的行為，由 `XXX` 撰寫者自行決定。

### Metadata 宣告慣例

建議在 metadata 中加入：

```json
{
  "is_multishot": true,
  "multi_shot_dirs": ["state", "data"]
}
```

`is_multishot: true` 是入口——值為 true 時，caller / hub 才進一步讀 `multi_shot_dirs`。`multi_shot_dirs` 列出此程式實際使用的目錄，省略則不宣告。

---

### 與其他 thinking 的關係

- `thinking_layers.md`：persistent 執行模型的 snapshot/checkpoint，建立在這裡的 `.state` 機制之上
- `thinking_production.md`：AI 生成函式後如何自動補上狀態宣告——尚未處理
