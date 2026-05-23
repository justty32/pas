# 解剖：「更多门派功法」武學 Mod 的工作原理

> 日期：2026-05-22
> 範圍：完整解剖工坊 mod *3700522118*「更多门派功法CN/EN」(作者 wilhelm)，重點在「**如何新增一個武功**」的具體實作模式。
> 原始 mod：`~/repo/pas/projects/taiwu/MoreFactionCombatSkills/`
> 反編譯產物：
> - Backend：`~/dev/taiwu-src/mods/MoreFactionCombatSkillsBackend/`（35 .cs）
> - Frontend：`~/dev/taiwu-src/mods/MoreFactionCombatSkillsFrontend/`（5 .cs）

## 0. 一句話總結

> **以 YAML 描述新武功（CombatSkillItem）與其特效（SpecialEffectItem），運行時克隆原版條目並以 reflection 覆寫欄位，新特效行為以獨立 C# class 寫成、放在固定命名空間 `GameData.Domains.SpecialEffect.<...>`，遊戲透過反射依字串實例化。**

整套機制可重複利用，作者把它抽成一個 mini-framework 叫 `FeaturesBoundToFuyu`（命名空間），是 mod 工程的核心，不是遊戲提供的 API。

---

## 1. Mod 結構回顧

```
MoreFactionCombatSkills/
├── Config.lua                        ← 注意檔名小寫 .lua（Level 2 已用過大寫，Linux 大小寫敏感，實機要驗）
├── Cover.png
├── CombatSkills.yml          31 KB   ← 武功定義
├── SpecialEffects.yml        34 KB   ← 特效定義
├── run.bat, run1.bat                  ← 作者本機建置腳本，無關運行
└── Plugins/
    ├── MoreFactionCombatSkillsBackend.dll
    ├── MoreFactionCombatSkillsFrontend.dll
    └── YamlDotNet.dll                 ← 相依，與主 dll 同層（Level 2 §9 dll 級相依機制）
```

`Config.lua` 內最關鍵的：

```lua
BackendPlugins  = { "MoreFactionCombatSkillsBackend.dll" }
FrontendPlugins = { "MoreFactionCombatSkillsFrontend.dll" }
ChangeConfig    = true        -- ConfigCell 會被修改
HasArchive      = true        -- 該 mod 有存檔資料
NeedRestartWhenSettingChanged = true
DefaultSettings = {
    { SettingType="Dropdown", Key="Language", Options={"简体中文","English"}, DefaultValue=0 },
    { SettingType="Toggle",   Key="LearnAll", DefaultValue=false },
}
```

→ 確認 Level 2 §6 的雙端載入：**武學 mod 必須同時提供 Backend + Frontend plugin**，因為戰鬥邏輯跑在 backend、UI/顯示在 frontend。

---

## 2. 進入點與初始化（Backend 端）

`~/dev/taiwu-src/mods/MoreFactionCombatSkillsBackend/FeaturesBoundToFuyu/FeaturesBoundToFuyuPlugin.cs:25-73`

```csharp
[PluginConfig("FeaturesBoundToFuyuPlugin", "wilhelm", "1.0")]
public class FeaturesBoundToFuyuPlugin : TaiwuRemakePlugin   // ← 注意：非 Harmony 基類
{
    private Harmony harmony;
    public static int LanguageKey { get; private set; }
    public static bool LearnAll  { get; private set; }

    public override void Initialize()
    {
        harmony = Harmony.CreateAndPatchAll(typeof(FeaturesBoundToFuyuPlugin));   // ← 只 patch 自己這個 class
        var modDirectory = DomainManager.Mod.GetModDirectory(ModIdStr);            // ← Backend 取 mod 目錄
        int lang = 0;
        DomainManager.Mod.GetSetting(ModIdStr, "Language", ref lang);              // ← Backend 取設定
        bool learnAll = false;
        DomainManager.Mod.GetSetting(ModIdStr, "LearnAll", ref learnAll);
        LearnAll = learnAll;
        LanguageKey = (lang == 1) ? 44 : 86;                                       // ← 44=英文, 86=中文

        DataConfigAppender.LoadSpecialEffectsFromYamlFile(
            Path.Combine(modDirectory, "SpecialEffects.yml"));
        DataConfigAppender.LoadCombatSkillsFromYamlFile(
            Path.Combine(modDirectory, "CombatSkills.yml"));
    }
}
```

