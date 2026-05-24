# 03 ─ 武功進化與變異（experiment #6）原始碼調查

> 日期：2026-05-24
> 範圍：為「中小門派」mod 的 **experiment #6（武功進化與變異）** 打底。回答：能否做出「五虎斷魂槍－水」這種變異武功？升降威力 / 改五行 該動哪些欄位？美術會不會跟著變？命名後綴怎麼掛？MVP 最省力路徑。
> 版本綁定：實裝版 **0.0.79.60**。
> 唯一事實來源 = 實裝 DLL（以 `ilspycmd -t` dump）。下文 **【實裝核對 ✅】**＝已對實裝 DLL 驗證；**⚠️**＝未對實裝核對（推測 / 待驗）。
> - 後端：`…/The Scroll Of Taiwu/Backend/GameData.dll`、`…/Backend/GameData.Shared.dll`
> - 前端：`…/The Scroll of Taiwu_Data/Managed/Assembly-CSharp.dll`（其旁亦帶一份 `GameData.Shared.dll`）
> 建立於：[`details/martial_arts_mod_anatomy.md`](../../details/martial_arts_mod_anatomy.md)（MySwordArt／更多门派功法 解剖）、[`details/sect_skill_favor_ui.md`](../../details/sect_skill_favor_ui.md)（武學樹 100% 讀 CombatSkill config）、[`answers/first_sword_art_design.md`](../../answers/first_sword_art_design.md)、[`progress.md`](../../progress.md)。

---

## 0. 一句話結論

**變異武功能做，且最省力路徑就是 MySwordArt 那條：把來源武功 `Duplicate(新TemplateId)` → 反射覆寫 `FiveElements` / `Grade` / 威力欄位 → `AddExtraItem` 注入為新 skill（前後端各一次）→ `TaiwuLearnCombatSkill` 送給玩家。** 不需要寫任何新特效類別、不需要碰戰鬥邏輯——MVP（升降威力＋改五行）100% 是 config 欄位層的事。
**美術不會因威力數值變；改五行只改圖示的「染色」、改品階改「品階外框」，圖示本體（sprite）由 `Icon` 字串欄位決定、不隨五行/品階變。**

---

## 1. `Config.CombatSkillItem` 欄位剖析（威力 / 五行 / 品階 / 修煉）

**權威來源【實裝核對 ✅】**：`ilspycmd -t Config.CombatSkillItem "…/Backend/GameData.Shared.dll"`。型別全名 **`Config.CombatSkillItem : ConfigItem<CombatSkillItem, short>`**（注意：不是舊源以為的 `GameData.Domains.CombatSkill.CombatSkillItem`，那個型別在實裝 DLL 不存在）。前端同名 `Config.CombatSkillItem` 來自前端 Managed 夾自己那份 `GameData.Shared.dll`【實裝核對 ✅】。

**所有欄位皆 `public readonly`**（含 ctor 三個：全參數版、無參預設版、`(short templateId, CombatSkillItem other)` 拷貝版）。`readonly` ⇒ 一般賦值改不了，但 **反射 `FieldInfo.SetValue` 可繞過**（MySwordArt 的 `DataConfigAppender.ApplyChanges` 就是這樣，`Shared/DataConfigAppender.cs:288-321`，`BindingFlags.NonPublic|Instance|Static|Public`）。

### 1.1 五行（唯一一欄）

| 欄位 | 型別 | 預設 | 說明 |
|---|---|---|---|
| **`FiveElements`** | `sbyte` | **5（Mix 混元）** | 五行屬性。值對照見下。 |

五行常數【實裝核對 ✅】`GameData.Domains.CombatSkill.FiveElementsType`（`GameData.Shared.dll`）：
`Metal=0 / Wood=1 / Water=2 / Fire=3 / Earth=4 / Mix=5`。
另含相生相剋表（`Countering/Countered/Producing/Produced`，各 `sbyte[5]`）—— 戰鬥中五行相剋傷害修正靠它。所以「改五行」會改變該武功在戰鬥中對不同五行對手的傷害關係（後端 `GameData.Domains.SpecialEffect.CombatSkill.Common.Assist.AddDamageByFiveElementsType` 等特效類存在【實裝核對 ✅ 類名存在】，⚠️ 詳細傷害公式未逐行追）。
→ **做「五虎斷魂槍－水」＝把 `FiveElements` 改成 2。** 就這一欄。

### 1.2 品階 / 階位（唯一一欄）

| 欄位 | 型別 | 預設 | 說明 |
|---|---|---|---|
| **`Grade`** | `sbyte` | 0 | 品階。範圍 **0–8（共 9 階）**——佐證：`Character.GetLearnedCombatSkillsFromSect(…, sbyte minGrade=0, sbyte maxGrade=8)`【實裝核對 ✅】。`GradeColors[Grade]` / `GradeBack[Grade]` 都按它索引。 |

