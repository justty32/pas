# thinking_routing.md

路由相關工具設計（2026-05-21）

名詞借用自區域網路中的 hub / router / switch 概念，但實際語意有所不同。

---

## Indexer

掃描指定資料夾中的可執行檔，產出靜態索引（`index.md`）供查找。  
不做路由、不做呼叫。One-shot 程式。

（詳見 `thinking_sfc.md` Hub/SFC/Indexer 三者區別）

### Indexer 升級版（待設計）

在基本索引之上，呼叫 AI 對被 index 的工具自動：
- 添加標籤（tags）
- 生成簡介（summary）
- 做分類（category）

產出的索引比純靜態版更豐富，方便 LLM caller 快速理解工具用途。具體設計待定。

---

## Router

**本質**：name → 某個可執行物 的 mapping，加上執行。

「可執行物」可以是：
- 單檔程式的路徑（`./tools/code_senior_and_very_smart.sh`）
- JSON store 中的腳本片段（來自 SFC 的 Layer 0 資料）
- 其他任何可被執行的東西

兩種情境在概念上是同一件事——router 不在意 mapping 的目標是檔案還是資料庫內容，只負責「查到 → 執行」。

```bash
router code_senior_a --lang c    # 查表後執行對應的可執行物
```

Mapping 的來源無硬性規定：可以是人工設定檔、從 indexer 輸出動態產生、或由 AI 自動導航——標準規範待定。

### Router 的升級版（待設計）

在基本路由之上，加入：
- 使用者安全憑證檢查
- 資源消耗管理

概念上類似網路中的 router 升級到 firewall / load balancer 的方向，但具體設計尚未開始。

---

## Switch

**本質**：有條件邏輯的 router。

Router 是單純的 mapping（一對一查表）；switch 在 mapping 之外，加入條件判斷：

> 若需求滿足某條件 → 導航到程式 A；否則 → 導航到程式 B

例如：檢查輸入語言是 C 還是 Python，分別路由到不同的 linter。

Switch 借用網路 switch 的名稱，但概念差異大——這裡的 switch 更接近條件式 dispatcher，不是廣播域分割。

具體標準規範待設計。

---

## Hub

**目前狀態**：概念尚未完整定義。

已知：
- 在本系統中，hub 的定位將**脫離網路概念**，進入另一個領域
- Hub 不等同於 indexer（靜態索引）、router（name mapping）、或 switch（條件路由）
- `thinking.md` 中有「Hub 作為透鏡」的早期設計思路（擴增、過濾、彙總 metadata），但此概念是否仍屬於 hub 或已分散給其他工具，待重新評估

待設計：hub 的完整定義與定位。
