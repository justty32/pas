# 09 - 遊戲內容子系統詳解

## 9.1 概述

`OpenNefia.Content` 包含所有 Elona 遊戲特定的邏輯，建立在 `OpenNefia.Core` 的引擎基礎上。這裡詳細說明每個子系統的設計。

## 9.2 Charas — 角色系統

### CharaComponent — 角色組件

```csharp
[RegisterComponent]
public class CharaComponent : Component
{
    public override string Name => "Chara";
    
    [DataField] public string Alias { get; set; } = string.Empty;
    
    // 種族（不直接設定，使用 CharaSystem 的方法）
    [DataField(required: true)]
    public PrototypeId<RacePrototype> Race { get; set; } = default!;
    
    // 職業（不直接設定，使用 CharaSystem 的方法）
    [DataField(required: true)]
    public PrototypeId<ClassPrototype> Class { get; set; } = default!;
    
    [DataField] public Gender Gender { get; set; } = Gender.Unknown;
    
    // 存活狀態（設定此屬性會同步更新 MetaDataComponent.Liveness）
    public CharaLivenessState Liveness
    {
        get => _liveness;
        set
        {
            _liveness = value;
            _metaData!.Liveness = GetGeneralLivenessState(value);
        }
    }
}
```

### 存活狀態對映

```csharp
public enum CharaLivenessState
{
    Alive,         → EntityGameLiveness.Alive        // 正常存活
    PetDead,       → EntityGameLiveness.Hidden        // 寵物陣亡（隱藏但不刪除）
    VillagerDead,  → EntityGameLiveness.Hidden        // 村民陣亡（會復活）
    Dead,          → EntityGameLiveness.DeadAndBuried // 永久死亡
}
```

### RacePrototype — 種族原型

```csharp
[Prototype("race")]
public class RacePrototype : IPrototype
{
    public string ID { get; private set; } = default!;
    
    // 種族基礎屬性值
    public Dictionary<PrototypeId<SkillPrototype>, int> BaseStats { get; private set; } = new();
    
    // 種族初始技能
    public List<PrototypeId<SkillPrototype>> BaseSkills { get; private set; } = new();
    
    // 種族特性（如夜視、抗火等）
    public List<PrototypeId<SkillPrototype>> Resistances { get; private set; } = new();
}
```

### ClassPrototype — 職業原型

```csharp
[Prototype("class")]
public class ClassPrototype : IPrototype
{
    public string ID { get; private set; } = default!;
    
    // 職業初始技能
    public Dictionary<PrototypeId<SkillPrototype>, int> BaseSkills { get; private set; } = new();
}
```

## 9.3 Skills — 技能與屬性系統

### SkillsComponent

技能和屬性在 OpenNefia 中**共用同一套系統**（都由 SkillPrototype 定義）：

```csharp
[RegisterComponent]
public class SkillsComponent : Component
{
    public override string Name => "Skills";
    
    // 生命值
    [DataField] public int HP { get; set; }
    [DataField] public int MaxHP { get; set; }
    
    // 魔力值
    [DataField] public int MP { get; set; }
    [DataField] public int MaxMP { get; set; }
    
    // 體力
    [DataField] public int Stamina { get; set; }
    [DataField] public int MaxStamina { get; set; }
    
    // 防禦相關（Stat<int> 帶有基礎值和增益值）
    [DataField] public Stat<int> DV { get; set; } = new(0);    // 迴避值
    [DataField] public Stat<int> PV { get; set; } = new(0);    // 防禦值
    [DataField] public Stat<int> HitBonus { get; set; } = new(0);     // 命中加成
    [DataField] public Stat<int> DamageBonus { get; set; } = new(0);  // 傷害加成
    
    // 技能字典（SkillPrototype ID → 等級和潛力）
    [DataField]
    public Dictionary<PrototypeId<SkillPrototype>, LevelAndPotential> Skills { get; } = new();
    
    // 技能點數
    [DataField] public int BonusPoints { get; set; } = 0;
    [DataField] public int TotalBonusPointsEarned { get; set; } = 0;
}
```

### LevelAndPotential

```csharp
public class LevelAndPotential
{
    public int Level { get; set; }        // 當前等級
    public int Potential { get; set; }    // 成長潛力（%，越高則升級越快）
    public int Experience { get; set; }   // 當前累積經驗
}
```

### SkillPrototype

技能和屬性都是 SkillPrototype：

```yaml
# 力量屬性
- type: skill
  id: Elona.AttrStrength
  name: Strength
  isAttribute: true      # 這是屬性，不是技能

# 近戰技能
- type: skill
  id: Elona.MartialArts
  name: Martial Arts
  isAttribute: false     # 這是技能
```

## 9.4 Equipment — 裝備系統

### EquipmentComponent

