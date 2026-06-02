# cws-no-llm — PROJECT.md

## 衍生目標

將 [cultivation-world-simulator](../../analysis/cultivation-world-simulator/) 的 **LLM 智能層完整替換為本地規則 AI + 詞庫組合文字系統**，使遊戲在**零網路、零 API Key、零 Ollama** 的環境下可完整運行，同時維持與原版相同的遊玩體驗骨架。

主要解決的問題：
1. 原版每月模擬需呼叫數十次 LLM API，速度慢、成本高、離線不可用
2. 透過規則 AI + 詞庫組合達到「Dwarf Fortress 風格涌現」，邏輯正確但文字有變化性

---

## 源專案

- **名稱**: cultivation-world-simulator v3.4.0
- **分析文件**: `analysis/cultivation-world-simulator/`
  - L1 概覽: `architecture/01_level1_overview.md`
  - L2 模組: `architecture/02_level2_modules.md`
  - 模擬迴圈: `html/simulation_loop.html`
  - LLM 整合: `html/llm_integration.html`
- **原始碼**: `projects/cultivation-world-simulator/src/`

---

## 技術棧

| 面向 | 選擇 |
|---|---|
| 後端語言 | Python 3.10+（與原版一致） |
| 規則 AI 模組 | 純 Python（無外部 AI 依賴） |
| 詞庫/模板 | Python 字典 + 格式字串（不用模板引擎） |
| 前端/伺服器 | 與原版完全相同（FastAPI / Vue3 / PixiJS） |
| 資料格式 | YAML（詞庫/模板）+ Python 常量 |

---

## 核心方向：Shim Layer 替換策略

**不重寫遊戲邏輯**。遊戲的世界規則、動作系統、宗門系統、存讀檔全部保留原版。  
只替換 `src/utils/llm/client.py` 的 `call_llm_with_task_name()` 背後的實作——在同一個介面下，把「送給 LLM」改成「交給本地 AI 引擎」。

```
原版流程:  call_llm_with_task_name(task, template, infos) → urllib POST → LLM → JSON
新版流程:  call_llm_with_task_name(task, template, infos) → local_ai.dispatch(task, infos) → JSON
```

這樣上層 Phase 代碼（simulator_engine/phases/）**完全不用動**。

---

## 16 個 LLM 任務的替換方案一覽

| 任務名稱 | 原本做什麼 | 替換方案 | 難度 |
|---|---|---|---|
| `action_decision` | 決定 NPC 本月做什麼 | **效用 AI**（Utility AI）評分 | ★★★★ |
| `long_term_objective` | 規劃長期目標 | **目標優先級引擎** | ★★★ |
| `sect_decider` | 宗門年度策略 | **宗門策略決策樹** | ★★★ |
| `single_choice` | 角色扮演選擇項 | **情境選項表**（預定義） | ★★★ |
| `relation_resolver` | 計算互動 → friendliness delta | **公式 + 性格相容矩陣** | ★★ |
| `relation_delta` | 同上（精確 delta） | 同上 | ★★ |
| `history_influence` | 歷史對當前的影響 | **事件累積評分** | ★★ |
| `sect_thinker` | 宗門年度思考文字 | **模板 + 宗門狀態填充** | ★★ |
| `story_teller` | 事件敘事文字 | **詞庫組合模板** | ★★ |
| `interaction_feedback` | 互動回饋描述 | **詞庫組合模板** | ★★ |
| `nickname` | 江湖外號 | **成就詞庫拼接引擎** | ★★ |
| `backstory` | 角色身世背景 | **傳記模板 + 詞庫** | ★ |
| `random_minor_event` | 小型隨機事件文字 | **預定義事件表 + 模板** | ★ |
| `sect_random_event` | 宗門隨機事件 | **預定義事件表** | ★ |
| `sect_random_event_reason` | 事件原因描述 | **原因模板** | ★ |
| `custom_content_generation` | 自訂內容生成 | **隨機池選取**（簡化） | ★ |

---

## 完成定義

### Phase 0（最低可用）
- [x] 所有 LLM 任務有 stub 實作（返回合法最小值）— `src/local_ai/dispatcher.py`
- [x] Shim 打入 `src/utils/llm/client.py::call_llm_with_task_name()`
- [ ] 遊戲可在無網路環境啟動並運行完整月份模擬（待實機測試）
- [ ] 不崩潰，事件入庫正常（待實機測試）

### Phase 1（可玩性）
- [ ] `action_decision`：效用 AI 讓 NPC 做出合理決策（不亂動）
- [ ] `relation_resolver/delta`：關係演化有公式邏輯
- [ ] `long_term_objective`：角色有合理目標

### Phase 2（有趣性）
- [ ] `story_teller / interaction_feedback`：詞庫組合文字有變化性
- [ ] `nickname`：外號有成就感
- [ ] `backstory`：背景故事多樣

### Phase 3（組織智能）
- [ ] `sect_decider`：宗門會做出合理策略決策
- [ ] `sect_thinker`：宗門有年度反思文字

### Phase 4（完整等價）
- [ ] 所有 16 個任務完整實作
- [ ] 基準測試：100 月模擬無崩潰
- [ ] 與原版行為對比測試

---

## 專案進度

- [x] 衍生目標定義
- [x] 設計文件 (`docs/design_overview.md`)
- [x] Phase 0：全任務 stub + shim 部署（待實機驗證）
- [ ] Phase 1：核心 AI（action_decision、relation、objectives）
- [ ] Phase 2：敘事系統（詞庫、模板）
- [ ] Phase 3：宗門 AI
- [ ] Phase 4：完整等價測試