**Backend mod 比 Frontend 多出來的 API（這份分析最大的副產品）**：

| 用途 | Backend API（在此被使用） | 對應的 Frontend API |
|---|---|---|
| 取 mod 目錄 | `DomainManager.Mod.GetModDirectory(modIdStr)` | `ModManager.GetModInfo(modIdStr).DirectoryName` |
| 取 mod 設定 | `DomainManager.Mod.GetSetting(modIdStr, key, ref val)` | `ModManager.GetSetting(modIdStr, key, ref val)` |

→ Backend 沒有 `ModManager` 可用（那是 Unity 前端的東西）；它走 `DomainManager.Mod.*`（位於 `GameData/Domains/Mod/ModDomainHelper.cs`）。這對 Level 2 §6 的「backend plugin 載入點未知」是個重要線索：backend 那邊有自己的 `DomainManager`，跟前端的 `SingletonObject` 是不同的 IoC 容器。

**Plugin 繼承選擇**：用了 `TaiwuRemakePlugin`（非 Harmony 版本），自己手動 `Harmony.CreateAndPatchAll(typeof(自己))`。原因推測：Harmony 版預設 `PatchAll(GetType().Assembly)` 會掃整個 dll 的所有 patch class，這邊只想 patch 自己這個 class 的方法。

---

## 3. 進入點與初始化（Frontend 端）

`~/dev/taiwu-src/mods/MoreFactionCombatSkillsFrontend/FeaturesBoundToFuyu/SpellsFromTheWestFrontendPlugin.cs:9-43`

```csharp
[PluginConfig("SpellsFromTheWestFrontendPlugin", "wilhelm", "1.0")]
public class SpellsFromTheWestFrontendPlugin : TaiwuRemakePlugin
{
    public override void Initialize()
    {
        AdaptableLog.Info("Load SpellsFromTheWest Frontend...");
        harmony = Harmony.CreateAndPatchAll(typeof(SpellsFromTheWestFrontendPlugin));
        var modInfo = ModManager.GetModInfo(ModIdStr);
        var directoryName = modInfo.DirectoryName;

        int val = 0;
        ModManager.GetSetting(ModIdStr, "Language", ref val);
        LanguageKey = (val == 1) ? 44 : 86;

        DataConfigAppender.LoadCombatSkillsFromYamlFile(Path.Combine(directoryName, "CombatSkills.yml"));
        DataConfigAppender.LoadSpecialEffectsFromYamlFile(Path.Combine(directoryName, "SpecialEffects.yml"));
    }
}
```

**重要：YAML 在 Frontend 與 Backend 都會被讀一次**。原因：前端與後端各自有自己的 `Config.Instance`（例如 `CombatSkill.Instance`、`SpecialEffect.Instance`），這些是不同 assembly 的單例。**新武功必須同時注入兩邊**，否則前端 UI 顯示不出、或後端戰鬥找不到。

**命名怪事**：前端 class 叫 `SpellsFromTheWestFrontendPlugin`，後端叫 `FeaturesBoundToFuyuPlugin`，PluginName 也不同，但 ModIdStr 一致。`PluginHelper.GetEntrypointType` 只看 `BaseType == TaiwuRemakePlugin`，名稱無所謂。這是作者跨 mod 共用程式碼留下的痕跡（`SpellsFromTheWest` 推測是早期作品名）——對自製 mod 沒有影響，只是參考。

---

## 4. YAML 資料格式：「克隆並覆寫」

### 4.1 CombatSkills.yml（武功本體）

來自 `~/repo/pas/projects/taiwu/MoreFactionCombatSkills/CombatSkills.yml`（節錄）：

