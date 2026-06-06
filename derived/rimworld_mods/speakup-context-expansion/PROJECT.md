# SpeakUp 情境擴充（speakup-context-expansion）

> Create 模式衍生小 mod。在 **SpeakUp 畅所欲言**（`cn.speakup.ttyet`）之上，
> 走「**新增情境變數（C# 改碼）**」路線，新增 3 個 vanilla SpeakUp 未覆蓋的
> **殖民地／地圖層級**情境變數＋對應中文台詞。

## 衍生目標

讓殖民者的動態閒聊能反映「比個人想法更大的局勢」。SpeakUp 原生情境變數幾乎都是
**單一 pawn 視角**（心情、想法、技能、傷病、穿戴…）與**地圖環境**（天氣、溫度、時間）。
缺少「整個殖民地此刻處於什麼處境」這一層。本擴充補上三條：

| # | 情境 | 新關鍵字 | 資料來源（RimWorld API，已驗證存在） |
|---|---|---|---|
| 1 | 正在戰鬥／受威脅 | `COLONY_DANGER`（none/low/high）、`INITIATOR_drafted`/`RECIPIENT_drafted`（是/否） | `Map.dangerWatcher.DangerRating`（`RimWorld.StoryDanger`）、`Pawn.Drafted` |
| 2 | 殖民地糧食危機 | `COLONY_FOOD_DAYS`（數值：可吃天數） | `Map.resourceCounter.TotalHumanEdibleNutrition`、`Map.mapPawns.FreeColonistsCount` |
| 3 | 近期殖民者死亡 | `COLONY_DAYS_SINCE_DEATH`（數值：天；無死亡時關鍵字不發出） | 自建 `ColonyDeathTracker`（GameComponent）＋ Postfix `Pawn.Kill` 記錄 tick |

### 「是否已被 vanilla SpeakUp 覆蓋」的查證結論

逐一掃過 `SpeakUp/ExtraGrammarUtility.cs` 與 `1.6/Defs`、`1.6/Patches` 後確認：

- **戰鬥/威脅**：`ExtraGrammarUtility` 完全沒有 raid/drafted/hostile/threat 等地圖層級判斷；
  XML 內出現的 `threat` 只是侮辱對話裡的一段**文字子規則**（`1.6/Defs/Interactions.xml:1934`），
  不是可判斷的情境變數。→ **未覆蓋，採用**。
- **糧食**：既有食物相關全部走**個人 mood thought**（`INITIATOR_thoughtDefName==NeedFood`、
  `INITIATOR_thoughtLabel==饥饿` 等，見 `1.6/Patches/z_add_chitchat_thoughts.xml:219` 起），
  反映的是「**這個 pawn 自己餓不餓**」，而非「**殖民地存糧夠不夠**」。
  我的 `COLONY_FOOD_DAYS` 是倉庫總量視角，兩者語意不同。→ **未覆蓋，採用**。
- **死亡**：既有只有 `INITIATOR_thoughtDefName==DeadMansApparel`（穿死人衣服）這種間接、
  個人化的提及（`1.6/Defs/chitchat_thoughts.xml:1417`）。沒有「近 N 天內有殖民者死亡」這種
  殖民地時間軸事件變數。→ **未覆蓋，採用**。

三者皆通過查證，無需替換。

## 參照素材

- 分析（權威索引）：`analysis/rimworld_mods/speakup/architecture/00_overview.md`、`01_dialogue_pipeline.md`、
  `details/extension_points.md`（B1/B3 改碼接點）。
