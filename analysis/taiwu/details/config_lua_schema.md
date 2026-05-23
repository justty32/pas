# Config.lua / CombatSkills.yml / SpecialEffects.yml 欄位規格

> 日期：2026-05-22
> 來源：`~/repo/pas/projects/taiwu/MoreFactionCombatSkills/` 三個檔案，對照
> `~/dev/taiwu-src/Assembly-CSharp/Config/CombatSkillItem.cs`、`.../SpecialEffectItem.cs`、
> `~/dev/taiwu-src/Assembly-CSharp/ModManager.cs` 的 `ReadModInfoFromTable`。
> 用途：寫武學 mod 時填三個檔案的查表規格。

---

## A. Config.lua（Mod manifest）

**檔名注意**：參考 mod 用的是小寫 `Config.lua`。但 Level 2 在 `ModManager.cs:56,723` 讀取時用的常數字串是 `"Config.Lua"`（大寫 C、大寫 L）。Linux 檔案系統大小寫敏感——**實機上務必驗證遊戲到底用哪種**。工坊 mod 是給 Windows 開發的（大小寫不敏感）所以兩種都能跑，移植到 Linux 要小心。**建議先用 `Config.Lua`（與程式碼常數一致）**。

格式：MoonSharp Lua 表，`return { ... }`。欄位（武學 mod 必要的標 ★）：

| 欄位 | 型別 | 必要 | 說明 |
|---|---|:--:|---|
| `Title` | string | ★ | mod 顯示名稱 |
| `Source` | int | | 0=External(本地)/1=Steam/2=DLC。本地開發用 0（或省略，遊戲會校正） |
| `FileId` | ulong | | Steam 工坊 id。本地開發**可省略**，遊戲自動分配 temp id |
| `Version` | string | | mod 版本，如 `"1.0.0.0"` |
| `GameVersion` | string | ★ | 目標遊戲版本，如 `"0.0.79.60-test"`。< 0.0.70 或大小版號不符會走 Legacy 路徑 |
| `Author` | string | | 作者 |
| `Description` | string | | 描述（可含 `\n`） |
| `Cover` | string | | 封面圖檔名（相對 mod 資料夾） |
| `WorkshopCover` | string | | 工坊封面 |
| `TagList` | string[] | | 標籤，如 `{ "Extensions" }` |
| **`BackendPlugins`** | string[] | ★ | 後端 dll 檔名（相對 `Plugins/`）。武學 mod 戰鬥邏輯放這 |
| **`FrontendPlugins`** | string[] | ★ | 前端 dll 檔名。武學 mod 用來讓 UI 認得新武功 |
| `BackendPluginsLegacy` / `FrontendPluginsLegacy` | string[] | | 舊版相容用，新 mod 留空 `{}` |
| `BackendPatches` / `FrontendPatches` | string[] | | 純資料修正描述，武學 mod 通常留空 |
| `EventPackages` | string[] | | 事件編輯器產出包，武學 mod 留空 |
| `Dependencies` | ulong[] | | 相依 mod 的 FileId 清單 |
| `Visibility` | int | | 0=公開 |
| **`ChangeConfig`** | bool | ★ | 會改 ConfigCell → 武學 mod 設 `true` |
| **`HasArchive`** | bool | ★ | 帶存檔資料 → 武學 mod 設 `true`（角色學會的新武功要存） |
| `NeedRestartWhenSettingChanged` | bool | | 改設定需重啟。語言切換類設 `true` |
| `DefaultSettings` | table[] | | 玩家可調設定（見下） |
| `UpdateLogList` | table[] | | 更新日誌 |

### DefaultSettings 條目格式

```lua
DefaultSettings = {
    { SettingType="Dropdown", Key="Language", DisplayName="语言", Description="...",
      Options={"简体中文","English"}, DefaultValue=0 },
    { SettingType="Toggle", Key="LearnAll", DisplayName="...", Description="...", DefaultValue=false },
}
```

`SettingType` 五選一（`ModManager.cs:992-1000`）：`Toggle` / `ToggleGroup` / `InputField` / `Slider` / `Dropdown`。其他值會丟 `InvalidOperationException`。在 plugin 內讀：`DomainManager.Mod.GetSetting(modIdStr, "Key", ref val)`（backend）/ `ModManager.GetSetting(...)`（frontend）。

---

## B. CombatSkills.yml（武功定義）

**結構**：YAML 頂層 mapping，`新TemplateId: { 欄位... }`。

```yaml
4126:                    # ← 新 TemplateId（>= 原表大小，建議 4000+）
 TemplateId: 477         # ← 克隆來源的原版 TemplateId（必填）
 <欄位>: <值>            # ← 覆寫到克隆副本上
```

**載入規則**（解剖報告 §5）：
- 頂層 key = `NewTemplateId`，必須 >= 原 config 表大小（否則 `EnsureExtraTemplateId` throw）。
- `TemplateId` 欄位 = 要 `Duplicate()` 的來源；其餘欄位以反射覆寫。
- `<數字><欄位名>`（如 `44Name`）= 該 LanguageKey 專用值（44=英文，86=中文預設）。