```yaml
4126:                                            # ← 新 TemplateId（YAML 頂層 key）
 TemplateId: 477                                 # ← 來源 TemplateId（克隆對象）
 Grade: 8                                        # ← 後續欄位覆寫到克隆出來的副本上
 Name: "万龙破天步"
 Desc: "(暂无描述)"
 DirectEffectID: 8252                            # ← 正練特效 → SpecialEffects.yml 內 8252
 ReverseEffectID: 8253                           # ← 逆練特效
 SectId: 14
 FiveElements: 3
 BookId: -1
 UsingRequirement: [[ 0, 160], [ 3, 60], [ 85, 500], [ 55, 400], [ 64, 400]]
 PrepareTotalProgress: 22000
 InnerRatioChangeRange: 10
 Penetrate: 700
 DistanceAdditionWhenCast: 5
 InjuryPartAtkRateDistribution: [10,10,0,10,10,10,10]   # 7 段傷害的分配（陣列）
 TotalHit: 200
 PerHitDamageRateDistribution: [70, 10, 20, 0]
 HasAtkAcupointEffect: 0
 HasAtkFlawEffect: 1
 Poisons: [0,0, 0,0, 0,0, 0,0, 0,0, 0,0]
 44Desc: "(no description)"                      # ← LanguageKey=44 (英文) 才用這值
 44Name: "Dragons Heaven-Breaking Step"
```

**這個檔案的標頭（前 111 行註解）**列出全部 0-111 的角色屬性 ID 對照表（Strength=0, Dexterity=1, ..., MaxHealth=104, MaxNeili=105 ...），對任何想動屬性的 mod 都是無價的參考。

### 4.2 SpecialEffects.yml（特效本體）

```yaml
8200:                                              # 新 TemplateId
 TemplateId: 642                                   # 克隆來源（五行刺）
 EffectActiveType: 1                               # 1=正練/2=逆練/3=...（見 §7）
 Name: "星罗钉"
 44Name: "Star-Studded Pin"
 SkillTemplateId: 4100                             # 對應到 CombatSkills.yml 內 4100
 ShortDesc: ["获得杀式"]
 44ShortDesc: ["Gain Sha Trick"]
 Desc: ["开始释放时：获得一个杀式。发挥一成威力时：若我方杀式小于三个，则获得两个杀式。"]
 44Desc: ["When starting to cast: ..."]
 RequireAttackPower: 10
 ClassName: "MoreFactionCombatSkills.JieQingMen.Qimen9"     # ★ 反射查找此 class
```

**`ClassName`** 是這份 mod 最巧妙的設計。值 `"MoreFactionCombatSkills.JieQingMen.Qimen9"` 在被 patch 過的 `SpecialEffectDomain.Add` 內會被拼成 `"GameData.Domains.SpecialEffect." + ClassName` 去 `Type.GetType()` 找——所以 mod 的特效類別 **必須放在 `GameData.Domains.SpecialEffect.<...>` 命名空間下**。

---

## 5. 資料注入機制：`DataConfigAppender`

源碼：`~/dev/taiwu-src/mods/MoreFactionCombatSkillsBackend/FeaturesBoundToFuyu/DataConfigAppender.cs`

### 5.1 流程

```
LoadCombatSkillsFromYamlFile(path)
  └── ParseYamlTopLevelObjects(yaml)
        ├── YAML 頂層 mapping 視為 {newTemplateId: {fieldName: value, ...}}
        ├── 每個 value 內若 key 是純數字+字串前綴 → 視為 localized field（44Name 等）
        └── 回傳 Dictionary<int, Dictionary<string,object>>
  └── foreach 每筆 YAML 條目:
        ├── 抽 TemplateId 欄位（克隆來源）
        ├── 把 NewTemplateId 加進 changes（YAML 頂層 key）
        ├── CreateAndAppendCombatSkillItemFromStringsNew(srcId, changes)
        │     ├── srcItem = CombatSkill.Instance[(short)srcId]
        │     ├── EnsureExtraTemplateId(newId, baseCount, "CombatSkillItem")
        │     │     └─ 規則：newId 必須 >= baseConfigCount（不能蓋掉原版）
        │     ├── newItem = srcItem.Duplicate(newId)              ← ★ ConfigItem 自帶 Duplicate
        │     ├── ApplyChanges(newItem, changes, ignored:["TemplateId","NewTemplateId"])
        │     │     └─ 反射依 fieldName 找 FieldInfo/PropertyInfo
        │     │        BindingFlags = NonPublic|Instance|Public|Static|... (53)
        │     │        ConvertChangeValue：YAML int→int、YAML list→T[] / List<T> / ctor(T[]) 等
        │     └── SaveCombatSkillItem(newItem)
        │           └── DataConfigAppenderHelpers.AddCombatSkillItemToConfig(idStr, refName, item)
        │                 ├── CombatSkill.Instance.AddExtraItem(idStr, name, item)  ← 加進 ConfigData 的 _dataArray
        │                 ├── AddSkillBreakGridList(item)
        │                 │     └─ 從同 Grade+Type 的原版找一個當參考，
        │                 │        複製其 SkillBreakGridListItem 的 5 個 break-grid 列表，
        │                 │        以 newId 寫一筆進 SkillBreakGridList.Instance
        │                 └─ 把 item 加進 helper 的 _combatSkillItems 列表（給後續 Install 用）
```

