# 太吾繪卷 · 遊戲物件資料解壓縮（名稱＋品級）

把遊戲內各類物件的「名稱＋品級」整批抽出留檔。涵蓋使用者指定的六大類別，並擴充多項相關類別。

## 檔案索引

**六大核心類別**

| 檔 | 內容 | 筆數 |
|---|---|---:|
| [01_武功.md](01_武功.md) | 武功總覽（種類×品級矩陣＋全武功索引） | 919 |
| [01_武功-種類/](01_武功-種類/) | 武功**依功法種類拆 14 檔**，各檔依品級分節，含**正/逆特效＋典故** | 14 檔 |
| [02a_物品-武器.md](02a_物品-武器.md) | 武器（Grade 0~8） | 921 |
| [02b_物品-防具飾品衣物.md](02b_物品-防具飾品衣物.md) | 防具 / 飾品 / 衣物 | 938 |
| [02c_物品-消耗品.md](02c_物品-消耗品.md) | 藥品 / 食物 / 茶酒 | 646 |
| [02d_物品-材料書籍雜項.md](02d_物品-材料書籍雜項.md) | 材料 / 雜物 / 書籍 / 工具 / 坐騎 / 促織 | 1741 |
| [03_職稱身份.md](03_職稱身份.md) | 職稱／身份（OrganizationMember）＋階級(0~8) | 244 |
| [04_建築.md](04_建築.md) | 建築（BuildingBlock）＋最高等級 | 319 |
| [05_城鎮種類.md](05_城鎮種類.md) | 城鎮種類（6 型）＋**命名後綴統計**＋完整鎮名清單 | 6 型 / 408 名 |

**補充類別**

| 檔 | 內容 | 筆數 |
|---|---|---:|
| [06_技藝武學.md](06_技藝武學.md) | 技藝(LifeSkill) / 絕技境界 / 武學類型 | 144 / 19 / 14 |
| [07_動物與毒.md](07_動物與毒.md) | 元雞 / 蛟 / 毒 | 64 / 40 / 6 |
| [08_傳承.md](08_傳承.md) | 傳承功法（Legacy） | 749 |
| [09_見聞情報.md](09_見聞情報.md) | 見聞／情報（InformationInfo） | 580 |
| [10_人物與組織.md](10_人物與組織.md) | 志向營生 / 稱號 / 門派勢力 | 18 / 43 / 42 |
| [11_命格與特性.md](11_命格與特性.md) | 命格(六道) / 主角特性 / 人物特性 | 6 / 30 / 734 |
| [12_NPC與商隊模板.md](12_NPC與商隊模板.md) | NPC 生成模板 / 商人類型 / 商隊模板 | 882 / 9 / 54 |
| [13_地形與地區.md](13_地形與地區.md) | 地區 / 地形(地圖塊) / 地貌類型 | 138 / 142 / 6 |
| [14_秘聞.md](14_秘聞.md) | 秘聞（SecretInformation） | 117 |
| [15_類型枚舉.md](15_類型枚舉.md) | 內力類型 / 絕招類型 / 製造類型 / 製造子類型 | 36 / 22 / 184 / 297 |
| [taiwu_objects.json](taiwu_objects.json) | 全部原始抽取資料（機器可讀） | — |

**事件與 NPC（子資料夾，各含獨立抽取腳本＋README）**

| 子夾 | 內容 | 覆蓋 |
|---|---|---|
| [奇遇事件/](奇遇事件/) | 歷練奇遇 196（名稱＋簡短介紹＋類型＋難度）＋行旅遭遇/茶馬/被獵殺/商店事件 | ~600 筆 |
| [NPC模板/](NPC模板/) | `Character` 882 模板完整欄位（生成類型／性別／種族／所屬門派／主屬性／武學資質／特性）＋EventActors 292 | 882 + 292 |
| [NPC過月行為/](NPC過月行為/) | MonthlyActions 84／AiAction 59／BehaviorType／PrioritizedActions／村民行動／Ai*決策樹 | 12 表 374 |

> ⚠️ **逐表版本漂移**：反編譯源(2026-05-22)與安裝版 ref/語言檔不完全同版。**多數表 ref 對齊**（名稱走 ref）；但 **Adventure 例外**——ref 的 id↔name 排序與反編譯 TemplateId 錯位（ref[5]=家常酒宴 但反編譯列5=家常茶会），故奇遇改走「語言檔行號」保 Name+Desc 自洽。各子夾 README 均註明其取捨。

各表 md 開頭附「**品級分布**」（每品級各幾筆）。05 含命名後綴分析（見下）。

