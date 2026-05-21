# thinking_rma.md

新想法紀錄（2026-05-21）

---

## rma：資源監控包裝程式

### 動機

Shell 層面的記憶體與執行時間管理需要一個統一工具。Linux 已有相關工具：

| 需求 | 現有 Linux 工具 |
|---|---|
| 執行時間限制 | `timeout N cmd` |
| 記憶體 / CPU 時間 / 檔案限制 | `ulimit`, `prlimit` |
| CPU 優先度 | `nice`, `renice` |
| 測量用量（事後） | `/usr/bin/time -v`, `/proc/<pid>/status` |
| 完整資源隔離 | `cgroups v2`, `systemd-run --scope` |

**設計原則**：能利用的就利用，除非需求太特殊，作業系統無法快速搞定，否則不重複造輪子。  
rma 要做的，要麼是**統一多工具的呼叫介面**，要麼是**提供 Linux 工具沒有的特殊服務**；重複的部分要避免。

---

### 介面設計

```bash
rma --exec code_senior.sh --args lang c   # 包裝執行（rma 管理資源）
code_senior.sh --lang c                   # 普通執行（無資源管理）
```

實作語言：**C**，直接使用 `setrlimit()`、`getrusage()`、`fork()`、`waitpid()`，無 runtime 依賴，開銷低。

---

### rma 相對 Linux 工具的獨特價值

1. **統一介面**：`timeout`、`prlimit`、`nice` 語法各不同；rma 用單一介面同時管多個指標
2. **Alert callback**：超出閾值時呼叫指定的 `.sh`（Linux 工具只有 kill，沒有 callback）
3. **結構化 log**：用量統計寫入指定 JSON 檔，方便 hub / AI caller 事後讀取
4. **軟警告 + 延遲強殺**：先 SIGTERM + grace period，再 SIGKILL；`timeout` 沒有 grace period 機制
5. **`--json-errors` 整合**：違規時的 stderr 遵守 ai_core 錯誤協議（`{"type": "MemoryExceeded", ...}`）

監控維度包括：記憶體用量（RSS）、執行時間（wall time / CPU time）、CPU 核心占用。

---

### 開放設計問題

**`--metadata` 要怎麼處理？**

```bash
rma --exec code_senior.sh --metadata
```

兩條路：
- **透傳模式**：等同於呼叫 `code_senior.sh --metadata`，rma 不插手——rma 是透明包裝器
- **包裝模式**：回傳 rma 自己的 metadata（包含此 rma 實例設定的資源限制）——rma 是有身份的工具

這個決定影響 rma 在 hub 裡的定位。尚未決定。

---

### 與 `thinking_layers.md` 的關係

rma 對應 `thinking_layers.md` 執行模型表格中「管資源」的一格：

| | one-shot | persistent |
|---|---|---|
| **不管資源** | pipe-and-script | — |
| **管資源** | **one-shot 程式**（rma 包裝這一層） | 持續性程式 |

rma 是讓 pipe-and-script 升格為「受資源管控的 one-shot」的標準工具。