特效注入流程一樣，只是換成 `SpecialEffect.Instance` 與 `SpecialEffectItem`，且不會 attach SkillBreakGridList。

### 5.2 關鍵實作細節

- **`ConfigItem<T,K>.Duplicate(newId)`**：遊戲內建 API，深拷貝一份原 config item 並指定新 id。是這套機制能成立的基石。
- **`ConfigData<T,K>.AddExtraItem(idStr, name, item)`**：把新 item 塞進該 ConfigData 的內部 `_dataArray`（從 helpers 內可見走 reflection 取 `_dataArray` 的證據——`DataConfigAppenderHelpers.cs:29-30`）。`name` 參數是 ConfigData 內部的 ref name，用作字串索引，模式為 `<原Name>_<TemplateId>`。
- **`EnsureExtraTemplateId`**：強制新 TemplateId 必須 >= 原表大小，避免蓋原版條目。
  - 武功實際範例：原版 CombatSkill 應在數百筆規模，YAML 內第一筆是 `4100`，這個 buffer 足以避碰撞。
  - 特效範例：原版規模類似，YAML 第一筆 `8200`。
- **本地化欄位前綴**：`TryParseLocalizedMemberKey("44Name")` 拆出 `languageKey=44, memberName="Name"`。`ApplyChanges` 時若有對應 LanguageKey 的覆寫，優先選之；否則用 base（無前綴）值。LanguageKey 取自 `FeaturesBoundToFuyuPlugin.LanguageKey`，由 mod 設定的 `Language` Dropdown 決定。

---

## 6. 容量擴張：解決遊戲內建 array 太小

最關鍵的兩個 Harmony patch（`FeaturesBoundToFuyuPlugin.cs:130-260`）：

### 6.1 `CombatSkillDomain.InitializeOnInitializeGameDataModule` 整段 Prefix replacement

原版這個方法會以 `CombatSkill.Instance.Count` 作為 dict 大小，但 mod 加進新 ID 後該 dict 不夠裝。Mod 直接 `return false` 阻擋原版 + 自己重做：

```csharp
[HarmonyPrefix]
[HarmonyPatch(typeof(CombatSkillDomain), "InitializeOnInitializeGameDataModule")]
public static bool InitializeOnInitializeGameDataModule_Hijack()
{
    int n = 32768;                                      // ★ 寫死 32768
    CombatSkillDomain.EquipAddPropertyDict = new short[n][];
    foreach (CombatSkillItem item in (IEnumerable<CombatSkillItem>)CombatSkill.Instance)
    {
        if (item == null) continue;
        short tid = item.TemplateId;
        if (tid < 0) continue;
        var list = item.PropertyAddList;
        if (list == null || list.Count == 0) continue;
        var arr = new short[112];                       // 112 = 全部屬性 ID 數
        foreach (var pv in list) {
            if (pv.PropertyId >= 0 && pv.PropertyId < arr.Length)
                arr[pv.PropertyId] = pv.Value;
        }
        CombatSkillDomain.EquipAddPropertyDict[tid] = arr;
    }
    // 重跑 private InitializeLearnableCombatSkillTemplateIds
    AccessTools.Method(typeof(CombatSkillDomain), "InitializeLearnableCombatSkillTemplateIds")
              ?.Invoke(null, null);
    return false;                                       // 不執行原版
}
```

