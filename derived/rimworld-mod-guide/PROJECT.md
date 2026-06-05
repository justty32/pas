# RimWorld Modding 入門指南（HTML）

## 衍生目標
為**資深 C# 工程師**製作一套 RimWorld mod 製作入門 HTML 指南，跳過 C# 語法基礎，聚焦 RimWorld 特有的架構與工具鏈。

## 技術棧
- 純靜態 HTML + 單一共用 CSS（`html/_shared.css`），暗色主題
- 無 build step，直接用瀏覽器開 `html/index.html`
- 遵循 CLAUDE.md 準則 6（HTML 導覽層）與準則 7（禁 ASCII art，改用語意化卡片/表格）

## 內容結構（html/）
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
| `08`–`27` | 內容系統與參考：貼圖/音效/在地化/Pawn生成/事件敘事/世界地圖/研究生產/戰鬥/測試/服裝/建築/動植物/需求心情/基因/任務/材質/能力/地圖生成/儲存/速查食譜 |
| `28-health-medical.html` | Hediff/HediffComp、手術 RecipeDef、BodyPart、免疫、義體 |
| `29-ai-jobs.html` | Job/Toil、WorkGiver、ThinkTree/JobGiver、Duty、預約 |
| `30-lord-groupai.html` | Lord/LordToil/LordJob、StateGraph、Trigger、突襲協調 |
| `31-factions.html` | FactionDef、goodwill、pawnGroupMaker、世界生成 |
| `32-ideology.html` | MemeDef/PreceptDef、Role、Ritual、Style（Ideology DLC）|
| `33-royalty.html` | RoyalTitleDef、permit、psylink、帝國（Royalty DLC）|
| `34-mechanitor.html` | mechanitor、bandwidth、機械 PawnKind、製造召回（Biotech DLC）|
| `35-temperature-gas.html` | GenTemperature、Room、gas grid、屋頂、WeatherDef |
| `36-performance.html` | tick 預算、HashOffset、剖析、Rand 確定性、多人相容 |

## 完成定義
- [x] 36 個內容頁 + 總覽 index + 共用 CSS（共 37 個 html）
- [x] nav 全站 37 連結一致（所有頁 nav block 雜湊相同、每頁恰 1 active）
- [x] 全繁體中文、程式碼語法高亮
- [x] index.html「共 37 章」+「深入系統與 DLC」卡片區（28–36）
- [x] 25–36 章程式碼範例對反編譯原始碼逐符號校對（12 章並行；修正大量虛構類別／錯誤欄位名／錯誤 namespace，詳見 session_log）
- [x] 版本標示統一為 1.6（badge／footer／supportedVersions 範例；保留兩處「1.5 引入」歷史事實敘述）
- [ ]（待定）logo 文字統一（02 頁為「RimWorld Modding」，其餘為「⚙ RimWorld Mod」）

## 對應 RimWorld 版本
1.6（磁碟上的反編譯原始碼 `projects/rimworld/` 即 1.6，含 Gravship/Odyssey；校對一律以此為權威。部分章節含 1.4/1.5/1.6 多版本相容說明）
