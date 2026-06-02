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

### Phase 0（最低可用）✅ 完成
- [x] 所有 LLM 任務有 stub 實作（返回合法最小值）— `src/local_ai/dispatcher.py`
- [x] Shim 打入 `src/utils/llm/client.py::call_llm_with_task_name()`
- [x] `sect_random_event.py::_generate_reason_fragment()` 加 local shim（stub reason fragment）
- [x] `autonomous_custom_content_service.py::should_trigger()` 本地模式直接 return False
- [x] 實機驗證：102→107 年模擬無崩潰、零 ERROR、零非法動作（9 個角色存活）

### Phase 1（可玩性）✅ 完成
- [x] `action_decision`：softmax 效用 AI，NPC 動作多樣化（Respire/Retreat/Plant 等）— `src/local_ai/decision.py`
- [x] `relation_delta`：互動類型公式引擎 + 好感度偏移 — `src/local_ai/relations.py`
- [x] `long_term_objective`：情境感知模板生成器（宗門/戰爭/靈石條件分支）— `src/local_ai/goals.py`
- [x] 實機驗證：103→108 年 17 月模擬無崩潰，10 個角色存活，動作多樣化

### Phase 2（有趣性）✅ 完成
- [x] `story_teller / interaction_feedback`：詞庫組合文字有變化性 — `src/local_ai/narrative.py`
- [x] `nickname`：外號有成就感（前綴+主題+後綴池，10 runs 皆唯一）— `src/local_ai/epithets.py`
- [x] `backstory`：背景故事多樣（起源/天賦/早期/現狀/抱負五段模板）— `src/local_ai/narrative.py`

### Phase 3（組織智能）✅ 完成
- [x] `sect_decider`：決策樹（外交/招募/驅逐/獎勵/扶持五維度）— `src/local_ai/sect_ai.py`
- [x] `sect_thinker`：宗門年度思考文字模板（30-100 字，境界/財力/戰局感知）— `src/local_ai/sect_ai.py`

### Phase 4（完整等價）
- [ ] 所有 16 個任務完整實作
- [ ] 基準測試：100 月模擬無崩潰
- [ ] 與原版行為對比測試

---

## 專案進度

- [x] 衍生目標定義
- [x] 設計文件 (`docs/design_overview.md`)
- [x] Phase 0：全任務 stub + shim 部署（待實機驗證）
- [x] Phase 1：核心 AI（action_decision Utility AI、relation_delta 公式、long_term_objective 模板）
- [x] Phase 2：敘事系統（詞庫、模板）
- [x] Phase 3：宗門 AI
- [ ] Phase 4：完整等價測試
