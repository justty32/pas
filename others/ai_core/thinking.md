# thinking.md

設計靈感與尚未進入正式文件的想法。

---

## 專案定位（2026-05-20 更新）

**ai_core 的用途是為 Heuristic Learning 提供基礎設施。**

Heuristic Learning（HL）是一種替代梯度更新的迭代範式：coding agent 直接編輯策略程式碼，環境回饋驅動下一輪改進，舊能力固化為測試與版本差異，而非消失在模型權重裡。

參考：[Learning Beyond Gradients](https://trinkle23897.github.io/learning-beyond-gradients/#zh)

ai_core 各元件對應的 HL 角色：

| ai_core 元件 | HL 角色 |
|---|---|
| `entry_manager` + `client` | LLM 監督者的呼叫介面 |
| `author` | agent 產生 / 修改策略函式 |
| `hub` + `funcs/` | 策略函式庫（Heuristic System） |
| `author` dry-run + retry | 環境回饋驅動的改進迴圈 |
| `--metadata` 介面 | agent 理解工具的唯一入口 |

---

## Metadata 設計補充（2026-05-20）

> 朝 coding agent 一側看，能接受多少耦合複雜度，取決於模型能力、上下文長度、memory 質量、工具質量、整體迭代速度。

**metadata 的職責是把認知負擔從 agent 身上搬走。** 這意味著 metadata 不只是描述「函式是什麼」，還要描述「agent 使用這個函式時需要多少認知資源」。

目前 `MetadataView` 的缺口：

| 缺失欄位 | 對應維度 | 說明 |
|---|---|---|
| `complexity` / `cognitive_load` | 模型能力 | 這個函式有多難用對？影響 agent 是否應拆解或迴避 |
| `memory_hints` | memory 質量 | 成功執行後哪些輸出值得跨輪次記住——**最優先補的欄位** |
| `idempotent` / `retry_safe` | 迭代速度 | 重跑有副作用嗎？agent 判斷是否重試時不能靠猜 |
| `semantic_coupling` | 工具質量 | 使用模式上常與哪些函式搭配——與 `dependencies`（技術依賴）不同 |

`memory_hints` 最關鍵：HL 的價值建立在跨輪次積累上，若函式不宣告哪些輸出值得記，agent 只能靠猜，memory 質量就會不穩定。

---

## Index 與 Metadata 的可變性，以及 Hub 作為透鏡（2026-05-21）

### 核心洞見：index 與 metadata 都不是靜態的

**Index 的兩層語意：**

| 層次 | 說明 | 穩定性 |
|---|---|---|
| 規範索引（canonical） | 絕對路徑 / module 完整路徑，指向「這個東西本身」 | 穩定，不隨環境改變 |
| 參照（reference） | 相對路徑 / hub-local name，指向「在某個上下文中怎麼找到它」 | 隨工作目錄、所在 hub 等上下文變動 |

相對路徑隨工作目錄改變，這不是缺陷——reference 是 canonical index 在特定上下文中的投影形式。

**Metadata 的可變性：**

Metadata 可以依 **subcommand 結構**改變，類比 `git --help` vs `git remote --help`：

- `xxx.sh --metadata` → 全域 metadata
- `xxx.sh subcommand --metadata` → 該 subcommand 的 metadata

**輸入不影響 metadata。** 無論 stdin、pipe 上游、還是 flag 帶入的資料，都不改變 metadata 的輸出。以 `-` 或 `--` 開頭的 flag 不得與 `--metadata` 混用（混用應報錯）。

Metadata 的可變性只有一個軸：**靜態的命令層次（subcommand）**，而非動態的執行期資料。

---

### Hub 是透鏡（lens）

Hub 是 index 的聚集，但對 hub 的**呼叫者**而言，hub 重新定義了 index 與 metadata 的形貌：

**Index 的重定義（命名空間化）**：
```
原始 canonical index：  ./tools/professor.sh
透過 hub 看到的 index：  prompt-hub/professor
```
Hub 提供一個新的命名空間層，把分散的路徑收攏為統一的邏輯名稱。

**Metadata 的重定義（透鏡式轉換）**：
Hub 可以對 metadata 做：
- **擴增**：加上 hub 自己的分類、tag、排序權重
- **過濾**：只暴露 `summary`，省略 `description`，節省 caller 的 context 用量
- **彙總**：把語意相近的函式群組成一份聯合描述

> 透鏡不改變物體本身，只改變觀察者看到的形象。Hub 的本質是**聚合 + 轉換**，不只是被動的目錄列表。

**推論：Hub 可以被組合。** Meta-hub 把多個 hub 的 index 再聚合，形成更高層的透鏡。每一層透鏡各自做轉換，外層 caller 只看到最終的聚合結果。

---

## 歷史紀錄

2026-05-18 之前的所有設計點已遷移至 `docs/architectures/`，對應表見舊版 `thinking.md`（git history）。