```csharp
[RegisterComponent]
public class EquipmentComponent : Component
{
    public override string Name => "Equipment";
    
    // 當前裝備（裝備槽 → 裝備實體）
    [DataField]
    public Dictionary<PrototypeId<EquipSlotPrototype>, EntityUid> EquippedItems { get; } = new();
}
```

### EquipSlotPrototype — 裝備槽原型

```yaml
- type: equipSlot
  id: Elona.MainHand
  name: Main Hand

- type: equipSlot
  id: Elona.OffHand
  name: Off Hand

- type: equipSlot
  id: Elona.Armor
  name: Armor

- type: equipSlot
  id: Elona.Head
  name: Head
```

## 9.5 World — 世界時間系統

```csharp
// 遊戲日期時間
public class GameDateTime
{
    public int Year { get; set; }
    public int Month { get; set; }       // 1-12
    public int Day { get; set; }         // 1-30（Elona 每月 30 天）
    public int Hour { get; set; }        // 0-23
    public int Minute { get; set; }      // 0-59
}
```

世界時間系統在每個回合後推進時間，影響：
- 店家貨物刷新
- NPC 的行為（睡眠）
- 月亮週期
- 季節效果

## 9.6 Factions — 陣營系統

```csharp
// 角色對其他角色的態度
public enum Relation
{
    Hate = -3,      // 敵對（會主動攻擊）
    Enemy = -2,     // 仇敵
    Neutral = 0,    // 中立
    Ally = 3,       // 盟友（保護）
}
```

```csharp
[RegisterComponent]
public class FactionComponent : Component
{
    public override string Name => "Faction";
    
    // 此角色的陣營 ID
    [DataField] public PrototypeId<FactionPrototype>? FactionId { get; set; }
    
    // 對玩家的個別態度（覆蓋陣營態度）
    [DataField] public Relation? TargetRelation { get; set; }
}
```

## 9.7 StatusEffects — 狀態異常系統

```csharp
[RegisterComponent]
public class StatusEffectsComponent : Component
{
    public override string Name => "StatusEffects";
    
    // 當前狀態異常（ID → 剩餘持續時間）
    [DataField]
    public Dictionary<PrototypeId<StatusEffectPrototype>, StatusEffectState> Effects { get; } = new();
}

public class StatusEffectState
{
    public int Duration { get; set; }    // 剩餘持續時間（回合數）
    public int Power { get; set; }       // 效果強度
}
```

常見狀態異常：
- `Elona.Blind` — 失明
- `Elona.Confused` — 混亂
- `Elona.Poisoned` — 中毒
- `Elona.Blessed` — 祝福
- `Elona.Cursed` — 詛咒
- `Elona.Paralyzed` — 麻痺
- `Elona.Sleep` — 睡眠

## 9.8 VanillaAI — NPC AI 系統

詳細見 [10_ai_turn_order.md](10_ai_turn_order.md)。

VanillaAI 系統的主要設計思想是**可插拔的 AI**：

```csharp
// 移除 VanillaAIComponent，換上自訂 AI 處理 NPCTurnStartedEvent
[RegisterComponent]
public class VanillaAIComponent : Component
{
    public override string Name => "VanillaAI";
    
    [DataField] public EntityUid? CurrentTarget { get; set; }
    [DataField] public int Aggro { get; set; } = 0;          // 仇恨值
    [DataField] public int MoveFrequency { get; set; } = 100; // 移動頻率（%）
}
```

## 9.9 EntityGen — 程序化實體生成

負責在地圖中隨機生成實體（NPC、物品等）：

```csharp
public interface IEntityGen
{
    // 在指定位置生成實體
    EntityUid? GenEntity(
        PrototypeId<EntityPrototype> id,
        EntityCoordinates coords,
        int? level = null
    );
    
    // 在地圖上隨機位置生成
    EntityUid? GenEntityAt(
        PrototypeId<EntityPrototype> id,
        IMap map,
        int? level = null
    );
    
    // 生成多個實體
    void GenEntities(
        IMap map,
        int count,
        Func<PrototypeId<EntityPrototype>> protoSelector
    );
}
```

## 9.10 Parties — 隊伍系統

```csharp
[RegisterComponent]
public class PartyComponent : Component
{
    public override string Name => "Party";
    
    // 隊伍領袖（若為 null 則此實體是獨立的）
    [DataField] public EntityUid? Leader { get; set; }
    
    // 隊伍成員（只在領袖身上有意義）
    [DataField] public List<EntityUid> Members { get; } = new();
}
```

```csharp
public interface IPartySystem
{
    bool IsInParty(EntityUid uid, EntityUid leader);
    bool IsPartyLeader(EntityUid uid);
    EntityUid? GetLeader(EntityUid member);
    IEnumerable<EntityUid> GetMembers(EntityUid leader);
    
    void AddMember(EntityUid leader, EntityUid newMember);
    void RemoveMember(EntityUid leader, EntityUid member);
}
```

