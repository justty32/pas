# Unciv AI 核心算法 Pseudo-code (C++ 重構參考)

本文件基於 Unciv 原始碼 (`UnitAutomation.kt`, `BattleHelper.kt`, `NextTurnAutomation.kt`, `ConstructionAutomation.kt` 等) 提取並整理了 AI 核心行為的 Pseudo-code，旨在為 C++ 重構提供演算法層面的精確指導。

---

## 一、 AI 每回合主控引擎 (Main Turn Engine)
**對應原始碼：** `NextTurnAutomation.kt -> automateCivMoves()`

```cpp
void NextTurnAutomation::automateCivMoves(Civilization& civ) {
    if (civ.isBarbarian()) {
        BarbarianAutomation(civ).automate();
        return;
    }

    // 1. 響應與外交事件
    respondToPopupAlerts(civ);
    TradeAutomation::respondToTradeRequests(civ);

    if (civ.isMajorCiv()) {
        // 主動外交與戰略決策
        DiplomacyAutomation::declareWar(civ);
        DiplomacyAutomation::offerPeaceTreaty(civ);
        ReligionAutomation::spendFaithOnReligion(civ);
        adoptPolicy(civ);
    }

    // 2. 科技選擇
    chooseTechToResearch(civ);

    // 3. 戰鬥預備：城市砲擊
    automateCityBombardment(civ);

    // 4. 單位戰術與移動 (最耗效能)
    automateUnits(civ);

    // 5. 城市建設與生產
    automateCities(civ);

    // 6. 擴張決策 (僅在快樂度與軍隊數量允許時)
    trainSettler(civ);
}
```

---

## 二、 單位自動化決策樹 (Unit Automation)
**對應原始碼：** `UnitAutomation.kt -> automateUnitMoves()`

這是一個嚴格的條件短路 (Short-circuit) 行為樹。一旦一個函數回傳 `true`，單位該回合的自動化就會結束。

```cpp
void UnitAutomation::automateUnitMoves(MapUnit& unit) {
    // 0. 生存與平民優先
    if (unit.getDamageFromTerrain() > 0 && tryHealUnit(unit)) return;
    if (unit.isCivilian()) {
        CivilianUnitAutomation::automateCivilianUnit(unit);
        return;
    }

    // 1. 空軍與特殊單位
    if (unit.isNuclearWeapon()) return AirUnitAutomation::automateNukes(unit);
    if (unit.baseUnit.isAirUnit()) return AirUnitAutomation::automate(unit);

    // 2. 護航與遺跡
    if (tryAccompanySettlerOrGreatPerson(unit)) return;
    if (tryGoToRuin(unit)) return;

    // 3. 戰鬥狀態下的生存抉擇
    if (unit.health < 50 && (tryRetreat(unit) || tryHealUnit(unit))) return;
    if (unit.health < 100 && canUnitHealInTurnsOnCurrentTile(unit, 2)) return; // 若安全且2回合可滿血，原地駐紮

    // 4. 戰術攻擊
    if (BattleHelper::tryDisembarkUnitToAttackPosition(unit)) return; // 登陸準備
    if (tryAttacking(unit)) return; // 嘗試攻擊範圍內最有價值目標 (詳見第三節)

    // 5. 戰略調度
    if (HeadTowardsEnemyCityAutomation::tryHeadTowardsEnemyCity(unit)) return;
    if (tryHeadTowardsEncampment(unit)) return; // 清剿蠻族營地
    if (tryGarrisoningLandUnit(unit)) return;   // 回城防守

    // 6. 戰前預備與探索
    if (unit.health < 80 && tryHealUnit(unit)) return;
    if (tryAdvanceTowardsCloseEnemy(unit)) return; // 向最近的敵人推進
    if (tryPrepare(unit)) return; // 向可能開戰的邊界城市集結
    if (tryExplore(unit)) return; // 探索未知區域
    if (tryFogBust(unit)) return; // 站崗驅散戰爭迷霧 (防止蠻族生成)
}
```

---

## 三、 戰術目標評分系統 (Target Selection)
**對應原始碼：** `BattleHelper.kt -> chooseAttackTarget()`

當一個單位決定攻擊時，它會對攻擊範圍內的所有敵軍/城市進行評分，選擇 `attackValue` 最高的目標。