→ **想 mod 任何「為遊戲新增條目」的玩法都會碰到類似容量問題**。這種「Prefix 整段取代＋大幅放大初始容量」是個通用 pattern，可以抄。

### 6.2 `SpecialEffectDomain.Add` 兩個 overload 的 Prefix replacement

原版用 type 系統內建路徑（編譯時就知道的型別）來建 SpecialEffect 實例。Mod 把它改成「先反射依字串名 `"GameData.Domains.SpecialEffect." + effectName`（或 + `effectItem.ClassName`）找 type，Activator.CreateInstance 建之」：

```csharp
string text = "GameData.Domains.SpecialEffect." + effectName;
Type type = Type.GetType(text) ?? AccessTools.TypeByName(text);   // ★ 反射查找
if (type == null) throw new Exception("Cannot find type '" + text + "'.");
SpecialEffectBase val = (SpecialEffectBase)Activator.CreateInstance(type, charId);
__instance.Add(context, val);
__result = val.Id;
return false;
```

→ 這個 patch 才是讓 mod 加的新特效類別能被遊戲找到的關鍵。沒有它，遊戲只認識原版內建的特效類。

### 6.3 `CombatDomain.CastSkillFree` Postfix hook

```csharp
[HarmonyPostfix]
[HarmonyPatch(typeof(CombatDomain), "CastSkillFree", ...)]
public static void OnCastSkillFreePatched(DataContext ctx, CombatCharacter chr, short skillId, ECombatCastFreePriority prio)
    => MoreFactionCombarSkillsEvents.RaiseCastSkillFree(ctx, chr, skillId, prio);
```

→ 因為原版沒對「自動釋放技能」拋出可訂閱事件，mod 自製了一個 `MoreFactionCombarSkillsEvents.CastSkillFree` 並用 Postfix 觸發它。給各特效類別當作 hook 點。

---

## 7. 特效類別的實作範式

每個 YAML 內 `ClassName` 指到的類別都繼承 `CombatSkillEffectBase`（在 `GameData.Domains.SpecialEffect.CombatSkill` 內）。命名空間必須以 `GameData.Domains.SpecialEffect.` 開頭。

### 7.1 簡單範例（無實質行為）

`~/dev/taiwu-src/mods/MoreFactionCombatSkillsBackend/GameData/Domains/SpecialEffect/MoreFactionCombatSkills/JinGangZong/Jianfa1.cs`：

```csharp
using GameData.Domains.CombatSkill;
using GameData.Domains.SpecialEffect.CombatSkill;

namespace GameData.Domains.SpecialEffect.MoreFactionCombatSkills.JinGangZong;

internal class Jianfa1 : CombatSkillEffectBase
{
    public static readonly short Jianfa1TId = 4117;   // 用來查 CombatSkills.yml 內的 TemplateId

    public Jianfa1() { }
    public Jianfa1(CombatSkillKey skillKey) : base(skillKey, (int)Jianfa1TId, (sbyte)(-1)) { }
}
```

→ 對應 Config.lua 描述的「佛王之剑：該功法無論正逆均無特效」。沒覆寫 OnEnable/OnDisable 就是「掛上但什麼都不做」。

### 7.2 完整範例：星羅釘 Qimen9

`~/dev/taiwu-src/mods/MoreFactionCombatSkillsBackend/GameData/Domains/SpecialEffect/MoreFactionCombatSkills/JieQingMen/Qimen9.cs`：