## 9.11 Levels — 等級系統

```csharp
[RegisterComponent]
public class LevelComponent : Component
{
    public override string Name => "Level";
    
    [DataField] public int Level { get; set; } = 1;
    [DataField] public int Experience { get; set; } = 0;
    [DataField] public int ExperienceToNext { get; set; } = 0;
}
```

## 9.12 DisplayName — 顯示名稱系統

```csharp
public interface IDisplayNameSystem
{
    // 取得實體的顯示名稱（考慮本地化、性別、複數等）
    string GetDisplayName(EntityUid uid);
    
    // 取得帶冠詞的名稱（如 "a sword"、"the warrior"）
    string GetDisplayNameWithArticle(EntityUid uid, bool definite = false);
}
```

```csharp
[RegisterComponent]
public class MetaDataComponent : Component
{
    // 原型中定義的基本名稱
    public string EntityName { get; set; } = string.Empty;
    
    // 自訂名稱（覆蓋原型名稱）
    public string? CustomName { get; set; }
}
```

## 9.13 MapVisibility — 視野 / FOV 系統

```csharp
public interface IVisibilitySystem
{
    // 判斷一個位置是否可見
    bool HasLineOfSight(EntityUid viewer, MapCoordinates target);
    
    // 更新視野（計算 FOV）
    void RefreshVisibility(EntityUid viewer);
}
```

FOV 算法使用 Elona 原版的視野計算方式（基於光線投射的變體）。

## 9.14 TurnOrder — 回合順序系統

詳見 [10_ai_turn_order.md](10_ai_turn_order.md)。

## 9.15 God — 神明系統

```csharp
[RegisterComponent]
public class GodComponent : Component
{
    public override string Name => "God";
    
    // 信仰的神明
    [DataField] public PrototypeId<EntityPrototype>? CurrentGod { get; set; }
    
    // 對神明的虔誠度
    [DataField] public int Piety { get; set; } = 0;
}
```

## 9.16 Fame、Karma、Sanity — 聲望、業力、精神系統

這些都是角色的全域追蹤值：

```csharp
[RegisterComponent]
public class FameComponent : Component
{
    public override string Name => "Fame";
    [DataField] public int Fame { get; set; } = 0;     // 聲望值
}

[RegisterComponent]
public class KarmaComponent : Component
{
    public override string Name => "Karma";
    [DataField] public int Karma { get; set; } = 0;    // 業力（正 = 善良，負 = 邪惡）
}

[RegisterComponent]
public class SanityComponent : Component
{
    public override string Name => "Sanity";
    [DataField] public int Sanity { get; set; } = 0;   // 精神值
    [DataField] public int MaxSanity { get; set; } = 0;
}
```

## 9.17 Journal — 任務日誌系統

```csharp
[RegisterComponent]
public class JournalComponent : Component
{
    public override string Name => "Journal";
    
    // 任務列表
    [DataField] public List<QuestData> Quests { get; } = new();
}

public class QuestData
{
    public PrototypeId<EntityPrototype> QuestPrototypeId { get; set; }
    public QuestState State { get; set; }
    public Dictionary<string, object> Data { get; } = new();
}

public enum QuestState
{
    Offered,
    InProgress,
    Completed,
    Failed,
}
```

## 9.18 Shopkeeper — 商店系統

```csharp
[RegisterComponent]
public class ShopkeeperComponent : Component
{
    public override string Name => "Shopkeeper";
    
    // 商品列表
    [DataField] public List<EntityUid> Inventory { get; } = new();
    
    // 商店類型（影響商品種類）
    [DataField] public PrototypeId<ShopInventoryPrototype>? ShopInventory { get; set; }
    
    // 最後補貨時間
    [DataField] public GameDateTime? LastRestockTime { get; set; }
}
```

## 9.19 Cargo — 重量系統

```csharp
[RegisterComponent]
public class CargoComponent : Component
{
    public override string Name => "Cargo";
    
    [DataField] public int Weight { get; set; } = 0;      // 此物品重量
    [DataField] public int CarryWeight { get; set; } = 0; // 此角色的攜帶重量上限
}
```

## 9.20 Qualities — 品質系統

```csharp
public enum Quality
{
    Bad,        // 劣質
    Normal,     // 普通
    Good,       // 良好
    Great,      // 優秀
    God,        // 神器
    Unique,     // 特殊（唯一物品）
}

[RegisterComponent]
public class QualityComponent : Component
{
    public override string Name => "Quality";
    [DataField] public Quality Quality { get; set; } = Quality.Normal;
}
```