**欄位**（對照 `CombatSkillItem.cs`，型別為遊戲內欄位型別）：

| 欄位 | 型別 | 說明 |
|---|---|---|
| `TemplateId` | short | 克隆來源 id（YAML 專用，不是最終 id） |
| `Name` | string | 武功名 |
| `Desc` | string | 描述 |
| `Grade` | sbyte | 品級（0=最高？依原版慣例，數字越大越低階；範例 8 階常見） |
| `Type` | sbyte | 武功類型。**劍法 = 7**（對照屬性表 AttainmentSword=87 的武學分類順序：拳掌3/指4/腿5/暗器6/劍7/刀8/長兵9/奇門10…）|
| `SubType` | ECombatSkillSubType | -1=Invalid, 0=Curse |
| `EquipType` | sbyte | 裝備類型 |
| `SectId` | sbyte | 門派 id（0=無門派/通用） |
| `FiveElements` | sbyte | 五行屬性 |
| `BookId` | short | 對應秘笈 id，-1=無 |
| `CanObtainByAdventure` | bool(0/1) | 可否歷練取得 |
| `OrderIdInSect` | sbyte | 門派內排序 |
| **`UsingRequirement`** | List<PropertyAndValue> | 使用需求 `[[PropertyId, Value], ...]`，如 `[[0,160],[73,500]]`（臂力160+劍法資質500）|
| **`DirectEffectID`** | int | 正練特效的 TemplateId（指向 SpecialEffects.yml）|
| **`ReverseEffectID`** | int | 逆練特效的 TemplateId |
| `PrepareTotalProgress` | int | 蓄力總進度（出招快慢，越大越慢；範例 16000–22000）|
| `BaseInnerRatio` | sbyte | 基礎內息比例 |
| `InnerRatioChangeRange` | sbyte | 內息比例變化範圍 |
| `Penetrate` | short | 穿透 |
| `DistanceAdditionWhenCast` | short | 出招時距離加成 |
| **`InjuryPartAtkRateDistribution`** | sbyte[] | 7 個身體部位的攻擊分配，如 `[10,10,0,10,10,10,10]` |
| **`TotalHit`** | short | 總命中段數（範例 180–200）|
| **`PerHitDamageRateDistribution`** | sbyte[] | 每段傷害分配 `[外功, ?, 內功, ?]`，如 `[70,10,20,0]` |
| `HasAtkAcupointEffect` | bool(0/1) | 攻擊是否帶點穴 |
| `HasAtkFlawEffect` | bool(0/1) | 攻擊是否帶破綻 |
| `Poisons` | PoisonsAndLevels | 12 元素陣列 `[type,lvl, ...]`（6 種毒×2）|
| `MobilityCost` | short | 行動力消耗 |
| `BreathStanceTotalCost` | sbyte | 提氣架勢總消耗 |
| `TrickCost` | List<NeedTrick> | 招式消耗 |
| `WeaponDurableCost` | sbyte | 武器耐久消耗 |
| `NeedBodyPartTypes` | List<sbyte> | 需要的身體部位 |

> 還有大量資產欄位（`AssetFileName`/`PrepareAnimation`/`CastParticle`/`CastSoundEffect` 等）控制動畫音效，**克隆時沿用來源即可**，新 mod 通常不覆寫（會繼承原版視覺）。

---

## C. SpecialEffects.yml（特效定義）

**結構**：同 CombatSkills.yml，`新TemplateId: { TemplateId: 來源, 欄位... }`。建議新 id 8000+。

**欄位**（對照 `SpecialEffectItem.cs`）：

| 欄位 | 型別 | 說明 |
|---|---|---|
| `TemplateId` | short | 克隆來源 id（YAML 專用）|
| `Name` | string | 特效名 |
| `EffectActiveType` | sbyte | **特效類型**：1=正練、2/3=其他啟用型（見下）|
| `SkillTemplateId` | short | 綁定的武功 TemplateId（指回 CombatSkills.yml）|
| `RequireAttackPower` | sbyte | 觸發威力門檻（範例 10 = 一成）|
| `MinEffectCount` / `MaxEffectCount` | short | 效果層數上下限 |
| `ShortDesc` | string[] | **tip 短描述陣列**（`ShowSpecialEffectTips(idx)` 的 idx 對應此陣列）。**注意一定是陣列**，即使一條也要 `["..."]` |
| `Desc` | string[] | 詳細描述陣列 |
| `AffectRequirePower` | int[] | 各層的威力需求 |
| `TransferProportion` | int | 轉化比例 |
| **`ClassName`** | string | **特效行為類別名**，會拼成 `GameData.Domains.SpecialEffect.<ClassName>` 反射查找。如 `"MoreFactionCombatSkills.JieQingMen.Qimen9"` |

