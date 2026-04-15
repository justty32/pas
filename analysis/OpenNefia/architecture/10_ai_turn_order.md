# 10 - NPC AI 與回合順序系統

## 10.1 概述

OpenNefia 使用**回合制系統**，玩家和 NPC 輪流行動。AI 系統採用事件驅動設計，使得 AI 行為可以輕鬆被 Mod 替換。

相關檔案：
- `OpenNefia.Content/VanillaAI/VanillaAISystem.cs` — Vanilla AI 主系統
- `OpenNefia.Content/VanillaAI/VanillaAIComponent.cs` — AI 組件
- `OpenNefia.Content/TurnOrder/TurnOrderSystem.cs` — 回合順序系統

## 10.2 TurnOrder — 回合順序系統

### 回合流程

```
玩家行動
    ↓
PlayerTurnResult → TurnResult.Succeeded（花費一個回合）
    ↓
TurnOrderSystem.EndPlayerTurn()
    ↓
對每個活存的 NPC：
    RaiseLocalEvent(npc, NPCTurnStartedEvent)
    ↓
NPC 的 AI 系統處理事件（如 VanillaAISystem）
    ↓
NPCTurnStartedEvent.Handle(TurnResult)
    ↓
TurnResult → 決定是否花費回合
    ↓
下一個回合開始
```

### TurnResult — 回合結果

```csharp
public enum TurnResult
{
    // 成功執行了一個動作，花費一個回合
    Succeeded,
    
    // 執行失敗，不花費回合（如移動被阻擋）
    Failed,
    
    // 中止（特殊情況）
    Aborted,
}
```

### NPCTurnStartedEvent

```csharp
// 每個 NPC 的回合開始時發送
[EventArgsUsage(EventArgsTargets.ByRef)]
public struct NPCTurnStartedEvent
{
    // 是否已被處理
    public bool Handled { get; private set; }
    
    // 處理結果
    public TurnResult Result { get; private set; }
    
    // AI 系統呼叫此方法標記已處理
    public void Handle(TurnResult result)
    {
        Handled = true;
        Result = result;
    }
}
```

## 10.3 VanillaAISystem — Vanilla AI 實作

VanillaAI 是 Elona 原版的 AI 邏輯重製：

```csharp
public sealed partial class VanillaAISystem : EntitySystem
{
    [Dependency] private readonly IMapRandom _mapRandom = default!;
    [Dependency] private readonly IMapManager _mapManager = default!;
    [Dependency] private readonly MoveableSystem _movement = default!;
    [Dependency] private readonly IFactionSystem _factions = default!;
    [Dependency] private readonly IPartySystem _parties = default!;
    [Dependency] private readonly IGameSessionManager _gameSession = default!;
    [Dependency] private readonly IVisibilitySystem _vision = default!;
    [Dependency] private readonly IRandom _random = default!;
    
    public override void Initialize()
    {
        // 訂閱 NPC 回合開始事件
        SubscribeLocalEvent<VanillaAIComponent, NPCTurnStartedEvent>(
            HandleNPCTurnStarted, 
            nameof(HandleNPCTurnStarted)
        );
        SubscribeAIActions();    // 訂閱 AI 動作事件
    }
}
```

### VanillaAIComponent — AI 組件

```csharp
[RegisterComponent]
public class VanillaAIComponent : Component
{
    public override string Name => "VanillaAI";
    
    // 當前攻擊目標
    [DataField] public EntityUid? CurrentTarget { get; set; }
    
    // 仇恨值（> 0 時主動追擊目標）
    [DataField] public int Aggro { get; set; } = 0;
    
    // 移動頻率（%，100 = 每回合都移動）
    [DataField] public int MoveFrequency { get; set; } = 100;
    
    // 使用技能的頻率
    [DataField] public int SkillUseFrequency { get; set; } = 50;
}
```

## 10.4 Vanilla AI 決策流程

```
HandleNPCTurnStarted(uid, ai, ref args)
    ↓
RunVanillaAI(entity, ai)
    ↓
1. 確認地圖存在
    ↓
2. 若是玩家的盟友 → DecideAllyTarget()（選擇敵對目標）
    ↓
3. 若當前目標不存在 → GetDefaultTarget()
    （通常是最近的敵對實體）
    ↓
4. 若有目標且仇恨值 > 0（或是盟友）→ DoTargetedAction()
    ├─ 嘗試向目標移動 / 攻擊
    ├─ 若在攻擊範圍 → 執行攻擊
    └─ 若不在攻擊範圍 → 移動接近目標
    ↓
5. 若無目標 → 隨機移動（MoveFrequency 控制）
```

```csharp
public TurnResult RunVanillaAI(EntityUid entity, VanillaAIComponent? ai = null, SpatialComponent? spatial = null)
{
    if (!Resolve(entity, ref ai, ref spatial))
        return TurnResult.Failed;
    
    if (!_mapManager.TryGetMap(spatial.MapID, out var map))
        return TurnResult.Failed;
    
    // 盟友選擇目標
    if (IsAlliedWithPlayer(entity))
        DecideAllyTarget(entity, ai, spatial);
    
    // 若目標已死亡，重置目標
    if (!EntityManager.IsAlive(ai.CurrentTarget))
        SetTarget(entity, GetDefaultTarget(entity), aggro: 0, ai);
    
    // TODO: 實作窒息、治療、使用物品等邏輯
    
    var target = ai.CurrentTarget;
    if (EntityManager.IsAlive(target) && (ai.Aggro > 0 || IsAlliedWithPlayer(entity)))
    {
        // 有目標且有仇恨 → 執行定向行動
        return DoTargetedAction(entity, ai, spatial);
    }
    else
    {
        // 無目標 → 隨機遊蕩
        return DoWandering(entity, ai, spatial);
    }
}
```

