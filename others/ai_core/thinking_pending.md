# thinking_pending.md

待討論主題（2026-05-21）

---

## 1. 路由相關工具設計（Indexer / Router / Switch / Hub）

詳細設計記錄：`thinking_routing.md`。

已確認拆分：
- **Indexer**：掃描 → 靜態索引，已確認
- **Router**：name mapping + subprocess dispatch，mapping 來源無硬性規定（設定檔、AI 導航等），標準規範待定
- **Switch**：有條件邏輯的 router，標準規範待定
- **Router 升級版**：加入安全憑證檢查 / 資源消耗管理，待設計

待設計：
- Router mapping 的標準規範
- Switch 的標準規範
- Router 升級版的具體設計
- **Hub 的完整定義**（已確認將脫離網路概念，進入另一個領域，尚未想好）

---

## 2. Small Function Center（SFC）設計

詳細設計記錄：`thinking_sfc.md`。

待設計：
- Tiny function 設定檔的具體格式
- 呼叫介面細節（參數傳遞方式）
- 動態 API（新增 / 持久化 tiny function）
- SFC 與 hub 的協作：hub 如何得知 SFC 旗下有哪些 subcommand

---

## 3. 持久性程式設計（persistent → server）

現有記錄：`thinking_layers.md`（執行模型分類）。

已確認立場：
- **持久性程式基本上建議設計成 server**（在 one-shot 與 multi-shot 之外的第三條路）
- `thinking_layers.md` 裡 JSON-RPC over stdin/stdout 的選項需要重新評估或更新

待設計：
- Server 的標準 lifecycle（啟動、就緒、處理請求、關閉）
- 對外介面規範（HTTP API 的基本 endpoint 慣例）
- 與 `--metadata` 協定的整合（server 啟用提示已有 §4.8，但 lifecycle 本身還沒有）
- Persistent 程式的 snapshot/checkpoint 機制（`thinking_layers.md` 提到「本質是 mini git」，尚未設計）

---

## 4. Singleton 資源設計

現有記錄：`CLAUDE.md`（LLM Entry Manager 是標準案例）、`docs/architectures/03_entry_manager.md`。

已知：
- Singleton 的觸發條件：資源有限，且請求者是多個不認識彼此的 caller
- 標準模式：queue + consume rate 管理
- LLM Entry Manager 是這個模式的具體實例

待設計：
- 通用 singleton 模式的抽象：什麼是「singleton 資源」的完整定義
- Queue 的標準介面（enqueue、dequeue、cancel）
- Consume rate 管理的標準介面（token、金錢、算力等不同維度）
- 多個 singleton 資源之間的協調（例如 LLM entry A 與 entry B 共用 GPU）

---

## 5. 調用鏈設計

現有記錄：`thinking_layers.md`（輕量追蹤方案）、`docs/architectures/02_protocol.md`（§5 錯誤處理慣例）。

### 定義

**調用鏈**在 shell 世界中指：process 與其子 process，或 pipeline 的前後節點。  
**程式內部的函數調用鏈**不在標準規範範疇內，由程式自行處理。

### 已確認立場：多調用鏈並發

標準規範不考慮多個調用鏈同時進行的問題。若使用者有相關需求，需自行處理相關風險。

| 問題 | 標準規範立場 |
|---|---|
| 呼叫順序 | 不管——由使用者自行決定與協調 |
| 資源搶占 | 建議將需要謹慎存取的資源交由某個持續性 server 管理；使用 singleton 也是推薦選擇 |

### 追蹤與可操作性（待設計）

已知：
- 輕量方案：每個工具在 stderr 輸出結構化 JSON log，成本接近零，由最外層 caller 決定是否收集

待設計：
- 調用鏈 ID 的傳遞機制（如何讓整條鏈共享同一個 trace ID）
- 收集工具：誰來彙整 stderr 的結構化 log、輸出成可讀的調用樹
- 可操作性：能否根據調用鏈紀錄重跑某一段、跳過某個節點、注入替代輸出

### 錯誤處理（待設計）

已知：
- stdout 正常結果、stderr 錯誤、exit code 非 0 表示失敗
- `--json-errors` 旗標讓 stderr 輸出結構化 JSON 供程式 caller 讀取

待設計：
- 調用鏈中途失敗時的傳播策略（fail-fast vs 繼續執行並標記）
- Retry 策略的標準化（`retriable` 欄位已有，但 retry 的實際行為由誰負責？）
- 部分失敗的彙報格式（整條鏈結束後如何彙整哪些節點成功、哪些失敗）

---

## 6. 跨邊界調用的統一設計（含分散式狀態）

現有記錄：`thinking_oop.md`（`outside_progs` 統一呼叫介面）。

### 已確認立場

**API 調用（HTTP）、shell 調用（subprocess）、程式內部函數調用，本質上是同一件事**——函式呼叫跨越不同的邊界：

| 邊界 | 呼叫形式 |
|---|---|
| 程式內部 | 直接函式呼叫 |
| 跨 process（shell） | subprocess + stdin/stdout |
| 跨網路（API） | HTTP request / response |

三者概念相同，只是傳遞機制不同。`outside_progs` 的統一呼叫介面建立在這個等價性之上。

### 待設計

額外設計工作：考慮**分散式系統的狀態問題**——當調用跨越網路邊界時，狀態的一致性、失敗恢復、冪等性等問題與本地調用有本質差異，需要專門設計。
