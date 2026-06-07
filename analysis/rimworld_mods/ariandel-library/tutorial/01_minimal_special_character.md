# 教學：用 Ariandel Library 做一個最小「特殊角色」（純 XML）

目標：不寫任何 C#，做出一個會出現在「特殊角色面板」、姓名固定、不會真死、行為像 Boss 的具名角色。
依據：本庫 `User_Manual_26May2026.md` §3 + 官方範例 mod `Ariandel.UserGuideSCMF`（Workshop 3668177055）。**範例本身即為最佳模板**，本教學是其精簡版。

## 0. 前置

- mod 的 `About.xml` 設相依：
```xml
<modDependencies>
  <li>
    <packageId>Ariandel.AriandelLibrary</packageId>
    <displayName>Ariandel Library</displayName>
  </li>
</modDependencies>
<loadAfter><li>Ariandel.AriandelLibrary</li></loadAfter>
```

## 1. 定義角色分頁（SpecialPawnTabDef）

`Defs/AriandelLibrary.SpecialPawnTabDef/MyTab.xml`（資料夾名須等於 Def 全限定名）：
```xml
<?xml version="1.0" encoding="utf-8"?>
<Defs>
  <AriandelLibrary.SpecialPawnTabDef>
    <defName>MyMod_HeroTab</defName>
    <label>My Heroes</label>
    <order>10</order>
  </AriandelLibrary.SpecialPawnTabDef>
</Defs>
```
（也可直接沿用庫內建分頁如 `AL_Homosapien_Tab`，省略本步。）

## 2. 定義角色 PawnKindDef（核心：三段式 modExtensions）

`Defs/PawnKindDef/MyHero.xml`：
```xml
<?xml version="1.0" encoding="utf-8"?>
<Defs>
  <PawnKindDef ParentName="BasePawnKind">
    <defName>MyMod_HeroKind</defName>
    <label>hero</label>
    <race>Human</race>
    <defaultFactionType>OutlanderCivil</defaultFactionType>
    <combatPower>50</combatPower>

    <modExtensions>

      <!-- (A) 必填：固定身分（姓名/年齡/背景/特質/hediff 全鎖死） -->
      <li Class="AriandelLibrary.FixedIdentityExtension">
        <firstNameKey>MyHero.FirstName</firstNameKey>
        <lastNameKey>MyHero.LastName</lastNameKey>
        <nickNameKey>MyHero.Nick</nickNameKey>
        <genderMode>Female</genderMode>
        <forcedAgeYears>24</forcedAgeYears>
        <disableRandomTraits>true</disableRandomTraits>
        <extraForcedTraits>
          <li><def>Kind</def></li>
        </extraForcedTraits>
      </li>

      <!-- (B) 必填：登錄進特殊角色管理器 -->
      <li Class="AriandelLibrary.SpecialPawnExtension">
        <uniqueID>MyHero</uniqueID>            <!-- 全域唯一主鍵，勿重複 -->
        <tabDef>MyMod_HeroTab</tabDef>
        <iconPathRecruited>MyMod/UI/MyHero</iconPathRecruited>
        <iconPathLocked>AriandelLibrary/Icon/NotRecruited</iconPathLocked>
        <labelKey>MyHero.label</labelKey>
        <descKey>MyHero.desc</descKey>
        <order>1</order>
        <normalCooldownTicks>300000</normalCooldownTicks>     <!-- 召回冷卻，預設 5 天 -->
        <resurrectCooldownTicks>2700000</resurrectCooldownTicks> <!-- 復活冷卻，預設 45 天 -->
      </li>

      <!-- (C) 必填：死亡交給虛境召回（不會真死） -->
      <li Class="AriandelLibrary.AL_Kill_Manager_Extension" />

      <!-- (D) 選填：Boss 行為開關（按需挑） -->
      <li Class="AriandelLibrary.AL_RefuseMentalBreak_Extension">
        <blockMentalBreak>true</blockMentalBreak>
      </li>
      <li Class="AriandelLibrary.AL_FloatMenuBlocker_Extension">
        <blockRescue>true</blockRescue>
        <blockCapture>true</blockCapture>
        <blockArrest>true</blockArrest>
      </li>
      <li Class="AriandelLibrary.AL_AgeFreeze_Extension">
        <freezeBiologicalAge>true</freezeBiologicalAge>
      </li>
      <li Class="AriandelLibrary.AL_AzzyPregnancy_Extension">
        <replaceWithKind>Colonist</replaceWithKind>   <!-- 防生複製人 -->
      </li>

      <!-- (E) 選填：DLC gated 工具（無 DLC 自動忽略） -->
      <li Class="AriandelLibrary.Anomaly.AL_ObeliskDuplicationBlocker_Extension"
          MayRequire="Ludeon.RimWorld.Anomaly" />

    </modExtensions>
  </PawnKindDef>
</Defs>
```

