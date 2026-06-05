# RimWorld Modding 入門指南（HTML）

## 衍生目標
為**資深 C# 工程師**製作一套 RimWorld mod 製作入門 HTML 指南，跳過 C# 語法基礎，聚焦 RimWorld 特有的架構與工具鏈。

## 技術棧
- 純靜態 HTML + 單一共用 CSS（`html/_shared.css`），暗色主題
- 無 build step，直接用瀏覽器開 `html/index.html`
- 遵循 CLAUDE.md 準則 6（HTML 導覽層）與準則 7（禁 ASCII art，改用語意化卡片/表格）

## 內容結構（html/）
共 **27 個內容頁** + 總覽頁，nav 全站統一為「總覽 + 01~27」28 連結。

| 檔案 | 主題 |
|---|---|
| `index.html` | 總覽：兩根支柱（XML/C#）、資料夾結構、技術棧、學習路線 |
| `01-environment.html` | VS/Rider 專案設定、.csproj reference、dnSpy 反編譯、開發迴圈 |
| `02-xml-defs.html` | Def 反序列化、類型速查、繼承、PatchOperation、DefOf |
| `03-harmony.html` | Prefix / Postfix / Transpiler、AccessTools、Priority、陷阱 |
| `04-patterns.html` | ThingComp、GameComponent、WorkGiver/JobDriver、Hediff、ModSettings、ITab、Alert、DefModExtension |
| `05-debug.html` | Dev mode、Log 閱讀、dnSpy attach、錯誤速查、Steam 發布、相容性 |
| `06-ui-widgets.html` | IMGUI、Widgets 速查、Listing_Standard、Dialog、貼圖、佈局 |
| `07-advanced.html` | IL Transpiler 深入、性能、Scribe 存檔、多版本、跨 mod、資料結構速查 |
| `08-graphics-textures.html` | 貼圖／圖形系統：Graphic 類型、PawnRenderer、材質、著色 |
| `09-sound-audio.html` | 音效系統：SoundDef、SubSoundDef、播放與參數 |
| `10-localization.html` | 在地化：Keyed/DefInjected、語言檔結構、複數規則 |
| `11-pawn-generation.html` | Pawn 生成：PawnKindDef、PawnGenerationRequest、Backstory/Trait/Skill/Hediff |
| `12-incidents-storyteller.html` | 事件與敘事者：IncidentDef/Worker、Storyteller、威脅點數、Letter |
| `13-world-map.html` | 世界地圖與派系：World/Tile、WorldObject、FactionDef、Caravan、Biome |
| `14-research-production.html` | 研究與生產鏈：ResearchProjectDef、RecipeDef、Bill、工作台、StatPart |
| `15-combat-damage.html` | 戰鬥與傷害：DamageDef/Worker、Verb、Projectile、護甲模型、BodyPart |
| `16-testing.html` | 測試：Dev 工具、單元測試思路、回歸驗證 |
| `17-apparel-equipment.html` | 服裝與裝備：Apparel、ApparelLayer、穿著圖形、Equipment 武器 |
| `18-buildings-power.html` | 建築與電力：ThingDef 建築、CompPower、電網 |
| `19-plants-animals.html` | 植物與動物：PlantProperties、生長、RaceProperties、馴養 |
| `20-needs-mood-thoughts.html` | 需求／心情／想法：NeedDef、ThoughtDef、Memory/Situational、MentalState |
| `21-genes-xenotypes.html` | 基因與異種：GeneDef、XenotypeDef、生物科技 |
| `22-quests.html` | 任務系統：QuestScriptDef、QuestNode、SignalAction |
| `23-stuff-materials.html` | 材質系統：StuffProperties、stuffCategories、StatFactor |
| `24-abilities-psycasts.html` | 能力與超能：AbilityDef、CompAbilityEffect、Psycast |
| `25-map-generation.html` | 地圖生成：MapGeneratorDef、GenStep、TerrainDef、噪聲、結構生成 |
| `26-storage-filters.html` | 儲存／分類／篩選：ThingCategoryDef、ThingFilter、StorageSettings、Building_Storage |
| `27-cookbook.html` | 速查食譜：常見任務的最小可用範例集 |

## 完成定義
- [x] 27 個內容頁 + 總覽頁 + 共用 CSS
- [x] nav 全站 28 連結一致、每頁 active 標記正確、logo 文字統一（皆「⚙ RimWorld Mod」）
- [x] 全繁體中文、程式碼語法高亮
- [ ]（選用）校對各頁程式碼範例正確性
- [ ]（選用）加 Preview／截圖

## 對應 RimWorld 版本
1.5（部分章節含 1.4/1.5 多版本相容說明）