**EffectActiveType 語意**（從 `SpecialEffectDomain.cs:269,375` 與 `ReverseNext.cs:67` 推斷）：
- `1` = 戰鬥技能正逆練特效（最常見，劍法用這個）
- `2` / `3` = 其他啟用類型（3 在 `FixAdd` 內走「帶 direction 的 ctor」分支，見解剖報告 §6.2）

**正逆練的關鍵 pattern**：同一個 `ClassName` 可被正練與逆練共用，行為靠特效類別內 `IsDirect` 分支。所以 CombatSkills.yml 的 `DirectEffectID` 和 `ReverseEffectID` 可指向兩個 SpecialEffects.yml 條目，但兩條目 `ClassName` 相同。

---

## D. 三檔交叉引用關係圖

```
CombatSkills.yml             SpecialEffects.yml                   特效 C# class
─────────────────            ──────────────────                   ──────────────
4126:                        8252:                                namespace GameData.Domains
 TemplateId: 477              TemplateId: 642                        .SpecialEffect.MyMod;
 DirectEffectID: 8252  ─────► SkillTemplateId: 4126               class MyEffect
 ReverseEffectID: 8253        ClassName: "MyMod.MyEffect" ───────►   : CombatSkillEffectBase
                             8253:                                  { OnEnable/OnDisable... }
                              SkillTemplateId: 4126
                              ClassName: "MyMod.MyEffect"
                              EffectActiveType: 1
```

連動規則：
1. 武功 `DirectEffectID`/`ReverseEffectID` → 指向特效的新 TemplateId。
2. 特效 `SkillTemplateId` → 指回武功的新 TemplateId。
3. 特效 `ClassName` → 反射對應到 `GameData.Domains.SpecialEffect.<ClassName>` 的類別。
4. 三者的「新 TemplateId」都必須避開原版範圍（武功 4000+、特效 8000+）。

---

## E. 最小可動的三檔範本（劍法）

**CombatSkills.yml**
```yaml
4200:
 TemplateId: 400          # 克隆某把原版劍法（id 待定）
 Name: "範例劍法"
 44Name: "Example Sword Art"
 Desc: "(暫無描述)"
 Grade: 5
 Type: 7                  # 劍法
 SectId: 0
 DirectEffectID: 8300
 ReverseEffectID: 8301
 UsingRequirement: [[73, 300]]   # 劍法資質 300
 TotalHit: 150
 PerHitDamageRateDistribution: [70, 10, 20, 0]
 InjuryPartAtkRateDistribution: [10,10,10,10,10,0,0]
```

**SpecialEffects.yml**
```yaml
8300:
 TemplateId: 640          # 克隆某個特效當基底
 Name: "範例劍意"
 44Name: "Example Sword Intent"
 SkillTemplateId: 4200
 EffectActiveType: 1
 RequireAttackPower: 10
 ShortDesc: ["累積劍意"]
 Desc: ["每次命中累積 1 層劍意，滿 5 層時下一擊傷害翻倍。"]
 ClassName: "MyMod.Sword.ExampleSwordIntent"
8301:
 TemplateId: 640
 Name: "逆·範例劍意"
 SkillTemplateId: 4200
 EffectActiveType: 1
 ClassName: "MyMod.Sword.ExampleSwordIntent"
```

**特效 class**（編進 backend dll）
```csharp
namespace GameData.Domains.SpecialEffect.MyMod.Sword;   // ← 必須以 GameData.Domains.SpecialEffect 開頭

internal class ExampleSwordIntent : CombatSkillEffectBase
{
    private int _stack;
    public ExampleSwordIntent() { }
    public ExampleSwordIntent(CombatSkillKey key) : base(key, 4200, (sbyte)(-1)) { }

    public override void OnEnable(DataContext ctx)
    {
        _stack = 0;
        Events.RegisterHandler_AttackSkillAttackHit(new OnAttackSkillAttackHit(OnHit));
    }
    public override void OnDisable(DataContext ctx)
    {
        Events.UnRegisterHandler_AttackSkillAttackHit(new OnAttackSkillAttackHit(OnHit));
    }
    private void OnHit(DataContext ctx, CombatCharacter atk, CombatCharacter def, short skillId, int idx, bool crit)
    {
        if (atk.GetId() == CharacterId && skillId == SkillTemplateId) { /* 累積與觸發邏輯 */ }
    }
}
```

> 範本中的 id（400/640/4200/8300）為佔位，B 階段會用實際原版 id 替換並設計真正的數值與機制。

---

## F. 參考檔案
- `~/repo/pas/projects/taiwu/MoreFactionCombatSkills/{Config.lua, CombatSkills.yml, SpecialEffects.yml}`
- `~/dev/taiwu-src/Assembly-CSharp/Config/CombatSkillItem.cs`
- `~/dev/taiwu-src/Assembly-CSharp/Config/SpecialEffectItem.cs`
- `~/dev/taiwu-src/Assembly-CSharp/ModManager.cs`（`ReadModInfoFromTable`）
- 交叉參見 [屬性 ID 表](property_ids.md)、[backend 事件](backend_combat_events.md)、[mod 解剖](martial_arts_mod_anatomy.md)