> 「品階」與「五行」是兩個獨立欄位；MVP 的「升降」改的是 **威力**（§1.3），不是 `Grade`。但 `Grade` 同時驅動：UI 名稱顏色、品階外框圖示、品階文字（見 §2），改它＝外觀大改。MVP **不建議動 `Grade`**（會讓變異武功看起來「升階」而非「強化」，且品階是學習/破解門檻的隱含基準）。

### 1.3 威力（傷害 / 真氣 / 招式數值 / 命中段數）相關欄位群

戰鬥威力不是單一欄位，而是一組。逐欄性質（依欄位名 + 戰鬥域引用佐證）：

| 欄位 | 型別 | 性質 | 戰鬥引用佐證【實裝核對 ✅】 |
|---|---|---|---|
| `TotalHit` | `short` | **命中總段數**（多段攻擊的段數，越多總傷越高） | — |
| `InjuryPartAtkRateDistribution` | `sbyte[7]` | **7 個身體部位的傷害分配率** | `CombatDomain` L2049/L8308-8314 直接讀此欄分配各部位傷 |
| `PerHitDamageRateDistribution` | `sbyte[4]` | **每段傷害率分配** | — |
| `Penetrate` | `short` | **穿透**（無視部分防禦/閃避） | — |
| `Penetrations` / `PenetrationResists` | `OuterAndInnerShorts` | 內外功穿透 / 抗穿透 | — |
| `OuterDamageSteps` / `InnerDamageSteps` | `int[7]` | **外傷/內傷的傷害階（per body part）** | `CombatDomain` L4752-4770 與 `CombatCharacter` L4194/L5602 讀「傷害階集合」；⚠️ 該處讀的是「角色級彙整後」的 step，CombatSkillItem 自身的 `OuterDamageSteps` 是否直接灌入未逐行追，但語意明確＝傷害階基底 |
| `FatalDamageStep` / `MindDamageStep` | `int` | **致命傷 / 心魔傷 階** | `CombatDomain` L4655-4773 有 `CalcFatalDamageStep/CalcMindDamageStep` 彙整 |
| `FightBackDamage` / `BounceRateOfOuterInjury` / `BounceRateOfInnerInjury` | `short` | 反擊傷 / 內外傷反彈率 | — |
| `InnerRatio` / `BaseInnerRatio` / `InnerRatioChangeRange` | `short`/`sbyte`/`sbyte` | **內外功比重**（影響走內傷或外傷；威力分配相關） | — |
| `HasAtkAcupointEffect` / `HasAtkFlawEffect` | `bool` | 攻擊是否封穴 / 製造破綻（招式效果強度） | — |
| `Poisons` | `PoisonsAndLevels` | **下毒種類與等級**（特效強度） | — |
| `PrepareTotalProgress` | `int` | **出招準備總進度**（越大出招越慢；間接影響 DPS） | — |
| `CastSpeed` / `AttackSpeed` / `MoveSpeed` 等 | `short` | 各種速度 | — |
| `MobilityCost` / `BreathStanceTotalCost` / `WeaponDurableCost` / `WugCost` / `TrickCost` | 多型別 | **消耗類**（行動力/架式氣息/兵器耐久/武器/招式消耗——「真氣消耗」概念散在這些 cost 欄位） | — |
| `PropertyAddList` | `List<PropertyAndValue>` | **裝備該功時加的角色屬性**（被動加成；強度來源之一） | 注入時 `CombatSkillDomain.EquipAddPropertyDict` 要夠大，見 §3.3 |
| `ScoreBonusType` / `ScoreBonus` | `sbyte`/`short` | 評分加成 | — |

> 「真氣消耗」在太吾叫法散落：`TotalObtainableNeili`（可習得總內力，修煉相關，見 §1.4）、`MobilityCost`/各 cost 欄。MVP 的「升降威力」**只動 §1.3 的傷害類欄位**（最直觀：`TotalHit` / `Penetrate` / `OuterDamageSteps` / `InnerDamageSteps` / `PerHitDamageRateDistribution`），其餘 cost/speed 不動以保平衡。

### 1.4 熟練 / 修煉相關欄位

