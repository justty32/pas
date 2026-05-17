# Unciv 核心演算法：原始碼級 Pseudo-code 參考手冊

本文件將 Unciv 的 Kotlin 核心邏輯轉化為 C++ 風格的虛擬碼，旨在為高性能重構提供嚴謹的邏輯參考。

---

## 1. 基礎層：定點數運算 (FixedPoint Math)
**位置**: `com.unciv.logic.map.PathingMapCache.kt`

```cpp
// 採用 Base 30 定點數系統，確保跨平台一致性
struct FixedPointMovement {
    static const int BASE = 30;
    int32_t bits;

    // 構造函數與轉換
    explicit FixedPointMovement(int32_t b) : bits(b) {}
    static FixedPointMovement fromFloat(float f) {
        // HALF_UP 四捨五入實作
        int32_t plusOneBit = (int32_t)(f * (BASE * 2));
        return FixedPointMovement((plusOneBit >> 1) + (plusOneBit & 1));
    }

    // 核心運算子
    FixedPointMovement operator+(const FixedPointMovement& other) const { return FixedPointMovement(bits + other.bits); }
    FixedPointMovement operator*(float multiplier) const { return fromFloat(bits * multiplier); }
    
    // 關鍵：定點數乘法需除回基數
    FixedPointMovement operator*(const FixedPointMovement& other) const {
        return FixedPointMovement((int32_t)((int64_t)bits * other.bits / BASE));
    }

    float toFloat() const { return (float)bits / BASE; }
};
```

---

## 2. 戰略層：AI 每回合執行心跳 (The Heartbeat)
**位置**: `com.unciv.logic.automation.civilization.NextTurnAutomation.kt`

```cpp
void NextTurnAutomation::automateCivMoves(Civilization& civ) {
    if (civ.isBarbarian()) return handleBarbarianAI(civ);

    // 1. 外交預處理
    respondToPopupAlerts(civ);
    handleDiplomacy(civ); // 宣戰、求和、友好宣言

    // 2. 資源分配
    adoptPolicy(civ);    // 採「分支完成」優先策略
    chooseTech(civ);     // 採「最便宜/次便宜」權重隨機策略

    // 3. 戰術動作 (高成本計算)
    automateCityBombardment(civ);
    automateUnits(civ);   // 依優先級移動：飛船零件 > 移民 > 殘血遠程 > 滿血近戰 > 將軍

    // 4. 內政建設
    automateCities(civ);  // 評估建設回報率
    trainSettler(civ);    // 根據幸福度與軍力比決定擴張
}
```

---

## 3. 內政層：城市建設價值評級 (Construction Ranking)
**位置**: `com.unciv.logic.automation.city.ConstructionAutomation.kt`

```cpp
float getConstructionScore(City& city, Construction& item) {
    float baseValue = calculateStatsValue(item.getStats());
    
    // 領袖性格修正 (PersonalityValue)
    float personalityMod = city.civ.personality.getModifier(item.category);
    
    // AI 權重修正 (Ruleset Uniques)
    float aiWeight = item.getUniqueWeight("AiChoiceWeight");

    // 剩餘工期懲罰 (Time Efficiency)
    int turnsToBuild = std::max(1, item.getRemainingWork() / city.getProduction());

    // 綜合公式：產出價值 * 性格修正 * AI權重 / 剩餘回合
    return (baseValue * personalityMod * aiWeight) / (float)turnsToBuild;
}

// 地塊分配權重 (Citizen Management)
float rankTile(Tile& tile, City& city) {
    Stats yields = tile.getYields();
    if (city.isStarving()) {
        yields.food *= 8.0f; // 極度飢渴保護
    } else if (city.civ.happiness < 0) {
        yields.happiness *= 2.0f; // 社會動盪修正
    }
    return yields.sumWithGlobalWeights();
}
```

---

## 4. 戰術層：進攻目標評分 (Attack Scoring)
**位置**: `com.unciv.logic.automation.unit.BattleHelper.kt`

```cpp
int calculateAttackValue(Unit& attacker, Target& target) {
    int score = 0;

    if (target.isMilitary()) {
        // 核心：血量越低分越高，預計傷害越高分越高 (補刀邏輯)
        score = 200 - target.health + calculateDamage(attacker, target);
    } else if (target.isCivilian()) {
        score = 50;
        if (target.isGreatPerson()) score += 150; // 捕獲偉人價值極高
        if (target.isSettler()) score += 60;      // 阻止擴張
    }

    // 移動後剩餘行動力加權 (保持靈活性)
    score += (attacker.remainingMovementAfterAttack() * 5);

    // 如果總分 < 30，AI 視為無效攻擊，傾向於等待或撤退
    return score;
}
```

---

## 5. 地理層：地圖生成氣候矩陣 (Climate Matrix)
**位置**: `com.unciv.logic.map.mapgenerator.MapGenerator.kt`

```cpp
struct ClimateParams {
    float temp; // [-1.0 (Polar), 1.0 (Equator)]
    float humid; // [0.0, 1.0]
};

TerrainType determineTerrain(ClimateParams p) {
    // 模擬 Ruleset 中的 TileGenerationConditions
    if (p.temp < -0.5f) return SNOW;
    if (p.temp < -0.2f) {
        return (p.humid > 0.5f) ? TUNDRA : PLAIN;
    }
    if (p.temp > 0.5f && p.humid < 0.2f) return DESERT;
    
    // 植被生成
    if (p.humid > 0.7f && p.temp > 0.3f) return JUNGLE;
    if (p.humid > 0.4f) return FOREST;
    
    return GRASSLAND;
}
```

---

### 🛠️ 重構提示：
1.  **SIMD 優化**: 在 C++ 中，`LongArray` 存儲的 `RouteNode` 可利用 SIMD 指令進行批量路徑估算。
2.  **線程安全**: AI 決策（`chooseNextConstruction`）應與渲染分離。定點數運算確保了在多線程環境下，即便浮點數異常也不會導致邏輯分歧。
3.  **DOD 架構**: 建議將 `Tile` 的數據成員拆分為 SoA (Structure of Arrays)，例如 `std::vector<int32_t> tileStats`，以提升 Cache 命中率。
