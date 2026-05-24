# 太吾繪卷 · 奇遇／遭遇事件資料抽取

把遊戲內「各類奇遇／遭遇事件」的**名稱 + 簡短介紹**整批抽出留檔。全程對遊戲與反編譯源唯讀。

## 資料來源（皆唯讀）

- 反編譯源：`~/dev/taiwu-src/Assembly-CSharp/Config/<Table>.cs`（2026-05-22 反編譯）
  - 每列資料 = `new <Table>Item(arg0, arg1, …)`；欄位↔argN 對應記在 `<Table>Item.cs` 建構子本體。
- 語言檔：`~/.local/share/Steam/steamapps/common/The Scroll Of Taiwu/The Scroll of Taiwu_Data/StreamingAssets/Language_CN/<pack>_language.txt`
  - `GetConfig("<pack>_language", idx)` = 該檔以 `\n` 切分後的**第 idx 行(0-based)**，字面 `\\n` 還原為換行；`idx==-1` 視為空字串。
- 名稱對照：`…/StreamingAssets/ConfigRefNameMapping/<Table>.ref.txt`（name 偶數行、id 奇數行，id==TemplateId）。

## 涵蓋資料表與筆數

| 表 | 標題 | 筆數 | 名稱欄 | 介紹欄 | 語言 pack |
|----|------|---:|--------|--------|-----------|
| `Adventure` | 歷練奇遇（主力） | 196 | arg1 | arg2 | Adventure_language |
| `AdventureType` | 奇遇類型 | 18 | arg1 | — | AdventureType_language |
| `AdventureTerrain` | 奇遇地形 | 23 | arg1 | arg2 | AdventureTerrain_language |
| `TravelingEvent` | 行旅遭遇 | 166 | arg1 | **arg4** | TravelingEvent_language |
| `TeaHorseCaravanEvent` | 茶馬商隊事件 | 24 | arg1 | arg2 | TeaHorseCaravanEvent_language |
| `TaiwuBeHuntedEvent` | 被獵殺/緝捕事件 | 15 | arg1(見坑) | — | TaiwuBeHuntedEvent_language |
| `ShopEvent` | 商店/設施事件 | 192 | **無 Name** | arg1 | ShopEvent_language |

> ShopEvent 任務估計 1310 筆，實際表只有 **192** 筆（估計值偏高，以實抽為準）。

## AdventureType 對照表（id → 顯示名 / 是否瑣碎 / 該類奇遇數）

> 採反編譯版語言檔取名（與 `Adventure.Type` 欄位的 id 體系對齊；安裝版 ref 為更細分的新版，見「版本漂移」）。

| id | 顯示名 | IsTrivial | 奇遇數 |
|---:|--------|-----------|---:|
| 0 | (空) | true | 0 |
| 1 | 主要故事 | false | 12 |
| 2 | 地区故事 | false | 36 |
| 3 | 奇缘趣事 | true | 9 |
| 4 | 外道巢穴 | true | 12 |
| 5 | 义士据点 | true | 3 |
| 6 | 季节趣事 | true | 21 |
| 7 | 比武招亲 | true | 15 |
| 8 | 比武招亲 | true | 15 |
| 9 | 天材地宝 | true | 4 |
| 10 | 天材地宝 | true | 2 |
| 11 | 天材地宝 | true | 2 |
| 12 | 天材地宝 | true | 2 |
| 13 | 天材地宝 | true | 2 |
| 14 | 天材地宝 | true | 11 |
| 15 | 剑冢异动 | false | 36 |
| 16 | 邂逅良缘 | true | 0 |
| 17 | 奇书宝典 | true | 14 |

說明：id 7/8 同為「比武招亲」（男/女版細分在新版 ref 才拆開）；id 9~14 同為「天材地宝」（新版 ref 拆成食材/木材/金铁/玉石/织物/药材 六類）。id 0、16 在本反編譯版未被任何奇遇使用。

## 欄位含義（Adventure）

- `Type`：奇遇類型 id（對 AdventureType）。
- `CombatDifficulty`：戰鬥難度（sbyte）。
- `LifeSkillDifficulty`：生活技能難度（sbyte）。
- `TimeCost`：耗時（byte）。
- 另有 `Interruptible`、`KeepTime`、`ResCost`、`ItemCost`、`Malice`、`AdventureParams`、
  以及分支結構 `StartNodes/TransferNodes/EndNodes/BaseBranches/AdvancedBranches`（未抽，原因見下）。

## 交付檔案