## 10.5 AI 動作系統（IAIAction）

AI 的具體動作（攻擊、施法等）被拆分為獨立的 AI 動作：

```csharp
public interface IAIAction
{
    // 是否可以執行此動作
    bool CanPerform(EntityUid entity, EntityUid target, VanillaAIComponent ai);
    
    // 執行動作
    TurnResult Perform(EntityUid entity, EntityUid target, VanillaAIComponent ai);
    
    // 動作的優先級（越高越優先）
    int Priority { get; }
}
```

```csharp
// VanillaAISystem.Actions.cs
private void SubscribeAIActions()
{
    // 注冊各種 AI 動作
    SubscribeLocalEvent<VanillaAIComponent, AIActionMeleeAttackEvent>(DoMeleeAttack);
    SubscribeLocalEvent<VanillaAIComponent, AIActionRangedAttackEvent>(DoRangedAttack);
    SubscribeLocalEvent<VanillaAIComponent, AIActionCastSpellEvent>(DoCastSpell);
    // ...
}
```

## 10.6 目標選擇邏輯

```csharp
// 取得預設目標（最近的敵對實體）
private EntityUid? GetDefaultTarget(EntityUid entity)
{
    var relation = _factions.GetRelationToPlayer(entity);
    
    if (relation <= Relation.Enemy)
    {
        // 敵對 NPC → 以玩家為目標
        return _gameSession.Player;
    }
    else if (relation >= Relation.Ally)
    {
        // 盟友 NPC → 以玩家的敵人為目標
        return FindNearestEnemy(entity);
    }
    
    return null;
}

// 盟友選擇目標（攻擊正在攻擊玩家或盟友的敵人）
private void DecideAllyTarget(EntityUid entity, VanillaAIComponent ai, SpatialComponent spatial)
{
    // 若當前目標仍然有效且在視野內，維持目標
    if (EntityManager.IsAlive(ai.CurrentTarget) && IsInSight(entity, ai.CurrentTarget!.Value))
        return;
    
    // 找到離玩家最近的敵人
    var newTarget = FindNearestEnemyOfPlayer(entity, spatial);
    SetTarget(entity, newTarget, aggro: 1, ai);
}
```

## 10.7 移動系統

AI 使用 `MoveableSystem` 進行移動：

```csharp
// 向目標方向移動一格
TurnResult MoveTowardsTarget(EntityUid entity, EntityUid target, VanillaAIComponent ai)
{
    var direction = GetDirectionToTarget(entity, target);
    return _movement.MoveEntity(entity, direction);
}

// 隨機遊蕩
TurnResult DoWandering(EntityUid entity, VanillaAIComponent ai, SpatialComponent spatial)
{
    // 依 MoveFrequency 決定是否移動
    if (_random.NextFloat() * 100 > ai.MoveFrequency)
        return TurnResult.Failed;
    
    // 隨機選擇一個方向
    var direction = _random.Pick(DirectionUtility.CardinalDirections);
    return _movement.MoveEntity(entity, direction);
}
```

## 10.8 AI 替換設計

VanillaAI 的設計允許 Mod 作者完全替換 AI：

```yaml
# 原版帶有 VanillaAI 的 NPC
- type: entity
  id: Elona.Goblin
  components:
    - type: VanillaAI    # 使用 VanillaAI

# 自訂 AI 的 NPC（移除 VanillaAI，添加自訂組件）
- type: entity
  id: MyMod.SmartGoblin
  parent: Elona.Goblin
  components:
    - type: VanillaAI
      enabled: false     # 停用 VanillaAI
    - type: MyCustomAI   # 使用自訂 AI
```

自訂 AI 只需處理 `NPCTurnStartedEvent`：

```csharp
public sealed class MyCustomAISystem : EntitySystem
{
    public override void Initialize()
    {
        SubscribeLocalEvent<MyCustomAIComponent, NPCTurnStartedEvent>(HandleTurn);
    }
    
    private void HandleTurn(EntityUid uid, MyCustomAIComponent ai, ref NPCTurnStartedEvent args)
    {
        if (args.Handled) return;
        
        // 自訂 AI 邏輯
        var result = DoCustomAI(uid, ai);
        args.Handle(result);
    }
}
```

## 10.9 視野判斷

AI 使用 `IVisibilitySystem` 判斷是否能「看到」目標：

```csharp
public interface IVisibilitySystem
{
    // 判斷 from 是否能看到 to
    bool HasLineOfSight(EntityUid from, EntityUid to);
    
    // 取得視野範圍
    int GetSightRange(EntityUid entity);
}
```

視野判斷考慮：
- 牆壁阻擋（IsOpaque 磁磚）
- 視野距離（由技能值決定）
- 黑暗條件
- 隱形狀態

## 10.10 GameSessionManager — 遊戲會話管理

```csharp
public interface IGameSessionManager
{
    // 當前玩家實體
    EntityUid Player { get; }
    
    // 設定玩家
    void SetPlayer(EntityUid uid);
    
    // 判斷是否是玩家
    bool IsPlayer(EntityUid uid);
}
```