| 欄位 | 型別 | 性質 |
|---|---|---|
| `TotalObtainableNeili` | `short` | **修煉此功可得總內力**（練滿能拿多少內力） |
| `ObtainedNeiliPerLoop` | `short` | 每周天獲得內力 |
| `InheritAttainmentAdiitionRate` | `byte` | **造詣繼承加成率**（拼字 typo 是原版的，`InheritAttainment**Adiition**Rate`，反射 key 要照抄） |
| `PracticeType` | `sbyte` | 修煉類型 |
| `FiveElementChangePerLoop` / `DestTypeWhileLooping` / `TransferTypeWhileLooping` | `sbyte` | 周天運轉時的五行/轉換（內功循環機制） |
| `LoopBonusSkillList` / `ExtraNeiliAllocationProgress` | List/`sbyte[5]` | 周天額外加成 |
| `SkillBreakPlateId` → `SkillBreakPlate`（property，查 `Config.SkillBreakPlate.Instance[id]`） | sbyte→item | **破解盤**（武學「破解/精通」格子系統） |
| `UsingRequirement` | `List<PropertyAndValue>` | **裝備/使用門檻**（戰鬥中能否上陣使用，非學習門檻；見 §4 重點） |

### 1.5 美術 / 資源綁定欄位（見 §2 詳述）

`Icon`（圖示 sprite 名）、`AssetFileName`、`PrepareAnimation`/`CastAnimation`/`CastParticle`/`CastSoundEffect`、`CastPetAnimation`/`CastPetParticle`、`Defend*`/`FightBack*` 動畫粒子音效、`JumpAni`/`JumpParticle`、`PlayerCastBossSkill*` 系列、`DistanceWhenFourStepAnimation`。全是 `string` / `string[]`（資源名指向）。

### 1.6 名稱 / 描述

`Name`、`Desc`、`BreakStart`、`BreakEnd` —— 皆 `string`。**ctor 內以 `LocalStringManager.GetConfig("CombatSkill_language", <int index>)` 解析後存成最終字串**【實裝核對 ✅】。但拷貝 ctor（`Duplicate` 走的那個）是直接 `Name = other.Name` 複製字串。**mod 注入時用反射把 `Name` 欄位直接寫成成品字串**（繞過語言檔），這正是 §5 命名後綴的根據。

---

## 2. 美術綁定：哪些欄位一改、圖示/特效會跟著變

**權威來源【實裝核對 ✅】**：前端 `CombatSkillView.SetData(...)`（`Assembly-CSharp.dll`，`ilspycmd -t CombatSkillView`）。武學樹每格的小元件就是 `CombatSkillView`（`UI_CombatSkillTree.RefreshSkillItem` 借用它）。關鍵幾行：

```csharp
CombatSkillItem combatSkillItem = CombatSkill.Instance[skillData.TemplateId];
CGet<TextMeshProUGUI>("Name").text = combatSkillItem.Name.SetColor(Colors.Instance.GradeColors[combatSkillItem.Grade]);   // 名稱顏色← Grade
CGet<CImage>("GradeBack").SetSprite(ItemView.GetGradeIcon(combatSkillItem.Grade));                                       // 品階外框 sprite← Grade
CGet<TextMeshProUGUI>("Grade").text = LocalStringManager.Get($"LK_ShortGrade_{combatSkillItem.Grade}");                  // 品階文字← Grade
CGet<CImage>("SectType").SetSprite(EquipTypeImg[combatSkillItem.EquipType], autoNativeSize:true);                        // 攻/守/輕功背景← EquipType
CGet<CImage>("SkillType").SetSprite(combatSkillItem.Icon, autoNativeSize:true);                                          // ★ 圖示本體 sprite← Icon 字串
CGet<CImage>("SkillType").SetColor(Colors.Instance.FiveElementsColors[combatSkillItem.FiveElements]);                    // ★ 圖示「染色」← FiveElements
```

對照「設計推測」修正後的**美術綁定真相**：

| 改哪個欄位 | 美術會變嗎 | 怎麼變（精確） |
|---|---|---|
| **威力數值**（`TotalHit`/`Penetrate`/`OuterDamageSteps`/`PerHitDamageRateDistribution`…） | **不變** ✅（符合推測） | 完全不碰任何美術；圖示/外框/動畫/粒子全不動。 |
| **`FiveElements`（五行）** | **變，但只是「染色」** | `SkillType` 圖示的 **tint color** 改成 `FiveElementsColors[該五行]`（金/木/水/火/土各一色）。**圖示 sprite 本身不換**——所以「五虎斷魂槍－水」會是原槍法圖示染成水色。前端另有 `CombatSkillView.FiveElementImg`（`string[6]` 對應 6 五行的 neili sprite）【實裝核對 ✅】，但 `SetData` 裡 `FiveElementsType` 那個 CImage 被 `.enabled=false` 關掉，故五行對圖示的可見影響＝**只有染色**。 |
| **`Grade`（品階）** | **變** | 名稱顏色（`GradeColors[Grade]`）＋ 品階外框（`ItemView.GetGradeIcon`→`ItemGradeBack[Grade]`）＋ 品階文字（`LK_ShortGrade_{Grade}`）。 |
| **`Icon`（字串）** | **變（直接換 sprite）** | 圖示本體就是這個字串指向的 sprite。要徹底換圖只能改它。 |
| **`EquipType`** | 變 | 攻/守/輕功/其他 的底框（`EquipTypeImg`）。 |
| **戰鬥特效美術**（`CastParticle`/`CastAnimation`/`CastSoundEffect`…） | 不變（除非你改這些字串） | 變異武功若沿用來源的這些字串欄位，動畫/粒子/音效＝來源原樣。 |

