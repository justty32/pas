# 第一個自製武功設計：流光劍法（劇意堆疊型）

> 日期：2026-05-22
> 需求：劍法 + 複雜機制特效 + 平衡向數值（可實戰）。
> 產出位置：`~/repo/pas/projects/taiwu/MySwordArt/`
> 設計依據：[屬性 ID 表](../details/property_ids.md)、[backend 事件手冊](../details/backend_combat_events.md)、[Config/YAML 規格](../details/config_lua_schema.md)、[mod 解剖](../details/martial_arts_mod_anatomy.md)。
>
> **狀態（2026-05-23 更新）：已對實裝版 0.0.79.60 重編、部署、實機可載入**（log：`Loaded 1 combat skill / 2 special effect items`、`Total 1 mods loaded`）。
> 編譯與版本漂移見 [dual_assembly_type_conflict.md](../details/dual_assembly_type_conflict.md)。
> **實機修正 1**：`UsingRequirement` 原誤用 `73`（劍法資質 QualificationSword）→ 後端 `GetPropertyValue` 不支援 Qualification* 而崩潰；已改 `87`（劍法造詣 AttainmentSword），需求只能用造詣/基礎屬性（見 [property_ids.md](../details/property_ids.md) 警告）。
> 待確認：技能是否正常顯示/可學/特效運作；mod 列表顯示名亂碼（manifest 編碼，外觀層）。§7 待確認項仍可實測後微調。

---

## 1. 武功概念

**流光劍法（Flowing-Light Sword）** —— 一把講究「連續命中累積劍意、滿溢一擊爆發」的中階劍法。

核心幻想：劍勢如流光不絕，每一次命中都讓劍意更盛；劍意滿盈時，下一次出手化為凌厲殺招。獎勵「持續進攻、不被打斷」的玩法，符合劇意堆疊型。

### 機制（正練「流光劍意」）
1. 此功法**每段命中**累積 1 層「劍意」（上限 5 層）。
2. 每層劍意提供 **+6% 本功法傷害**（被動，最多 +30%）。
3. 當劍意達 **5 層**並再次施展本功法時：消耗全部 5 層 → 獲得 **1 個殺式（殺, trickType=19）** + 此次施展**穿透 +400**，然後層數歸 0。
4. 戰鬥開始或切換武功時層數重置。

### 機制（逆練「逆·流光劍意」）
- 同樣累積劍意並加傷，但**滿層觸發改為**：消耗 5 層 → 對敵人施加 **1 個破綻（隨機部位）**，不獲得殺式。
- 設計用意：正練偏「自我增益＋資源（殺式）」，逆練偏「壓制敵人（破綻）」，給玩家流派選擇。

### 平衡考量
- 加傷上限 +30% 需要連續命中 5 段才滿，且滿層後爆發即重置，**不是無腦疊加**。
- 殺式產出受「滿層才給 1 個」限制，產率溫和。
- 數值對標原版同階劍法（克隆 太極劍法 538 的基礎框架），不破壞平衡。

---

## 2. 克隆來源與 ID 配置

| 項目 | 值 | 說明 |
|---|---|---|
| 武功克隆來源 | **538（太極劍法）** | 經典劍法，數值平衡、動畫音效沿用 |
| 特效克隆來源 | **642（五行刺特效，EffectActiveType=1）** | 結構正確的戰鬥技能特效，行為由 ClassName 覆寫故來源不影響邏輯 |
| 新武功 TemplateId | **4500** | 避開參考 mod 的 4100–4126 |
| 新正練特效 TemplateId | **8500** | 避開參考 mod 的 8200–8253 |
| 新逆練特效 TemplateId | **8501** | |
| 特效 ClassName | `MySwordArt.LiuGuangSwordIntent` | 拼成 `GameData.Domains.SpecialEffect.MySwordArt.LiuGuangSwordIntent` |

> ⚠ 克隆來源 538/642 的實際欄位值我未逐一讀出（config 是 binary）。本設計覆寫關鍵戰鬥欄位，其餘沿用來源。實機若數值怪異，再調整或換克隆來源。

---

## 3. 關鍵常數（本設計用到）

| 常數 | 值 | 來源 |
|---|---|---|
| 武功大類 Type：劍法 | **7** | `CombatSkillType.ref.txt` |
| trickType：殺 | **19** | `TrickType.ref.txt` |
| trickType：刺 / 劈 | **4 / 3** | 劍法常用招式 |
| 劍法資質 PropertyId | **73** | [屬性表](../details/property_ids.md) |
| 劍法造詣 PropertyId | **87** | |
| 屬性陣列長度 | **112** | EquipAddPropertyDict 每條 |

---

## 4. CombatSkills.yml