```csharp
internal class Qimen9 : CombatSkillEffectBase
{
    private int _SkillPower;

    public Qimen9() { }
    public Qimen9(CombatSkillKey skillKey) : base(skillKey, 54100, (sbyte)(-1)) { }

    public override void OnEnable(DataContext context)
    {
        _SkillPower = 0;
        if (IsDirect)
        {
            AffectDatas = new Dictionary<AffectedDataKey, EDataModifyType>();
            AffectDatas.Add(new AffectedDataKey(CharacterId, 199, -1, -1, -1, -1),
                            (EDataModifyType)0);
        }
        Events.RegisterHandler_CastSkillEnd(new OnCastSkillEnd(OnCastSkillEnd));
        Events.RegisterHandler_PrepareSkillBegin(new OnPrepareSkillBegin(OnPrepareSkillBegin));
    }

    public override void OnDisable(DataContext context)
    {
        Events.UnRegisterHandler_PrepareSkillBegin(...);
        Events.UnRegisterHandler_CastSkillEnd(...);
    }

    private void OnPrepareSkillBegin(DataContext ctx, int charId, bool isAlly, short skillId)
    {
        if (charId == CharacterId && skillId == SkillTemplateId) {
            DomainManager.Combat.AddTrick(ctx,
                IsDirect ? CombatChar : DomainManager.Combat.GetCombatCharacter(!isAlly, false),
                (sbyte)19,    // ← 19 是「杀式」trick id
                IsDirect);
            ShowSpecialEffectTips(0);
        }
    }

    private void OnCastSkillEnd(DataContext ctx, int charId, bool isAlly, short skillId, sbyte power, bool interrupted)
    {
        if (charId == CharacterId && skillId == SkillTemplateId) {
            int n = IsDirect
                ? Helpers.CountTricks(CombatChar, 19)
                : Helpers.CountTricks(CurrEnemyChar, 19);
            if (n < 3) {
                ShowSpecialEffectTips(0);
                DomainManager.Combat.AddTrick(ctx, ..., 19, 2, IsDirect, false);
            }
        }
    }
}
```

**通用範式（自製武功特效會反覆套用）**：

1. 繼承 `CombatSkillEffectBase`。
2. 兩個 ctor：`()`（給反序列化用）+ `(CombatSkillKey)`（傳給基類，含特效自己的 id）。
3. `OnEnable`：訂閱戰鬥事件（`Events.RegisterHandler_*`），可選地設定 `AffectDatas`。
4. `OnDisable`：對應 `UnRegisterHandler_*`。
5. 事件 handler 內檢查 `charId == CharacterId && skillId == SkillTemplateId` 過濾自己。
6. 變更狀態用 `DomainManager.<Domain>.<Method>(context, ...)`（如 `AddTrick`, `Heal`, `AddInjury`）。
7. 顯示 tip 用 `ShowSpecialEffectTips(idx)` —— `idx` 對應到 SpecialEffects.yml 內 `ShortDesc` 陣列的索引。
8. 正逆判定用 `IsDirect`。`ShortDesc`、`Desc` 等是 list 而非 string，就是因為支援多個 tip 索引。

### 7.3 可用的 backend Events（從觀察推得）

從 Qimen9 與 `MoreFactionCombarSkillsEvents.cs`（mod 自製）觀察，遊戲提供至少：

- `CastSkillEnd(ctx, charId, isAlly, skillId, power, interrupted)`
- `PrepareSkillBegin(ctx, charId, isAlly, skillId)`
- `AdvanceMonthFinish(context)` （用在 plugin 入口處註冊）
- `CastSkillFree(...)`（mod **自製**，原版沒提供）

→ 完整可用事件清單要去翻 `~/dev/taiwu-src/Assembly-CSharp/GameData/DomainEvents/`（Level 3 待辦）。

---

## 8. 「過月送武功」機制

`FeaturesBoundToFuyuPlugin.cs:84-128`：

```csharp
public override void OnEnterNewWorld()
{
    Events.UnRegisterHandler_AdvanceMonthFinish(new OnAdvanceMonthFinish(AdvanceFinishHandler));
    Events.RegisterHandler_AdvanceMonthFinish(new OnAdvanceMonthFinish(AdvanceFinishHandler));
}
public override void OnLoadedArchiveData()  // 同上，雙重註冊保險
{
    ...
}
public void AdvanceFinishHandler(DataContext context) => Install();

private void Install()
{
    foreach (var item in DataConfigAppenderHelpers.CombatSkillItems)
        learn(DataContextManager.GetCurrentThreadDataContext(), item.TemplateId);
    if (LearnAll)
        for (int i = 0; i < 722; i++)
            learn(DataContextManager.GetCurrentThreadDataContext(), (short)i);
}

private void learn(DataContext ctx, short tid)
{
    TaiwuCombatSkill val = default;
    if (!DomainManager.Taiwu.TryGetElement_CombatSkills(tid, ref val))
        DomainManager.Taiwu.TaiwuLearnCombatSkill(ctx, tid, ushort.MaxValue);
}
```