**結論修正**：原設計推測「五行改→美術變、階位改→美術變、威力改→美術不變」**方向正確**，但更精確是：
- 五行改 → **只圖示染色變**（不換 sprite）；
- 階位改 → 品階外框/名色/品階字變；
- 威力改 → 美術完全不變；
- 真正換圖示 sprite 只能改 `Icon` 字串。

→ 對 experiment #6「五虎斷魂槍－水」這種變異，**不需要任何美術資源**：沿用來源 `Icon` + 把 `FiveElements=2`，遊戲自動把圖示染成水色，視覺上就讀得出「這是水屬性版」。零美術成本。

---

## 3. runtime 複製既有武功 → 改數值/五行：必須以新 TemplateId 注入

### 3.1 結論：要做變異武功，**必須注入為「新 TemplateId」的 extra item**（前後端各一次）

**權威證據【實裝核對 ✅】**：`Config.Common.ConfigData<T,K>`（`GameData.Shared.dll`，`ilspycmd -t "Config.Common.ConfigData\`2"`）：

```csharp
public int Count => _dataArray?.Count ?? 0;
public int CountWithExtra => Count + _extraDataMap.Count;

public int AddExtraItem(string identifier, string refName, object configItem) {
    int templateId = ((T)configItem).GetTemplateId();
    if (templateId < _dataArray.Count) throw ...;           // ★ 新 id 必須 >= 原表大小
    if (_extraDataMap.ContainsKey(templateId)) throw ...;
    if (_refNameMap.TryGetValue(refName, ...)) throw ...;
    _refNameMap.Add(refName, templateId);
    _extraDataMap.Add(templateId, val);                     // ★ 存進「額外表」
    return templateId;
}

public int AddOrModifyItem(T configItem) {                  // ← 另一條路（見 3.2）
    int templateId = configItem.GetTemplateId();
    if (templateId < _dataArray.Count) { _dataArray[templateId] = configItem; return templateId; }  // ★ 就地覆寫原表
    if (templateId == -1) { _dataArray.Add(configItem.Duplicate(_dataArray.Count)); ... }
    throw ...;
}

public T GetItem(TKey id) {                                 // 先查 _dataArray，再查 _extraDataMap
    if (num < _dataArray.Count) return _dataArray[num];
    if (_extraDataMap.TryGetValue(num, out var v)) return v;
    return null;
}
IEnumerator<T> GetEnumerator() {                            // ★ 列舉/Iterate 涵蓋 _dataArray + _extraDataMap
    foreach (var item in _dataArray) yield return item;
    foreach (var v in _extraDataMap.Values) yield return v;
}
```

要點：
1. **`AddExtraItem` 強制 `新 id >= _dataArray.Count`**（原版表大小）——所以變異武功只能用全新的、超出原表的 TemplateId。**不可拿既有 id 注入。** MySwordArt 用 4500、參考 mod 用 4100+，4000+ 為安全區。
2. **`Iterate`/列舉會走到 `_extraDataMap`**——所以注入的新 skill **會被武學樹的 `CombatSkill.Instance.Iterate(item => item.SectId==...)` 看到並顯示**（佐證 [`sect_skill_favor_ui.md` C-2/C-4](../../details/sect_skill_favor_ui.md)：武學樹 100% data-driven）。
3. **前後端各一份 `CombatSkill.Instance` 單例**（兩邊各自的 `GameData.Shared.dll`）——所以注入要在 backend plugin 與 frontend plugin **各做一次**（[`progress.md`](../../progress.md) 通則：AddExtraItem 前後端各一次；本調查再次證實）。

### 3.2 能否「就地改既有 CombatSkill」？能，但不該用於變異

