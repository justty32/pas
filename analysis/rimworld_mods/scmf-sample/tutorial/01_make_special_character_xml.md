# 教學：純 XML 做一個你自己的特殊角色

以 SCMF Sample 的 Ingefrid 為藍本，做一個「具名、固定外觀、不死可召回」的特殊角色。**全程零 C#**。

前置：你的 mod 硬相依 `Ariandel.AriandelLibrary`，並以某個既有種族（本例沿用米莉拉 `Ancot.MiliraRace`，它提供 `Milira_PawnBase`、`MI_Milira_Tab` 分頁、HAR `Milira_Race`）為宿主。

## 步驟 0：mod 骨架與相依

`About/About.xml` 宣告硬相依與載入順序（照抄 `About/About.xml:10-28` 結構）：
- `modDependencies` → `Ariandel.AriandelLibrary`
- `loadAfter` → AriandelLibrary + 你要用的種族 mod

`LoadFolders.xml` 用 `IfModActive` 把種族專屬內容 gate 起來（`LoadFolders.xml:8-12`），讓缺種族 mod 時不報錯：
```xml
<li IfModActive="Ancot.MiliraRace">1.6/Mods/Ancot.MiliraRace</li>
```

## 步驟 1：背景故事（共用 Defs）

`1.6/Defs/BackStoryDef/MyChar_Backstory.xml`，型別 `AlienRace.AlienBackstoryDef`（藍本 `Backstory_Milira_Sample.xml`）。重點：給每個背景一個 `spawnCategories` tag（如 `MyChar_Adult_Tag`），稍後 PawnKind 用它篩選；`slot` 分 `Childhood`/`Adulthood`。

## 步驟 2：自訂特質（選用，共用 Defs）

`1.6/Defs/TraitDef/MyChar_Traits.xml`，型別 `TraitDef`，`commonality` 設極小（如 `0.000001`）避免被隨機角色抽到。可在 `modExtensions` 掛 AL 特質級工具（`Traits_Sample.xml:24-42`）：
```xml
<modExtensions>
  <li Class="AriandelLibrary.AL_NoSkillDecay_Extension"/>
  <li Class="AriandelLibrary.AL_LockSkill_Extension">
    <skill>Melee</skill><level>20</level><preventDecay>true</preventDecay>
  </li>
</modExtensions>
```

## 步驟 3：核心 — PawnKindDef（種族 gated 目錄）

`1.6/Mods/Ancot.MiliraRace/Defs/PawnkindDef/MyChar.xml`。從種族 base 繼承：`<PawnKindDef ParentName="Milira_PawnBase">`。
先填裝備/外觀層（`apparelRequired`、`weaponTags`、`forcedHairColor`、`backstoryFiltersOverride` 用步驟 1 的 tag），再進 `modExtensions` 掛框架三件套（必填）：