→ 為何不是「進入存檔就送」而是「過月才送」？因為 `OnEnterNewWorld` / `OnLoadedArchiveData` 觸發時間點某些 backend state 尚未完成，作者實際測過會踩雷（Config.lua 描述有「修复开局进门直接报错的问题，现在改为过月添加功法」這條 changelog 為證）。

→ 想自製 mod 把新武功**自動傳授**給主角，照抄 `OnEnterNewWorld → 註冊 AdvanceMonthFinish → 在 handler 內 `TaiwuLearnCombatSkill`` 這條路。

---

## 9. 自製武學 Mod 工作清單（給後續實作用）

按優先序：

1. **取一個原版武功當克隆基底**：選一個 Grade/Type 跟你想要的接近的，記下其 TemplateId（去 `~/dev/taiwu-src/Assembly-CSharp/Config/ConfigCells/` 撈，或寫個小工具列出）。
2. **設計 YAML**：
   - `CombatSkills.yml`：選個未用過的 `NewTemplateId`（>= 原表大小，4000+ 是安全範圍），填 `TemplateId: <來源id>`、覆寫 `Name`、`Desc`、`44Name`、`44Desc`、`DirectEffectID`、`ReverseEffectID`、`SectId`、`InjuryPartAtkRateDistribution`、`PerHitDamageRateDistribution`、`UsingRequirement` 等。
   - `SpecialEffects.yml`：填 `NewTemplateId`（8000+ 安全）、`TemplateId`（克隆來源）、`EffectActiveType`、`SkillTemplateId`（指回 CombatSkills.yml 的 4xxx）、`Name/Desc`、`44Name/44Desc`、`RequireAttackPower`（觸發威力閾值）、`ShortDesc`（tip 索引陣列）、`ClassName`（你要寫的特效 class 完整名）。
3. **寫特效 class**（`GameData.Domains.SpecialEffect.<YourNamespace>.YourEffect`）：繼承 `CombatSkillEffectBase`，覆寫 `OnEnable/OnDisable`，註冊事件。
4. **寫 backend plugin**：抄 `FeaturesBoundToFuyuPlugin` 結構——`Initialize` 內 `Harmony.CreateAndPatchAll(typeof(自己))` + `LoadSpecialEffectsFromYamlFile/LoadCombatSkillsFromYamlFile`、`OnEnterNewWorld` 註冊 `AdvanceMonthFinish` 送武功、復用兩個容量擴張 Harmony patch。
5. **寫 frontend plugin**：抄 `SpellsFromTheWestFrontendPlugin`，只負責讀同樣的 YAML（讓前端 UI 也認得新項目）。
6. **包資料夾**：`MyMartialArtsMod/{Config.lua, Plugins/{Backend.dll, Frontend.dll, YamlDotNet.dll}, CombatSkills.yml, SpecialEffects.yml}`。
7. **`Config.lua`**：`ChangeConfig=true`、`HasArchive=true`、`BackendPlugins/FrontendPlugins` 各填一個 dll。

最大幾個地雷：
- 忘記在前後端**雙端**載 YAML → 前端不顯示或後端不認得 → 開戰崩。
- `EquipAddPropertyDict` 容量 patch 沒做 → 學技能時 array 越界。
- 特效 class 命名空間沒掛在 `GameData.Domains.SpecialEffect.*` 底下 → 反射查不到。
- `ClassName` YAML 寫的字串跟實際 namespace+class 對不上 → runtime throw `"Cannot find type '...'."`.
- `NewTemplateId` < `baseConfigCount` → `EnsureExtraTemplateId` 直接 throw。
- 在 `Initialize` 內呼叫 backend API → 此時還沒接通，會踩雷（見 §8）。

---

## 10. 對 Level 2 待釐清項的回應