`AddOrModifyItem(item)` 當 `templateId < _dataArray.Count` 時會 `_dataArray[templateId] = item` **就地覆寫原版**【實裝核對 ✅】。技術上可把「五虎斷魂槍」原條目換掉。但：
- 這是**全域**改動——所有 NPC、所有既有存檔裡那把槍法全部一起變，無法做「某人的那把變異了、別人的沒變」。
- 違反 experiment #6 的「個別武功進化/變異」語意。
→ **變異武功一律走 `AddExtraItem` 注入新 id**，不要用 `AddOrModifyItem`。`AddOrModifyItem` 只適合「想把原版某武功整體 rebalance」這種 mod。

### 3.3 具體步驟（以 MySwordArt 為範本，「複製某既有 skill → 改威力/五行 → 注入新 skill → 可學/可顯示」）

MySwordArt 已實證可跑（[`first_sword_art_design.md`](../../answers/first_sword_art_design.md)：實機技能顯示/可學/戰鬥特效全綠）。變異武功就是把它的 YAML 換成「克隆來源 = 想變異的那把武功」：

1. **選來源**：例如「五虎斷魂槍」的原版 TemplateId（⚠️ 確切 id 未查；可在 runtime `CombatSkill.Instance.Iterate` 找 `Name.Contains("五虎斷魂槍")`，或翻 config）。
2. **YAML（`CombatSkills.yml`）**——MySwordArt 的 `DataConfigAppender` 已支援：頂層 key = 新 id（如 `4600`）、`TemplateId:` = 來源 id、其餘欄位覆寫：
   ```yaml
   4600:
    TemplateId: <五虎斷魂槍原id>     # 克隆來源
    Name: "五虎斷魂槍－水"            # 直接成品字串（見 §5）
    FiveElements: 2                  # 改五行＝水
    # 升威力範例（升級）：
    TotalHit: 220                    # 原值×1.x
    Penetrate: 800
    # 降威力範例（降級）：把上面數值改小即可
   ```
3. **特效（`SpecialEffects.yml`）**：變異武功**沿用來源的特效**——`DirectEffectID`/`ReverseEffectID` 不覆寫即繼承來源。**experiment #6 MVP 不需要寫新特效類別。**（若要加變異獨有特效才需 §7 of `martial_arts_mod_anatomy.md` 那套 ClassName 反射機制。）
4. **注入**：呼 `DataConfigAppender.LoadCombatSkillsFromYamlFile(path)`——backend plugin 與 frontend plugin **各跑一次**（[`martial_arts_mod_anatomy.md` §3](../../details/martial_arts_mod_anatomy.md)）。
5. **送給玩家**：`DomainManager.Taiwu.TaiwuLearnCombatSkill(ctx, (short)4600, ushort.MaxValue)`（過月鉤 `AdvanceMonthFinish` 內，[`martial_arts_mod_anatomy.md` §8](../../details/martial_arts_mod_anatomy.md)；或聊天選項回呼內）。
6. **容量 patch（必做）**：`CombatSkillDomain.InitializeOnInitializeGameDataModule` 的 `EquipAddPropertyDict` 必須放大到容得下新 id（MySwordArt 已抄這個 Harmony patch，寫死 32768；[`martial_arts_mod_anatomy.md` §6.1](../../details/martial_arts_mod_anatomy.md)）。

### 3.4 踩雷清單（變異武功特有 + 既有）

- **新 id 必須 >= 原表 Count**，否則 `AddExtraItem` throw（§3.1）。動態生成變異時要維護一個遞增 id 池（如從 5000 起跳，每變異一次 +1），且**跨存檔要持久化這個 id↔變異定義映射**（`HasArchive=true`，否則重載存檔後該 id 對應的 extra item 不存在 → 玩家身上的技能 id 變孤兒 → 顯示/戰鬥查 `GetItem` 回 null）。⚠️ 這是動態變異比 MySwordArt（固定一把）**多出來的最大工程**：MySwordArt 每次開遊戲都重注入同一批固定 id，動態變異則 id 是運行期決定的，必須存檔同步。
- **前後端不同步**＝前端顯示不出 / 後端戰鬥 `GetItem` 回 null 崩。
- `EquipAddPropertyDict` 容量沒放大 → 學技能時 array 越界（§3.3 step 6）。
- 反射覆寫的欄位名要**精確**（含原版 typo `InheritAttainmentAdiitionRate`）。
- `SkillBreakGridList`：MySwordArt 的 `DataConfigAppenderHelpers.AddCombatSkillItemToConfig` 會替新 skill 補一筆破解格列表（從同 Grade+Type 原版抓參考）；變異武功若改了 `Grade` 要注意這步抓不抓得到參考（MVP 不改 Grade 就無此問題）。⚠️ 此細節未對實裝逐行核（MySwordArt 已實機過 ⇒ 機制可信）。

---

## 4. MVP 可行性評估（升降威力 ＋ 五行變化；走聊天選項）

