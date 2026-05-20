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

## 歷史紀錄

2026-05-18 之前的所有設計點已遷移至 `docs/architectures/`，對應表見舊版 `thinking.md`（git history）。