- `extract_adventures.py`：抽取腳本（複用上層 `extract_objects.py` 的 `split_top`/`iter_new_calls`/`load_lang`/`load_ref`），輸出 `adventures.json`。
- `gen_markdown.py`：讀 JSON → 產出下列分類 Markdown。
- `adventures.json`：全量結構化資料（每筆含 `Desc` 簡短版 + `DescFull` 完整版）。
- `01_歷練奇遇_Adventure.md`：196 筆，按 AdventureType 分節（名稱＋簡介＋戰鬥/生活難度＋耗時）。
- `02_其他遭遇事件.md`：TravelingEvent / TeaHorseCaravanEvent / TaiwuBeHuntedEvent / ShopEvent。
- `03_奇遇地形_AdventureTerrain.md`：23 種地形。

## 重現方式

```bash
cd /home/lorkhan/repo/pas/analysis/taiwu/object_data_dump/奇遇事件
python3 extract_adventures.py   # → adventures.json + 終端摘要
python3 gen_markdown.py         # → 01/02/03 *.md
```

## 完整範例（名稱 → 簡短介紹）

1. **世外秘境**（季节趣事，戰鬥6/生活1）：「荒野偏僻之处，隐有不知名的喑哑嘶声扰人心神。此处隐秘难寻，竟好似一处世外秘境。其中有何怪异之处，不如前去一探究竟……」
2. **《浑心无字诀》**（奇书宝典，戰鬥7/生活7）：「不世宝典——《浑心无字诀》——已被发现！武林当中正邪各派的高手正逐渐聚集于此，一场大战在所难免！」
3. **道路坎坷**（TravelingEvent / 行旅遭遇）：「前方道路坎坷，由此地通行将损耗载具耐久…」

## 資料坑與注意事項（重要）

### 1. 版本漂移：反編譯源 vs 安裝版 ref／語言檔 不同版本
反編譯源（2026-05-22）與安裝版的 `ConfigRefNameMapping`／語言檔**並非同一版本**。驗證：
- `Adventure.cs` row 0 的 Name 索引 arg1=135 → 安裝版 `Adventure_language[135]`=「世外秘境」；
  但 `Adventure.ref.txt` 的 id 0 卻是「比武大会·刀法」（= `Adventure_language[137]`，對應反編譯 row **1**）。
  → 反編譯源的 **TemplateId→內容對應** 與安裝版 ref 不一致（ref 用了新版重排的 id）。
- 但反編譯源的 **arg1(Name)／arg2(Desc) 行號在安裝版語言檔內仍取出「內部自洽」的 Name+Desc 配對**
  （相鄰兩行語意一致）。
- **結論**：本抽取一律走「語言檔行號」路線（`Name=lang[arg1]`），**不採 ref 名稱**，
  以免 Name 取自新版 id 排序、Desc 取自舊版行號 → 張冠李戴。
- 同類漂移亦見於 `AdventureType`（ref 18 項細分 vs 反編譯版 12 行）與 `ShopEvent`
  （ref id 0「堤堰成功」≠ 語言檔[0]「顺利地进行了捕捞工作」）。

### 2. TaiwuBeHuntedEvent 的逐列偏移
此表每門派一個「敘述區塊」。反編譯源 arg 行號採每區塊 **14 行步幅**（0,14,28,…），
但安裝版語言檔每區塊多一行（15 行），導致自 row1 起逐列累積偏移、敘述文字錯位
（如 row1 的 arg1 取到上一區塊末行的敘述、arg2 取到「峨眉派」）。
→ 此表 **Name 改用 ref**（`TaiwuBeHuntedEvent.ref` 已驗證 15 個門派名 id==TemplateId 對齊：
少林派/峨眉派/百花谷/武当派/元山派/狮相门/然山派/璇女派/铸剑山庄/空桑派/金刚宗/五仙教/界青门/伏龙坛/血犼教），
敘述因偏移不可靠故不取語言檔行，以制式說明代替。

### 3. 分支結構（StartNodes/Branches/EndNodes）未抽
`AdventureItem` 的分支清單欄位（arg15~arg19）在反編譯結果中是**反編譯器產生的區域變數佔位**
（如 `arg215`、`arg219`），實際 `new List<…>{…}` 內容於別處賦值，無法靠 inline 解析取得。
依任務要求（分支樹不必展開）故略過，僅保留「名稱＋簡介＋類型＋難度」。

### 4. TravelingEvent 的 Type 為 enum
`TravelingEventItem` 的 `Type`(arg3)、`DisplayType`(arg2) 是 enum（非 int）。本抽取取 enum 點號後字尾
（如 `ETravelingEventType.AreaMaterial` → `AreaMaterial`）。Desc 在 **arg4**（非 arg2）。

### 5. TravelingEvent 名稱 ref 為英文代號
`TravelingEvent.ref` 給的是英文 code name（如 `JingjiMaterial`），非玩家可見中文，故必走語言檔。
