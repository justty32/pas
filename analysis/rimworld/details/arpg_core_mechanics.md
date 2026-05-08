# RimWorld ARPG 化轉換：核心機制深度實作指南

本文件旨在深化 `arpg_conversion_design.md` 中的概念，為開發者提供具體的技術路徑與底層 C# 實作思路。

## 1. 單一角色控制與攝像機 (Single-Character Control)

ARPG 的核心感在於「我就是這個角色」。這需要打破 RimWorld 的 RTS 操作慣例。

### A. WASD 移動實作
RimWorld 預設是點擊移動。要實作 WASD，需要監聽鍵盤輸入並直接驅動 `Pawn_PathFollower`。
*   **技術點**: 監聽 `Unity` 的 `Input.GetKey`。
*   **實作路徑**:
    *   建立一個 `WorldComponent` 或 `MapComponent` 每一幀 (Update) 檢查按鍵。
    *   計算方向向量，並在 Pawn 當前位置的相鄰格中找到目標點。
    *   調用 `pawn.pather.StartPath(targetCell, PathEndMode.OnCell)`。
    *   **優化**: 為了流暢度，應使用 `pawn.Drawer.tweener` 平滑移動。

### B. 攝像機鎖定 (Camera Lock)
*   **Harmony Patch**: 攔截 `CameraDriver.Update`。
*   **邏輯**: 若處於 ARPG 模式，強制將 `CameraDriver.instance.CurrentPos` 鎖定在 `selectedPawn.DrawPos`。
*   **縮放限制**: 調整 `CameraDriver` 的縮放參數，提供更接近地面的視角。

## 2. 動作戰鬥引擎 (Action Combat Engine)

RimWorld 的戰鬥是基於 RNG 與掩體計算的。ARPG 需要更直觀的判定。

### A. 近戰範圍傷害 (Cleave/AOE Melee)
原版近戰是單體攻擊。
*   **實作**: 覆寫 `Verb_MeleeAttack.TryCastShot`。
*   **邏輯**: 
    1. 獲取攻擊者面向的扇形區域 (Sector)。
    2. 使用 `GenRadial.RadialCellsAround` 或自定義幾何判定找出區域內所有 `Pawn`。
    3. 對每個目標執行 `DamageWorker.Apply`。
    4. 播放揮砍特效 (Effecter)。

### B. 彈幕與指向性技能 (Projectiles)
*   **自定義 Projectile**: 繼承 `Projectile` 類別。
*   **特性**:
    *   **穿透 (Piercing)**: 在 `Impact` 時不銷毀，而是減少穿透次數並繼續移動。
    *   **爆炸 (Explosive)**: 碰撞時觸發 `GenExplosion`。
    *   **跟蹤 (Homing)**: 在 `Tick` 中每幀微調前進向量指向目標。

## 3. 技能系統架構 (Skill & Resource System)

ARPG 需要一個比原版 `Verb` 系統更靈活的技能框架。

### A. 能量槽 (Resource Bar)
*   **數據儲存**: 使用 `ThingComp` 掛載在 Pawn 身上，儲存 `CurrentMana`, `MaxMana`。
*   **自動回復**: 在 `CompTick` 中根據屬性（智力、裝備加成）恢復能量。

### B. 技能執行生命週期
建立一個 `SkillDef` (繼承自 `Def`) 與 `SkillWorker` 類別：
1.  **CheckRequirement**: 能量是否足夠？是否冷卻中？
2.  **CastTime**: 啟動 Pawn 的「施法動作」，可被擊退或眩暈中斷。
3.  **OnExecute**: 執行具體邏輯（生成彈幕、加 Buff）。
4.  **StartCooldown**: 進入冷卻計時。

## 4. 戰利品與屬性隨機化 (Loot & Affixes)

實作類似 Diablo 的隨機裝備系統。

### A. 隨機屬性組件 (CompRandomAffix)
*   **實作**: 為所有武器與護甲掛載一個 `ThingComp`。
*   **初始化**: 在 `PostPostMake` 時根據物品等級 (Item Level) 隨機抽取屬性池（如：+10% 攻速, +5 火焰傷害）。
*   **StatPart**: 透過 `StatPart` 接口將這些隨機屬性注入到 Pawn 的總體屬性計算中。

### B. 掉落物視覺強化
*   **光柱效果**: 根據物品品質（普通、稀有、傳奇）在掉落物位置生成不同顏色的常駐粒子效果 (`Mote`)。

## 5. 性能優化建議 (Optimization)

*   **物件池 (Object Pooling)**: ARPG 會有大量彈幕，務必對 `Mote` 與 `Projectile` 使用物件池。
*   **空間分割**: 在進行 AOE 判定時，利用 RimWorld 內建的 `PawnGrid` 快速篩選目標，避免遍歷全圖。

---
*文件路徑: analysis/rimworld/details/arpg_core_mechanics.md*