## 3. 翻譯 Key

`Languages/English/Keyed/MyHero.xml`：
```xml
<LanguageData>
  <MyHero.FirstName>Aria</MyHero.FirstName>
  <MyHero.LastName>Ariandel</MyHero.LastName>
  <MyHero.Nick>Aria</MyHero.Nick>
  <MyHero.label>Aria</MyHero.label>
  <MyHero.desc>A named hero managed by the Special Character Manager.</MyHero.desc>
</LanguageData>
```

## 4. 劇情招募（選填，把「真身」綁進管理器）

`SpecialPawnExtension` 只宣告 kind 是特殊角色；要讓某個生成的實體成為「真身」，最簡單純 XML 路徑＝對話招募。

`Defs/AriandelLibrary.DialogueDef/MyHeroDialogue.xml`：
```xml
<Defs>
  <AriandelLibrary.DialogueDef>
    <defName>MyMod_HeroIntro</defName>
    <useTypewriter>true</useTypewriter>
    <lines>
      <li>
        <order>0</order>
        <speakerNameKey>MyHero.Nick</speakerNameKey>
        <text>I will fight by your side.</text>
        <options>
          <li>
            <label>Welcome aboard.</label>
            <optionComps>
              <li Class="AriandelLibrary.DialogueOptionCompProperty_RecruitDialogPawn" />
              <li Class="AriandelLibrary.DialogueOptionCompProperty_RegisterDialogPawn" />
              <li Class="AriandelLibrary.DialogueOptionCompProperty_CloseDialog">
                <notifyFinished>true</notifyFinished>
              </li>
            </optionComps>
          </li>
        </options>
      </li>
    </lines>
  </AriandelLibrary.DialogueDef>
</Defs>
```

`Defs/HediffDef/MyHeroTalk.xml`（掛在角色身上以提供右鍵對話入口）：
```xml
<Defs>
  <HediffDef>
    <defName>MyMod_HeroTalk</defName>
    <label>can talk</label>
    <comps>
      <li Class="AriandelLibrary.HediffCompProperties_AriandelDialogue">
        <dialogueDef>MyMod_HeroIntro</dialogueDef>
      </li>
    </comps>
  </HediffDef>
</Defs>
```
生成這個 pawn（NPC 狀態）時掛上 `MyMod_HeroTalk` hediff（例如透過 incident/quest 或 `FixedIdentityExtension.extraForcedHediffs`）→ 玩家右鍵 pawn 出現對話選項 → 選「Welcome aboard」→ 招募並註冊真身 → 對話完 hediff 自動移除。

## 5. 驗證

1. 啟用 Harmony + Ariandel Library + 你的 mod，**重啟遊戲**（註冊表在 StaticConstructorOnStartup/LongEvent 建立）。
2. 開發者模式 spawn `MyMod_HeroKind`，確認姓名固定、年齡正確。
3. 底部「特殊角色」按鈕 → 你的分頁應出現該角色頭像（未招募為鎖定圖示）。
4. 招募後讓其受致命傷 → 不應真死，而是進復活冷卻（面板顯示冷卻）。

## 何時要 C#？

以上全程零 C#。需要 C# 的情境見 `details/extension_points.md` §三（如全新能力效果、非對話的真身註冊、改框架行為）。