**武功特效**：每個武功的 `DirectEffectID`/`ReverseEffectID`（CombatSkillItem arg16/17）指向 `SpecialEffect` 表的 TemplateId，該表 `Desc`(arg19, int[]→`SpecialEffect_language`) 即正/逆特效機制描述（多行時取最後一條為完整描述）；典故則為武功自身 `Desc`(arg3)。特效文字內 `$0$`/`$1$` 是遊戲即時算出的威力成數，靜態無法還原，保留原樣。

## 資料從哪來？（架構）

太吾繪卷的 config 資料**硬編在反編譯後的 C# 靜態初始化**裡，不是外部資料檔：

- **品級／數值**：`~/dev/taiwu-src/Assembly-CSharp/Config/<Table>.cs`
  每列是 `new <Table>Item(arg0, arg1, …)`；對應的 `<Table>Item.cs` 建構子本體記載
  「欄位 = argN」對應（如 `Grade = arg2;`）。這些是字面整數，與安裝版的穩定 `TemplateId` 綁定。
- **名稱**：安裝版 `…/StreamingAssets/ConfigRefNameMapping/<Table>.ref.txt`
  直接記錄「名稱 ↔ TemplateId」（name 在偶數行、id 在奇數行），**與安裝版同步**。

抽取＝解析 `.cs` 取每列的 `TemplateId` 與品級欄位，再用 ref 檔把 `TemplateId → 名稱` 接上。

### 為什麼不用 `Language_CN/*_language.txt`？

`<Table>Item.cs` 的名稱其實是 `LocalStringManager.GetConfig("X_language", argN)`，
即語言檔的**第 argN 行**（0-based）。但本機安裝版的部分語言檔（如
`BuildingBlock_language`、`Organization_language`）相對反編譯版**插入過行**，
導致行號索引漂移（水域被跳過、職稱落到描述行）。`武功/物品/職稱` 的語言檔未漂移，
但為求一致與正確，**全部改以 ref 檔為名稱權威來源**（消歧、版本對齊）。
工具仍保留語言檔行號作為缺漏時的回退（本次 0 筆回退）。

## 六大類別對應表

| 使用者類別 | 對應資料 | 品級欄位 |
|---|---|---|
| 武功名稱品級 | `CombatSkill` | `Grade`（越大越高階） |
| 物品名稱品級 | `Weapon/Armor/Accessory/Clothing/Carrier/CraftTool/Medicine/Food/Material/Misc/SkillBook/Cricket` | `Grade` 0~8 |
| 職稱名稱品級 | `OrganizationMember`（`GradeName`） | `Grade` 0~8（8=掌门/城主/大当家） |
| 建築名稱品級 | `BuildingBlock` | `MaxLevel`（最高可建等級） |
| 城鎮種類名稱品級 | 列舉 `EOrganizationSettlementType` | 規模順序：村庄<市镇<关寨<城（另有门派据点、太吾村） |
| 身份名稱品級 | 同 `OrganizationMember`（太吾中「職稱／身份」為同一張成員階位表） | `Grade` 0~8 |

> 註：太吾的「職稱」與「身份」共用 `OrganizationMember` 一張表（門派職務、城鎮身份、營生身份都在內），
> 故 03 一檔即同時覆蓋兩者。

## 城鎮命名後綴（05 重點）

世俗聚落的名字來自 `Config/LocalTownNames.cs` 的 `TownNameCore`（硬編字串），**末字即種類標記**：

| 種類 | 後綴分布 |
|---|---|
| 村庄(Village) | 村×81 · 乡×55 |
| 市镇(Town) | 镇×101 · 驿×35 |
| 关寨(WalledTown) | 寨×64 · 口×34 · 关×26 · 砦×11 · 山×1 |

- **「堡」不在原版鎮名池**；Sect（门派据点）與 City 型聚落直接用「所屬組織名」（`Organization`），
  「堡／庄／谷／派」這類後綴出現在門派／勢力名（铸劍山庄、百花谷；玩家自製「陳家堡」亦屬此類）。
- 命名規則：`WorldMapModel.GetSettlementName` — 有隨機名 id 用鎮名池，否則用組織名。

## 重現方式

```bash
cd analysis/taiwu/object_data_dump
python3 extract_objects.py      # → taiwu_objects.json（讀反編譯 + 安裝版 ref，唯讀）
python3 render_markdown.py      # → 01..06_*.md
```

路徑常數寫在 `extract_objects.py` 開頭（遊戲安裝路徑、反編譯路徑）。全程唯讀，不改動遊戲檔。