- SpeakUp 原始碼（直接讀）：`/home/lorkhan/.local/share/Steam/steamapps/workshop/content/294100/3445623063/`
  - `SpeakUp/ExtraGrammarUtility.cs:54`（`ExtraRules`，本擴充 Postfix 的目標）
  - `SpeakUp/ExtraGrammarUtility.cs:282`（`MakeRule` 語意，本擴充複製其「空值跳過」邏輯）
  - `SpeakUp/HarmonyPatches/GrammarResolver_Resolve.cs:20`（把 `ExtraRules()` 結果 AddRange 進 grammar）
  - `SpeakUp/HarmonyPatches/RuleEntry_ValidateConstantConstraints.cs:43`（數值 `<,>,<=,>=` 約束，本擴充的數值關鍵字賴此生效）
  - `SpeakUp/DialogManager.cs`（`Initiator`/`Recipient` public static 欄位）
  - `1.6/Patches/z_add_chitchat_nearest.xml:3`（XML 注入 Chitchat 的寫法範本）

## 技術棧

- C# / .NET Framework 4.8（RimWorld 1.6 mod 慣例），Harmony（`Lib.Harmony` 由 RimWorld 環境提供，編譯參照 workshop `0Harmony.dll`）。
- 注入機制：**Harmony Postfix `SpeakUp.ExtraGrammarUtility.ExtraRules()`**（B3 外掛式，不改原 mod）。
  附加的 `Rule_String` 會被 SpeakUp 既有的 `GrammarResolver_Resolve` Prefix 自然收走，沿用其 r_logentry 管線與數值約束。
- 死亡追蹤：`GameComponent`（隨存檔持久化）＋ Postfix `Verse.Pawn.Kill`。
- 台詞：`PatchOperationAdd` 注入原版 `Chitchat` 的 `logRulesInitiator/rulesStrings`（`1.6/Patches/zzz_context_expansion.xml`）。

## 目錄結構

```
speakup-context-expansion/
├── About/About.xml                       packageId=pas.speakup.contextexpansion，loadAfter SpeakUp/Harmony
├── Source/                               C# 原始碼 + .csproj（net48）
│   ├── SpeakUpContextExpansion.csproj
│   ├── SpeakUpContextExpansionMod.cs     Mod 入口，PatchAll
│   ├── ExtraRulesInjector.cs             核心：Postfix ExtraRules，注入三組情境變數
│   ├── ColonyDeathTracker.cs             GameComponent，記錄上次殖民者死亡 tick
│   ├── Pawn_Kill_Patch.cs                Postfix Pawn.Kill，殖民者死亡時寫入 tracker
│   └── Properties/AssemblyInfo.cs
├── 1.6/
│   ├── Assemblies/SpeakUpContextExpansion.dll   已成功編譯（見下）
│   └── Patches/zzz_context_expansion.xml        三情境的中文台詞
├── docs/context_variables.md             情境變數 / grammar key / 引用方式 / 建置步驟
├── PROJECT.md                            （本檔）
└── session_log.md
```

## 完成定義（Definition of Done）

- [x] 確認 3 個情境變數均未被 vanilla SpeakUp 覆蓋（查證結論見上）。
- [x] 每個呼叫的 RimWorld/SpeakUp API 均對照本機 `Assembly-CSharp.dll` / `SpeakUp.dll` 以 monodis 驗證存在。
- [x] C# 原始碼完整、含 .csproj（net48）、Mod 入口 PatchAll。
- [x] 對應中文台詞以 `PatchOperationAdd` 注入 Chitchat。
- [x] **DLL 已在本機成功編譯**：`dotnet build -c Release` → `1.6/Assemblies/SpeakUpContextExpansion.dll`
      （本機 `~/.local/share/Steam/.../RimWorldWin64_Data/Managed` 提供 Assembly-CSharp/UnityEngine，
       workshop 提供 0Harmony.dll 與 SpeakUp.dll；net48 reference assemblies 由 NuGet 套件提供）。
- [ ] **未做**：在實際 RimWorld 1.6 遊戲內執行時驗證（in-game smoke test）。本機未啟動遊戲驗證，
      邏輯正確性靠 API 對照與編譯保證；建議實機觀察 dev log 確認三關鍵字有被注入。
```
```