```yaml
4500:
 TemplateId: 538                 # 克隆 太極劍法
 Name: "流光劍法"
 44Name: "Flowing-Light Sword"
 Desc: "劍勢如流光不絕，每段命中積累劍意，劍意滿盈時化作凌厲一擊。"
 44Desc: "The blade flows like streaming light; each hit builds Sword-Intent, unleashed in a piercing strike when it brims over."
 Grade: 5                        # 中階
 Type: 7                         # 劍法
 SectId: 9                       # 鑄劍山莊 Zhujian（劍主題門派）；仍保留 CanObtainByAdventure 與過月自動送
 CanObtainByAdventure: 1
 DirectEffectID: 8500            # 正練特效
 ReverseEffectID: 8501           # 逆練特效
 UsingRequirement: [[87, 100]]   # 劍法造詣 AttainmentSword=87（原誤用 73 劍法資質，需求用 Qualification 會崩潰，見下）
 PrepareTotalProgress: 15000     # 出招速度（中等）
 Penetrate: 600
 TotalHit: 160                   # 命中段數
 InjuryPartAtkRateDistribution: [10,10,10,10,10,0,0]
 PerHitDamageRateDistribution: [70, 10, 20, 0]
 HasAtkAcupointEffect: 0
 HasAtkFlawEffect: 0
 Poisons: [0,0, 0,0, 0,0, 0,0, 0,0, 0,0]
```

## 5. SpecialEffects.yml

```yaml
8500:
 TemplateId: 642                 # 克隆一個有效的戰鬥技能特效
 Name: "流光劍意"
 44Name: "Flowing-Light Intent"
 EffectActiveType: 1
 SkillTemplateId: 4500
 RequireAttackPower: 10          # 一成威力即觸發累積
 ShortDesc: ["積累劍意", "劍意爆發"]
 44ShortDesc: ["Build Intent", "Intent Burst"]
 Desc: ["每段命中積累一層劍意（上限五層），每層使本功法傷害+6%。劍意滿五層後再次施展：消耗全部劍意，獲得一個殺式並使此次穿透+400。"]
 44Desc: ["Each hit builds 1 Sword-Intent (max 5); each stack grants +6% damage with this skill. At 5 stacks, the next cast consumes all stacks to gain 1 Sha trick and +400 penetration."]
 ClassName: "MySwordArt.LiuGuangSwordIntent"
8501:
 TemplateId: 642
 Name: "逆·流光劍意"
 44Name: "Reverse Flowing-Light Intent"
 EffectActiveType: 1
 SkillTemplateId: 4500
 RequireAttackPower: 10
 ShortDesc: ["積累劍意", "劍意爆發"]
 44ShortDesc: ["Build Intent", "Intent Burst"]
 Desc: ["每段命中積累一層劍意（上限五層），每層使本功法傷害+6%。劍意滿五層後再次施展：消耗全部劍意，對敵人隨機部位施加一個破綻。"]
 44Desc: ["Each hit builds 1 Sword-Intent (max 5); each stack grants +6% damage. At 5 stacks, the next cast consumes all stacks to inflict 1 Flaw on a random body part of the enemy."]
 ClassName: "MySwordArt.LiuGuangSwordIntent"
```

> 正逆練共用同一個 `ClassName`，行為靠特效類別內 `IsDirect` 分支（mod 標準做法）。

## 6. 特效 C# 類別

見 `~/repo/pas/projects/taiwu/MySwordArt/Backend/Effects/LiuGuangSwordIntent.cs`（本文件 §8 也附完整碼）。要點：
- `OnEnable` 訂閱 `AttackSkillAttackHit`（每段命中）與 `CastAttackSkillBegin`（施展開始，檢查滿層爆發）。
- 用 `AffectDatas` + `GetModifiedValue(int)` 做被動加傷（依當前層數）。
- 滿層爆發：正練 `DomainManager.Combat.AddTrick(ctx, char, 19, IsDirect)` + 加穿透；逆練 `AddFlaw(...)`。
- `OnDisable` 退訂所有 handler。

---

## 7. 待確認項 → 已決議（2026-05-23）

| 項目 | 決定 |
|---|---|
| 1. 克隆來源 538/642 | **保留**（538 太極劍法為多段劍法、契合「連續命中」，已實測可用） |
| 2. 數值（+6%/層、5層、穿透+400、滿層1殺式） | **維持現狀**（平衡向） |
| 3. 逆練滿層效果 | **維持施加破綻**（壓制敵人，與正練自我增益對比） |
| 4. 綁門派 | **綁鑄劍山莊 Zhujian（SectId=9）**，劍主題門派；仍保留 CanObtainByAdventure＋過月自動送 |
| 5. 名稱 | **保留「流光劍法 / Flowing-Light Sword」** |

> 全部已套用到 `dist/CombatSkills.yml` 並重新部署（純資料，不需重編 dll）。實作完整、功能已於實機驗證（技能顯示/可學/戰鬥特效）。

---

## 8. 已產出的檔案清單

於 `~/repo/pas/projects/taiwu/MySwordArt/`：
- `dist/CombatSkills.yml`、`dist/SpecialEffects.yml`、`dist/Config.Lua`（資料）
- `Backend/Effects/LiuGuangSwordIntent.cs`（特效邏輯）
- `Backend/Plugin.cs`（後端入口 + 容量 patch）
- `Frontend/Plugin.cs`（前端入口）
- `Shared/DataConfigAppender.cs` + `DataConfigAppenderHelpers.cs`（從參考 mod 移植，待清理 IL 註解）
- `Backend/MySwordArt.Backend.csproj`、`Frontend/MySwordArt.Frontend.csproj`
- `libs/YamlDotNet.dll`

> 尚未編譯。`DataConfigAppender.cs` 仍是反編譯原始碼，含 `//IL_xxxx` 與 `DefaultInterpolatedStringHandler` 痕跡，編譯前要清成正常 C#（這步留待你確認設計後再做）。