```xml
<modExtensions>
  <!-- 必填 1：固定身分 -->
  <li Class="AriandelLibrary.FixedIdentityExtension">
    <firstNameKey>MyChar_Name_First</firstNameKey>
    <lastNameKey>MyChar_Name_Last</lastNameKey>
    <nickNameKey>MyChar_Name_Nick</nickNameKey>
    <childhoodBackstoryDef>MyChar_Backstory_Child</childhoodBackstoryDef>
    <adulthoodBackstoryDef>MyChar_Backstory_Adult</adulthoodBackstoryDef>
    <forcedAgeYears>120</forcedAgeYears>
    <forcedChronologicalAgeYears>672</forcedChronologicalAgeYears>
    <forcedHeadTypeDef>MiliraHead4</forcedHeadTypeDef>
    <disableRandomTraits>true</disableRandomTraits>
    <extraForcedTraits>
      <li><def>Bloodlust</def></li>
      <li><def>MyChar_Trait</def></li>
    </extraForcedTraits>
    <extraForcedHediffs>
      <li><def>PsychicAmplifier</def><severity>1</severity><partDef>Brain</partDef><overwriteIfExists>true</overwriteIfExists></li>
    </extraForcedHediffs>
  </li>

  <!-- 必填 2：角色標籤（供面部動畫等回指） -->
  <li Class="AriandelLibrary.NPCKindTag"><npcTag>MyChar</npcTag></li>

  <!-- 必填 3：登錄進特殊角色管理器 -->
  <li Class="AriandelLibrary.SpecialPawnExtension">
    <uniqueID>MyChar</uniqueID>                 <!-- 全域唯一！ -->
    <tabDef>MI_Milira_Tab</tabDef>              <!-- 借用種族提供的分頁 -->
    <iconPathRecruited>MyMod/Icon/MyChar</iconPathRecruited>
    <iconBGPath>AriandelLibrary/Icon/BGTex/BGShroud</iconBGPath>
    <labelKey>SpecialPawnMyChar.label</labelKey>
    <descKey>SpecialPawnMyChar.desc</descKey>
    <normalCooldownTicks>300000</normalCooldownTicks>
    <resurrectCooldownTicks>2700000</resurrectCooldownTicks>
    <order>20</order>
  </li>

  <!-- 選用：行為改寫，按需加減（見 details/extension_points.md 全表） -->
  <li Class="AriandelLibrary.AL_Kill_Manager_Extension" />            <!-- 不死，改召回 -->
  <li Class="AriandelLibrary.AL_FloatMenuBlocker_Extension">
    <blockRescue>true</blockRescue><blockCapture>true</blockCapture><blockArrest>true</blockArrest>
  </li>
  <li Class="AriandelLibrary.AL_AzzyPregnancy_Extension"><replaceWithKind>Milira_Colonist</replaceWithKind></li>
  <li Class="AriandelLibrary.AL_TraitLock_Extension"><requiredTraits><li>MyChar_Trait</li></requiredTraits></li>
</modExtensions>
```

取捨提醒（對照 GuanJu）：要能被煉/被殺就**別加** `AL_Kill_Manager_Extension`；`AL_LockConsciousness_Extension` 只給 boss/灵体；Anomaly/RJW 類記得加 `MayRequire`。完整可選清單見 `../details/extension_points.md`。

## 步驟 4：語言檔（填入實際文字）

`1.6/Languages/English/Keyed/Name.xml`（藍本 `Name.xml`）——步驟 3 填的全是 key，這裡才是真名：
```xml
<MyChar_Name_First>...</MyChar_Name_First>
<SpecialPawnMyChar.label>...</SpecialPawnMyChar.label>
<SpecialPawnMyChar.desc>...</SpecialPawnMyChar.desc>
```

## 步驟 5：入手途徑 — ShroudOutcomeDef（種族 gated 目錄）

`.../Defs/AriandelLibrary.ShroudOutcomeDef/MyChar_Outcome.xml`（藍本 `ShroudOutcomeDef_Milira.xml`）：用內建 `workerClass=AriandelLibrary.ShroudOutcome_Generator`，`pawnList` 指向步驟 3 的 PawnKind，`shouldBeRegistered=true`、`isUnique=true`。這樣角色就能透過虛境儀式入手並自動登錄。

## 步驟 6（選用）：外觀差異與面部動畫

- HAR patch（`Patch_Ingefrid.xml` / `Patch_Alien_Milira.xml`）：用 `<Backstory><backstory>...</backstory></Backstory>` 條件，在種族 `bodyAddons` 裡**新增**專屬髮型/光環、並**隱藏**原本通用 addon。
- 面部動畫（gate 在 `1.6/Mods/Nals.FacialAnimation`）：`FacialAnimation.*TypeDef` 掛 `AriandelLibrary.FA.ModExtension_NPCFA` 的 `forNPC`，值＝步驟 3 的 `npcTag`，即可綁定專屬眼/嘴/膚。

## 驗收

- 啟用 AriandelLibrary + 對應種族 mod，遊戲不報紅。
- 透過虛境儀式可召出該角色，名字/外觀/特質固定。
- SCM 對應分頁出現角色頭像，可召回/復活。
- 全程未編譯任何 .dll。

## 全程零 C# 的界線

照本教學能做出「組裝既有積木」的特殊角色。若你想要**框架沒提供的新行為**（新主動技能效果、新行為改寫 extension、新 Shroud 結果邏輯、新 SCM 分頁），就超出純 XML，需寫 C#——見 `../details/extension_points.md` 末節。
