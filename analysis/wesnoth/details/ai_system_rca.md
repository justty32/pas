# Wesnoth 技術專題 - AI 系統與 RCA 決策框架剖析

## 1. RCA (Recruitment and Combat AI) 框架
Wesnoth 的 AI 核心是一個基於「候選行動 (Candidate Action, CA)」的權重決策系統。

### 核心組件: `candidate_action`
- **evaluate()**: 評估當前局勢並返回一個得分 (double)。
  - 得分越高，優先級越高。
  - `BAD_SCORE` (0) 表示不應執行。
- **execute()**: 執行該行動（如移動單位、發起攻擊、招募士兵）。
- **特點**: 
  - **解耦**: 每個行動（進攻、守衛、醫療、招募）都是獨立的類別。
  - **動態性**: 隨著戰場情境變化，行動的得分會動態浮動。

## 2. AI 決策流程 (Loop)
RCA 階段會運行一個循環：
1. **評估階段**: 調用所有已註冊 CA 的 `evaluate()`。
2. **選擇階段**: 挑選得分最高的 CA。
3. **執行階段**: 調用最高分 CA 的 `execute()`。
4. **重複**: 執行完畢後回到步驟 1，直到沒有得分大於 0 的 CA 或執行次數達到上限。

## 3. 關鍵行動類型
- **招募行動 (Recruitment CA)**: 根據當前金錢、領袖位置與對手兵種決定招募哪種單位。
- **戰鬥行動 (Combat CA)**: 評估攻擊的勝算、反擊傷害與戰略價值。
- **目標導向移動 (Move to Targets CA)**: 讓單位向特定目標（如村莊或敵人領袖）推進。

## 4. 擴展性與 Lua 整合
- **工廠模式**: 使用 `candidate_action_factory` 動態創建 CA 對象。
- **Lua AI**: 允許開發者使用 Lua 編寫 `evaluate` 與 `execute` 邏輯，無需重新編譯 C++ 即可自定義 AI 行為。

## 5. 核心類別參考
- `src/ai/composite/rca.hpp`: 定義了 `candidate_action` 基礎類別。
- `src/ai/default/stage_rca.cpp`: RCA 決策循環的主控邏輯。
- `src/ai/default/recruitment.cpp`: 複雜的招募邏輯實作。

---
*最後更新: 2026-05-17*