使用者拍板 MVP：① 升級/降級＝改威力；② 五行變化。門檻＝**修改者造詣須高出該功法一階**，消耗大量歷練與時間（**五行變化無造詣限制**）。全程走聊天選項。

### 4.1 可行性：高。全部落在 config 欄位層，零戰鬥邏輯、零美術。

| MVP 項 | 改哪些欄位 | 美術影響 | 難度 |
|---|---|---|---|
| ① 升級威力 | §1.3 傷害群放大（建議只動 `TotalHit`、`Penetrate`、`PerHitDamageRateDistribution`、`OuterDamageSteps`/`InnerDamageSteps`） | 無 | 低 |
| ① 降級威力 | 同上縮小 | 無 | 低 |
| ② 五行變化 | `FiveElements`（0–5 任一） | **只圖示染色**（自動，零成本） | 極低 |

### 4.2 最省力實作（強烈建議）

**做法 A（推薦）＝「升威力 / 改五行」每次都產出一個新 extra skill，把玩家身上舊的換成新的。**
1. 玩家選聊天選項「進化此武功」。
2. mod 讀玩家身上某 learned skill 的 TemplateId → 取 `CombatSkill.Instance[id]` 當來源。
3. `Duplicate(新id)` + 反射改 `FiveElements` 或威力欄位（複用 MySwordArt 的 `DataConfigAppender`／或直接呼 `ConfigItem.Duplicate` + 反射）。
4. `AddExtraItem` 前後端各注入（§3）。
5. **移除舊 skill、學新 skill**：`DomainManager.Character.LearnCombatSkill(ctx, charId, 新id, readingState)`（保留原修煉進度 readingState 可選）。⚠️ 「移除某 learned skill」的 API 未在本次調查確認（`TaiwuLearnCombatSkill` 只加不刪）——待釐清（§8）。若無乾淨移除 API，退路是讓變異版與原版並存（玩家自己不用舊的）。

**門檻檢查（造詣高出一階）＝由 mod 自己算，遊戲不幫你擋**：
- 學習 API `TaiwuLearnCombatSkill` **不檢查 `UsingRequirement`**【實裝核對 ✅，body 見下】——它只是 `DomainManager.Character.LearnCombatSkill(...)` + 處理 NotLearn 進度。`UsingRequirement` 是**戰鬥中能否上陣使用**的門檻，不是學習門檻。
  ```csharp
  public void TaiwuLearnCombatSkill(DataContext context, short skillTemplateId, ushort readingState=0) {
      DomainManager.Character.LearnCombatSkill(context, _taiwuCharId, skillTemplateId, readingState);
      if (_notLearnCombatSkillReadingProgress.ContainsKey(skillTemplateId)) { ...搬進度... }
  }
  ```
- 所以「造詣須高出該功法一階」要**在聊天選項的條件/回呼裡自己判斷**：
  - 取修改者該武功 `Type` 的造詣：`Character.GetCombatSkillAttainments()`（回 `ref CombatSkillShorts`，按武學大類索引）【實裝核對 ✅，`Character` L20668】，或 `Character.GetPropertyValue(ECharacterPropertyReferencedType type)`【實裝核對 ✅，L3350】用造詣 property id（如劍法造詣=87，見 [`progress.md`](../../progress.md)/property_ids）。
  - 與來源 skill 的 `Grade` 比較。⚠️ 「造詣數值 → 對應第幾階」的換算表未本次確認（造詣是 0–N 的 short，階是 0–8）——需查造詣→可修煉階位的對照（GlobalConfig 內某 threshold 陣列，待釐清 §8）。MVP 可先用**保守規則**：要求造詣 >= 某固定門檻 × (Grade+2) 之類，先跑起來再調。
- **五行變化無造詣限制**：聊天選項對「改五行」分支不掛造詣條件即可。
- **消耗大量歷練與時間**：歷練（經驗）扣除＝呼對應 domain 扣資源 API（⚠️ 確切 API 未查，但 MonthlyAiDemo 已證實能改太吾資源，[`progress.md`](../../progress.md)）；「時間」＝可用「過月後才生效」或扣行動點/月數模擬。這兩者是數值消耗，非結構難點。

**做法 B（不推薦給 MVP）＝就地 `AddOrModifyItem` 改原版**：全域污染，否決（§3.2）。

### 4.3 走聊天選項的接點