| Level 2 待釐清 | 本份結果 |
|---|---|
| Backend plugin 載入點 | **仍未直接看到載入點**，但確認 backend mods 跑 `DomainManager.Mod.GetModDirectory(modIdStr)` / `GetSetting`，與前端 `ModManager.*` 平行。載入點推測在 `Encyclopedia.dll` 或反編譯之外的 backend assembly。Level 3 仍要追。 |
| `ModConfigDataManager.LoadModConfig` | 未在本 mod 出現，這條路（從 mod 攜帶 `Config/` 子資料夾覆寫 ConfigCells）顯然存在但 **沒被本 mod 使用**。本 mod 是直接呼叫 `ConfigData.AddExtraItem`，比 `Config/` 路徑更動態。 |
| ConfigDataModificationUtils | 同上，本 mod 沒走這條。 |
| YAML / 結構化資料 vs Lua | **本 mod 不用 Lua 跑資料**，用 YAML + YamlDotNet 載入後注入到 `ConfigData<T>.AddExtraItem`。`Config.lua` 只當 manifest 用。 |
| 事件系統整合 | 看到 `Events.RegisterHandler_*` 是 backend 戰鬥事件入口；`EventPackages` 那條（劇情事件）本 mod 沒用，仍是 Level 3 待辦。 |

---

## 11. 立即可用的衍生產出

把這份分析變成「動手做」要：

- 寫一份**繁中教學** `tutorial/add_new_combat_skill.md`，把 §9 的工作清單拆成手把手步驟（含 `.csproj` 設定、dotnet build 指令、本地 `Mod/` 放置）。
- 寫一份**屬性 ID 對照表** `details/property_ids.md`，把 `CombatSkills.yml` 標頭的 0-111 整理成 markdown 表，方便查找。
- 寫一份**Config.lua manifest 規格** `details/config_lua_schema.md`，補上 §2 與 Level 2 §2 沒對齊的細節（小寫 .lua、欄位順序等）。

留待 Level 3：
- backend plugin 載入點究竟在哪
- 完整 backend Events 清單（`GameData/DomainEvents/`）
- `EventPackages` 的劇情事件 mod 路線
- `ConfigCell <-> ConfigData` 之間 `_dataArray` 與 `AddExtraItem` 的 invariant
- 上傳到工坊的流程（Steam UGC）

---

## 12. 參考檔案

**Mod source（讀過）**：
- `~/repo/pas/projects/taiwu/MoreFactionCombatSkills/Config.lua`
- `~/repo/pas/projects/taiwu/MoreFactionCombatSkills/CombatSkills.yml`
- `~/repo/pas/projects/taiwu/MoreFactionCombatSkills/SpecialEffects.yml`
- `~/dev/taiwu-src/mods/MoreFactionCombatSkillsBackend/FeaturesBoundToFuyu/FeaturesBoundToFuyuPlugin.cs`
- `~/dev/taiwu-src/mods/MoreFactionCombatSkillsBackend/FeaturesBoundToFuyu/DataConfigAppender.cs`
- `~/dev/taiwu-src/mods/MoreFactionCombatSkillsBackend/FeaturesBoundToFuyu/DataConfigAppenderHelpers.cs`
- `~/dev/taiwu-src/mods/MoreFactionCombatSkillsBackend/GameData/Domains/SpecialEffect/MoreFactionCombatSkills/JinGangZong/Jianfa1.cs`
- `~/dev/taiwu-src/mods/MoreFactionCombatSkillsBackend/GameData/Domains/SpecialEffect/MoreFactionCombatSkills/JieQingMen/Qimen9.cs`
- `~/dev/taiwu-src/mods/MoreFactionCombatSkillsFrontend/FeaturesBoundToFuyu/SpellsFromTheWestFrontendPlugin.cs`

**遊戲源（待 Level 3 深挖）**：
- `~/dev/taiwu-src/Assembly-CSharp/Config/ConfigCells/` 全部
- `~/dev/taiwu-src/Assembly-CSharp/GameData/DomainEvents/` 全部
- `~/dev/taiwu-src/Assembly-CSharp/GameData/Domains/CombatSkill/`、`SpecialEffect/`、`Combat/`、`Taiwu/`
