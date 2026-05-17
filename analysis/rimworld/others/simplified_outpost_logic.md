# 進階哨站：簡化產出與全維度收益設計 (Simplified & Wild Design)

秉持「RimWorld 就是要亂玩」的核心精神，我們將哨站系統的監測邏輯簡化為最直觀的「全地圖狀態變動」。不設防作弊，玩家想怎麼搬資源、怎麼利用機制，都將成為哨站實力的一部分。

## 1. 簡化版產出監測：全地圖資產快照 (Inventory Delta)

不再指定特定儲存區，系統會直接觀察整張地圖的物資消長。

*   **實作機制**:
    *   **期初快照 (T0 Snapshot)**: 當玩家啟動採樣時，遍歷 `map.resourceCounter.AllCountedAmounts`，紀錄所有可用資源的數量。
    *   **期末快照 (T1 Snapshot)**: 採樣結束時，再次遍歷。
    *   **計算產出**: `(T1 - T0) / 採樣天數 = 日均產出`。
*   **玩家的自由度**:
    *   玩家可以從外面搬資源進來「灌水」產能。
    *   玩家可以透過瘋狂狩獵、砍伐來極大化短期產量。
    *   *註：這反而增加了一種「準備封存期」的策略玩法，看誰能在這段時間內壓榨出最大效能。*

## 2. 人物與技能增長 (Pawn & Skill Growth)

封存後的哨站將根據採樣期的人員表現，提供長期的「教育」收益。

*   **技能同步**:
    *   紀錄每個小人在採樣期間各技能獲得的 XP 總量。
    *   封存後，這些小人的技能會以該速率的 50%~100% 持續增長（反映「哨站日常工作」的鍛鍊）。
*   **新成員產出 (Personel Recruitment)**:
    *   若採樣期間地圖上有新加入的殖民者、俘虜（且被招募），哨站未來會定期產出「新兵」或「奴隸」送到主基地。

## 3. 勢力關係與外交 (Diplomacy)

*   **外交回饋**:
    *   如果玩家在採樣期間頻繁與某個派系進行貿易或釋放囚犯，哨站會紀錄這個「外交趨勢」。
    *   封存後，該哨站會定期自動增加與該派系的友好度（反映「邊境貿易站」的長期經營）。

## 4. 實作架構修正 (C# Logic)

```csharp
public class ProductivitySnapshot {
    public Dictionary<ThingDef, int> itemDeltas;
    public Dictionary<Pawn, Dictionary<SkillDef, float>> skillXpGains;
    public Dictionary<Faction, float> factionRelationGains;
    
    public void FinalizeAndApply(OutpostWorldObject outpost) {
        // 將所有增量數據除以天數，存入哨站的持續收益引擎
        outpost.dailyOutput = this.itemDeltas.ToDaily();
        outpost.trainingRate = this.skillXpGains.ToDaily();
        outpost.diplomacyBonus = this.factionRelationGains.ToDaily();
    }
}
```

## 5. 為什麼這樣更好玩？

1.  **容錯率高**: 不管玩家裝了什麼儲存 Mod (Deep Storage, Racks)，只要原版的 `ResourceCounter` 能掃描到，系統就認帳。
2.  **鼓勵「突擊式建設」**: 玩家可以集中全勢力資源在 10 天內把分基地衝到極限產能，然後「封存」成一個超級糧倉，這種爆發式的操作非常有 RimWorld 的特色。
3.  **動態故事**: 哨站不再是個死板的工廠，它是一個會「成長」的邊境社群，人員在裡面變強，關係在裡面變好。

---
*文件路徑: analysis/rimworld/others/simplified_outpost_logic.md*