聊天選項框架（事件/對話選項）已在前面實驗涵蓋（[`design_vision.md` 底層接點表](../design_vision.md)、AbyssManualEvent 手寫事件已實證）。MVP 把「進化武功」掛成一個聊天選項：
- 選項**顯示條件**：身上有可進化的武功 + （升威力分支）造詣達標。
- 選項**回呼**：執行 §4.2 的 Duplicate→改欄位→注入→換 skill + 扣歷練。
- ⚠️ 聊天選項回呼裡能否安全做 `AddExtraItem`（runtime 注入，非載入期）＝本調查未實證。MySwordArt 是在 plugin `Initialize`/載入期注入固定批次；**運行期動態注入**理論上可行（ConfigData 是活物件、`_extraDataMap` 隨時可加），但要注意：①前後端都要注入（聊天選項回呼跑在哪端？對話/事件邏輯多在後端，前端要另想辦法同步，可能要發 domain method 或前端也跑一份注入）；②存檔持久化（§3.4）。**這是 MVP 最大的未知風險點，列為首要待驗。**

---

## 5. 命名後綴（－水／－奇／－禪）怎麼掛

**結論：直接把成品字串寫進 `Name` 欄位即可，不需要動任何語言檔。**

依據【實裝核對 ✅】：
- `CombatSkillItem.Name` 是 `string`，雖然全參數 ctor 走 `LocalStringManager.GetConfig("CombatSkill_language", <int>)`，但**拷貝 ctor（`Duplicate` 用的）直接 `Name = other.Name` 複製字串**，而 MySwordArt 的 `DataConfigAppender.ApplyChanges` 用反射 `field.SetValue` **把 `Name` 整個覆寫成 YAML 給的字串**（`Shared/DataConfigAppender.cs:310-314`）。
- 前端顯示直接讀 `combatSkillItem.Name`（§2，`CombatSkillView.SetData`），不再過語言檔。

所以「五虎斷魂槍－水」的後綴：
- **MVP 最省力**＝在產生變異 item 時把 `Name` 設成 `來源Name + 後綴`。例如 `源.Name + "－水"`（水）、`+ "－奇"`、`+ "－禪"`。後綴對照表自己在 mod 內維護（五行→「－金/木/水/火/土」，或自訂風格詞）。
- **編碼**：`Name` 走 YAML / 反射字串，**由後端 net6 以 UTF-8 讀**（[`progress.md`](../../progress.md) 編碼通則：YAML/事件語言檔 UTF-8）。**只有 `Config.lua` 的 `Title`（mod 列表顯示名）才是前端 GBK** —— 那是 mod 名稱亂碼問題（[`first_sword_art_design.md`](../../answers/first_sword_art_design.md) 提到的外觀層），**與武功 `Name` 後綴無關**。所以掛「－水」不會踩 GBK 雷。
- **多語**：若要英文後綴，沿用 MySwordArt 的 `44Name`/`86Name` 本地化前綴機制（`DataConfigAppender.TryParseLocalizedMemberKey`，`Shared/DataConfigAppender.cs:235-257`）：`44Name: "Five-Tiger Soul-Breaking Spear (Water)"`。MVP 可先只做中文。

---

## 6. CombatSkill 關鍵欄位對照表（速查）

| 類別 | 欄位 | 型別 | MVP 要動嗎 | 美術影響 |
|---|---|---|---|---|
| 五行 | `FiveElements` | sbyte (Metal0/Wood1/Water2/Fire3/Earth4/Mix5) | ✅ 改 | 圖示染色 |
| 品階 | `Grade` | sbyte (0–8) | ❌ 不動 | 名色+品階框 |
| 威力·段數 | `TotalHit` | short | ✅ 升降 | 無 |
| 威力·穿透 | `Penetrate` | short | ✅ 升降 | 無 |
| 威力·分配 | `PerHitDamageRateDistribution` | sbyte[4] | 可選 | 無 |
| 威力·部位分配 | `InjuryPartAtkRateDistribution` | sbyte[7] | 可選 | 無 |
| 威力·傷害階 | `OuterDamageSteps`/`InnerDamageSteps` | int[7] | 可選 | 無 |
| 修煉 | `TotalObtainableNeili`/`InheritAttainmentAdiitionRate`/`PracticeType`/`SkillBreakPlateId` | 多 | ❌ 沿用 | 無 |
| 使用門檻 | `UsingRequirement` | List<PropertyAndValue> | ❌ 沿用 | 無（且非學習門檻，是戰鬥上陣門檻） |
| 名稱 | `Name`/`Desc` | string | ✅ 加後綴 | 名色（隨 Grade） |
| 美術·圖示 | `Icon` | string | ❌ 沿用 | 圖示本體 sprite |
| 美術·特效 | `CastParticle`/`CastAnimation`/`CastSoundEffect`… | string | ❌ 沿用 | 戰鬥動畫/粒子/音效 |

---

## 7. 美術綁定總結圖（一句話）