```cpp
int BattleHelper::getCityAttackValue(MapUnit& attacker, City& city) {
    bool canCapture = attacker.isMelee() && !attacker.hasUnique("CannotCaptureCities");
    
    // 如果城市只有 1 滴血且可以佔領，無限優先級
    if (city.health == 1 && canCapture) return 10000;
    
    // 如果攻擊力足夠一擊必殺
    if (canCapture && city.health <= calculateDamageToDefender(attacker, city)) return 10000;

    // 評估風險 (近戰)
    if (attacker.isMelee()) {
        int expectedDamage = calculateDamageToAttacker(attacker, city);
        // 如果攻擊後自己會死
        if (attacker.health - expectedDamage * 2 <= 0) {
            int friendlyUnitsAround = countFriendlyUnitsAroundCity(city, 3);
            // 如果友軍不夠多 (<5)，則退縮不攻擊城市
            if (friendlyUnitsAround < 5) return 0; 
        }
    }

    int attackValue = 100;
    if (attacker.isSiegeUnit()) attackValue += 100; // 攻城武器專注打城
    else if (attacker.isRanged()) attackValue += 10;
    
    // 城市血量越低，分數越高 (最高 +20，最低 -20)
    attackValue -= (city.health - 60) / 2;

    // 戰場態勢影響：敵軍單位越多，越不該打城 (先清兵)
    for (Tile t : city.getTilesInDistance(2)) {
        if (t.hasEnemyUnit()) attackValue -= 5;
    }
    return attackValue;
}

int BattleHelper::getUnitAttackValue(MapUnit& attacker, AttackableTile& enemyTile) {
    MapUnit* enemyUnit = enemyTile.militaryUnit;
    if (enemyUnit != nullptr) {
        // 核心公式：補刀殘血優先 + 傷害期望值
        return 200 - enemyUnit->health + calculateDamageToDefender(attacker, *enemyUnit);
    } 
    
    CivilianUnit* civilian = enemyTile.civilianUnit;
    if (civilian != nullptr) {
        int value = 50;
        if (attacker.isMelee() || attacker.canReachThisTurn(enemyTile)) {
            if (civilian.isGreatPerson()) value += 150;
            if (civilian.isSettler()) value += 60;
            return value;
        } else {
            // 遠程單位不應該射擊可以被捕獲的平民，會留給近戰單位去抓
            return 10; 
        }
    }
    return INT_MIN;
}
```

---

## 四、 戰鬥損害數學模型 (Combat Damage Math)
**對應原始碼：** `BattleDamage.kt`

Unciv 的傷害公式採用指數曲線，這保證了戰鬥力差距帶來的絕對優勢。

```cpp
float BattleDamage::calculateDamage(float attackerStrength, float defenderStrength) {
    // 1. 強度比值差
    // 若攻擊方戰鬥力為 12，防守方為 10
    // difference = 12 - 10 = 2
    float difference = attackerStrength - defenderStrength;
    
    // 2. 指數運算 (e = 2.71828)
    // 基礎傷害為 30，每 25 點戰鬥力差距會使傷害乘以 e (約 2.71 倍)
    // 若 difference 為正，傷害放大；若為負，傷害縮小
    float e = 2.7182818f;
    float expectedDamage = 30.0f * pow(e, difference / 25.0f);
    
    // 3. 加上隨機數擾動 (±20%)
    // float finalDamage = expectedDamage * (0.8f + Random::nextFloat(0.4f));
    return expectedDamage;
}
```

---

## 五、 城市生產決策矩陣 (City Construction)
**對應原始碼：** `ConstructionAutomation.kt`

AI 決定城市要建造什麼時，是透過「轉換產出為分數 (Gold Value)」來比較的。

```cpp
void ConstructionAutomation::chooseNextConstruction() {
    ArrayList<ConstructionChoice> choices;
    
    // 1. 緊急狀態處理
    if (city.health < city.getMaxHealth() || civ.isMilitaryWeak()) {
        // 尋找能建造的最強防禦單位或城防建築 (如城牆)
        Building* wall = getBestDefenseBuilding();
        if (wall) return city.setCurrentConstruction(wall);
        return city.setCurrentConstruction(getBestMilitaryUnit());
    }

    // 2. 評估所有可用建築 (轉化為價值分數)
    for (Building b : availableBuildings) {
        float score = 0.0f;
        // 估算建造後能帶來的每回合收益增長
        Stats yieldIncrease = estimateYieldIncrease(b);
        
        // 將不同資源轉化為統一的分數 (以領袖性格加權)
        // 例如：好戰領袖會給 Production(錘子) 較高權重
        score += yieldIncrease.gold * personality.value(Commerce);
        score += yieldIncrease.production * personality.value(Production);
        score += yieldIncrease.science * personality.value(Science);
        
        // 考慮建築成本 (越貴分數越低)
        float costEffectiveness = score / b.cost;
        choices.add({b, costEffectiveness});
    }

    // 3. 評估單位需求
    if (civ.needsMoreMilitary()) {
        float militaryScore = evaluateMilitaryNeed();
        choices.add({getBestMilitaryUnit(), militaryScore});
    }
    
    if (civ.needsWorkers()) {
        choices.add({WorkerUnit, 15.0f}); // 固定高優先級補齊工人
    }

    // 4. 加權隨機選擇
    // 不一定總是選最高分，而是依照分數比例隨機 (Random Weighted)，增加行為多樣性
    Construction finalChoice = selectRandomWeighted(choices);
    city.setCurrentConstruction(finalChoice);
}
```
