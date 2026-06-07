# World Tech Level 擴充接點（純 XML vs 必須 C#）

> 本 mod 是「為了被資料擴充而生」的過濾框架。**幾乎所有實用擴充都是純 XML**：寫 `TechLevelConfigDef` 給任意內容 mod 的 def 標科技等級／替代物。改過濾邏輯本身才需 C#（且要懂 LunarFramework）。

## 純 XML vs 必須 C# 二分表

| 需求 | 純 XML？ | 接點 / 說明 |
|---|---|---|
| 讓本 mod 認得某內容 mod 的物品/研究/派系… 的科技等級 | ✅ 純 XML | 新增 `WorldTechLevel.TechLevelConfigDef`，設 `defType` ＋ `entries`（每筆 defName/techLevel/priority）。這是**最主要、作者預期的擴充方式**（相容補丁） |
| 被過濾時用低科技替代物頂替 | ✅ 純 XML | `TechLevelConfigDef.alternatives`（`targets`/`categories` → 候選 `options[{defName, weight}]`） |
| 純文字內容（背景故事等）按關鍵字推級 | ✅ 純 XML | `TechLevelConfigDef.storyFilters`（`strongTerms`/`weakTerms` → `techLevel`） |
| 條件式等級（看裝了哪些 mod / 哪個 DLC / 是否地外） | ✅ 純 XML | `LevelEntry` 的 `ifModPresent` / `unlessModPresent` / `contentPack` / `offworld` 欄位 |
| 場景預設等級 | ✅ 純 XML | `ScenPartDef WorldTechLevel`（已附），場景作者可放進自訂場景 |
| 過濾「演算法／時機」（哪些生成環節被攔） | ❌ C# | `WorldTechLevel.Patches.*` 約 40 個 Harmony patch；新攔截點要寫 patch |
| 替代物的選取邏輯、建材替換規則 | ❌ C# | `ReplacementUtility` / `BuildingMaterialUtility` |
| 新增一個「科技等級」本身 | ❌ 不可（原版列舉） | `TechLevel` 是原版 enum（Neolithic…Archotech），不可加 |

## TechLevelConfigDef 結構（純 XML）

```
TechLevelConfigDef (defName, defType=要標註的 Def 型別如 ThingDef)
├─ entries: List<LevelEntry>
│   └─ LevelEntry { defName; techLevel; priority;
│                   ifModPresent; unlessModPresent; contentPack; offworld }
├─ alternatives: List<AlternativesEntry>
│   └─ { targets[]; categories[]; options:List<{defName; weight}> }
└─ storyFilters: List<StoryFilterEntry>
    └─ { strongTerms[]; weakTerms[]; techLevel }
```

> `priority`：多筆來源衝突時的覆寫優先序（本 mod 自帶的原版內容多用 `-1`，讓相容補丁可用更高 priority 覆蓋）。

## 最省力衍生：給某內容 mod 寫科技等級相容補丁（純 XML）

```xml
<WorldTechLevel.TechLevelConfigDef>
  <defName>WTL_MyContentMod_Things</defName>
  <defType>ThingDef</defType>
  <entries>
    <li><defName>MyMod_LaserRifle</defName><techLevel>Spacer</techLevel></li>
    <li><defName>MyMod_IronSword</defName><techLevel>Medieval</techLevel></li>
  </entries>
  <alternatives>
    <li>
      <targets><li>MyMod_LaserRifle</li></targets>
      <options><li><defName>Gun_BoltActionRifle</defName><weight>1</weight></li></options>
    </li>
  </alternatives>
</WorldTechLevel.TechLevelConfigDef>
```

可用 `<li ... MayRequire="author.mod"/>` 或 `LevelEntry.ifModPresent` 讓補丁只在該 mod 存在時生效。

## 結論導向

- **此 mod 是本群組中「純 XML 擴充性最高」者之一**：整個對外介面就是 `TechLevelConfigDef`。做任何「為 X 內容 mod 補科技等級」的衍生，零 C#。
- 只有想擴大「過濾涵蓋面」（攔新的生成環節）或改替代演算法才碰 C#，且需熟悉 LunarFramework 載入機制。