> **威力＝純數值（美術全不變）；五行＝圖示自動染色（零美術成本，肉眼可辨）；品階＝名色+外框（MVP 不動）；要換圖示本體只能改 `Icon` 字串。** 變異武功（五虎斷魂槍－水）只需 `FiveElements=2` + `Name` 加後綴 + 威力數值調整，**完全不碰任何美術資源**。

---

## 8. 待釐清 / 未對實裝核對清單

| # | 項目 | 狀態 | 影響 |
|---|---|---|---|
| 1 | **運行期（聊天選項回呼內）動態 `AddExtraItem` 注入**是否安全、前後端如何同步、是否要發 domain method | ⚠️ 未實證（MySwordArt 是載入期固定批次注入） | **MVP 最大風險**，首要實機驗 |
| 2 | **變異 skill 的 id↔定義 跨存檔持久化**（`HasArchive`，重載後 extra item 重建） | ⚠️ 未設計 | 動態變異比固定 mod 多出的工程，不做會孤兒崩 |
| 3 | **「移除/替換」玩家身上某 learned skill** 的乾淨 API | ⚠️ 未確認（`TaiwuLearnCombatSkill` 只加） | 影響「進化後舊版消失」體驗；無則並存 |
| 4 | **造詣數值 → 階位** 換算（造詣 short 對應第幾階，以判「高出一階」） | ⚠️ 未查（疑在 GlobalConfig threshold 陣列） | MVP 門檻判定精確度；可先用保守規則跑 |
| 5 | 五行相剋實際**傷害公式**（`FiveElementsType.Countering` 等如何進傷害計算） | ⚠️ 只確認類名/表存在，未追公式 | 改五行的戰鬥實際強弱（不影響「能不能做」） |
| 6 | CombatSkillItem 的 `OuterDamageSteps`/`InnerDamageSteps` 是否**直接**灌入角色傷害階 | ⚠️ 戰鬥域讀的是角色級彙整值，來源關係未逐行追 | 升威力時選哪欄最有效（先用 `TotalHit`/`Penetrate` 最穩） |
| 7 | 「五虎斷魂槍」**原版 TemplateId** | ⚠️ 未查 | 實作時 runtime `Iterate` 找名或翻 config 即得 |
| 8 | `SkillBreakGridList` 對改了 `Grade` 的新 skill 是否抓得到參考 | ⚠️ 未逐行核（MVP 不改 Grade 則無關） | 僅當未來要做「升階」變異才需驗 |

---

## 9. 已核對之實裝來源（本次 ilspycmd dump）

- 【實裝核對 ✅】`Config.CombatSkillItem`（全欄位 + 三 ctor + `Duplicate`）— `Backend/GameData.Shared.dll`
- 【實裝核對 ✅】`Config.CombatSkillItem` 同名存在於前端 — `…_Data/Managed/GameData.Shared.dll`
- 【實裝核對 ✅】`GameData.Domains.CombatSkill.FiveElementsType`（五行常數+相剋表）— `Backend/GameData.Shared.dll`
- 【實裝核對 ✅】`Config.Common.ConfigData\`2`（`AddExtraItem`/`AddOrModifyItem`/`GetItem`/列舉涵蓋 extra）— `Backend/GameData.Shared.dll`
- 【實裝核對 ✅】`CombatSkillView.SetData`（美術綁定：`Icon`=sprite、`FiveElements`=染色、`Grade`=框/名色）+ `FiveElementImg[6]`/`SectImg[16]`/`EquipTypeImg` — `…/Managed/Assembly-CSharp.dll`
- 【實裝核對 ✅】`ItemView.GetGradeIcon`（Grade→`ItemGradeBack[grade]`）、`Colors.GradeColors`/`FiveElementsColors` — `…/Managed/Assembly-CSharp.dll`
- 【實裝核對 ✅】`TaiwuDomain.TaiwuLearnCombatSkill`（不檢查 UsingRequirement）、`Character.GetPropertyValue`/`GetCombatSkillAttainments`/`GetLearnedCombatSkillsFromSect(minGrade0,maxGrade8)` — `Backend/GameData.dll`
- 【實裝核對 ✅】`CombatDomain` 對 `InjuryPartAtkRateDistribution`（L2049/L8308）、傷害階集合（L4752-4773）的引用 — `Backend/GameData.dll`
- 【既有調查／已實證】MySwordArt `Shared/DataConfigAppender.cs`（反射覆寫 readonly 欄位、YAML 克隆注入）、`martial_arts_mod_anatomy.md`（容量 patch / 過月送武功 / 雙端注入）、`sect_skill_favor_ui.md`（武學樹 100% data-driven）。
