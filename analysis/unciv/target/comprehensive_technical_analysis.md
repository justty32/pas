# Unciv 核心機制深度剖析白皮書 (Comprehensive Technical Analysis)

## 1. 地圖生成與公平性 (Map Generation & Fairness)
- **起點選擇 (RegionStartFinder)**: 採用「由內而外」的搜尋策略，優先保證 1-3 環內的資源密度。
- **補償機制 (StartNormalizer)**: 
    - 透過 `Food^2 / 4` 公式計算食物價值，確保「高質量地塊」優先。
    - 產能不足時強行植入丘陵或戰略資源。
    - 清理起點障礙，確保開局可玩性。

## 2. 城市建設 AI (Construction Automation)
- **決策公式**: `Value = (BaseValue * Modifier) / RemainingWork`。
- **動態平衡**: 
    - 戰爭時軍事權重翻倍；發呆移民會觸發護航補償。
    - 工人需求隨城市數量動態調整。
    - 奇觀與勝利零件具有極高權重，受文明性格（Personality）深度影響。

## 3. 戰術戰鬥邏輯 (Tactical Combat)
- **優先級序列**: 生存 > 護航 > 補血/撤退 > 攻擊 > 探索。
- **集火公式**: `AttackValue = 200 - 目標血量 + 預計傷害`。
    - 誘發 AI 優先「補刀」殘血單位。
    - 偉人與移民對 AI 具有極高的「嘲諷值」（+150/60 分）。

## 4. 戰略戰爭動機 (Strategic War Motivation)
- **趁火打劫**: 敵方處於多線作戰時，AI 宣戰動機增加；己方多線作戰時則大幅降低。
- **供給驅動**: 部隊供給赤字會反向刺激 AI 開戰，將「過剩兵力」投入戰場消耗。
- **外交制約**: 科研協定與友好宣言是有效的戰爭緩衝器，受「忠誠度」性格加權。

---
*本報告由 Gemini CLI 透過對 Unciv 4.20.6 原始碼的深度剖析產出，旨在為重構與 AI 優化提供參考。*
