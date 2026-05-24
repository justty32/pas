# 太吾繪卷 · 各類 NPC 模板 完整資料抽取

本資料夾把遊戲內「各類 NPC 模板」整批抽出留檔，**核心＝`Character` 表（882 筆）**，
另含次要的 `EventActors`（事件立繪角色，292 筆）。全程對遊戲與反編譯源唯讀。

## 一、資料來源（皆唯讀）

| 用途 | 路徑 |
|---|---|
| NPC 模板硬編資料 | `~/dev/taiwu-src/Assembly-CSharp/Config/Character.cs`（882 列 `new CharacterItem(...)`） |
| 欄位 → argN 對照 | `~/dev/taiwu-src/Assembly-CSharp/Config/CharacterItem.cs`（建構子 `:229-339`） |
| 名稱權威（與安裝版同步） | `StreamingAssets/ConfigRefNameMapping/Character.ref.txt`（name 偶數行/id 奇數行） |
| 特性名（FeatureIds 解析） | `ConfigRefNameMapping/CharacterFeature.ref.txt` |
| 門派名（OrganizationInfo 解析） | `ConfigRefNameMapping/Organization.ref.txt` |
| 事件角色 | `Config/EventActors.cs`、欄位 `EventActorsItem.cs:26-37`、`EventActors_language.txt` |
| 分類常量 | `GameData/Domains/Character/Creation/CreatingType.cs`、`MainAttributeType.cs` |

姓名/字/匿名稱號文字＝`Character_language.txt`，但本任務多以 ref 名稱為準（更貼合安裝版）。

## 二、CharacterItem 關鍵欄位 → argN 對照

`CharacterItem.cs` 建構子共 108 個參數（arg0~arg107）。對「描述一個 NPC 模板」有意義的：

| 欄位 | argN | CharacterItem.cs 行 | 含義 |
|---|---|---|---|
| `TemplateId` | arg0 | :231 | 模板 id（== ref 的 id） |
| `Surname` | arg1 | :232 | 姓（Character_language 行號） |
| `GivenName` | arg2 | :233 | 名（Character_language） |
| `AnonymousTitle` | arg3 | :234 | 匿名稱號（Character_language） |
| `FixedAvatarName` | arg5 | :236 | 固定頭像資源名（如 `NpcFace_monv`） |
| **`CreatingType`** | arg6 | :237 | **主分類**：0 固定/1 智能/2 隨機敵/3 固定敵 |
| `GroupId` | arg7 | :238 | 成群生成分組 id（-1=無） |
| **`FeatureIds`** | arg24 | :255 | **初始特性** id 清單（List\<short\>，對 CharacterFeature） |
| **`Gender`** | arg29 | :260 | **性別**：-1 隨機 / 0 女 / 1 男 |
| `PresetBodyType` | arg30 | :261 | 體型預設 |
| **`Race`** | arg31 | :262 | **種族**：0 漢 / 1 藏族 |
| `PresetFame` | arg34 | :265 | 預設名望 |
| `BaseAttraction` | arg36 | :267 | 基礎魅力（-1=隨機） |
| `BaseMorality` | arg37 | :268 | 基礎道德 |
| `ActualAge` | arg38 | :269 | 實齡（-1=隨機） |
| `InitCurrAge` | arg39 | :270 | 初始當前年齡 |
| `Health` / `BaseMaxHealth` | arg40/arg41 | :271-272 | 生命 / 基礎生命上限 |
| `BirthMonth` | arg42 | :273 | 出生月 |
| **`OrganizationInfo`** | arg43 | :274 | **所屬門派**：(OrgTemplateId, Grade 階級, Principal, SettlementId) |
| `IdealSect` | arg45 | :276 | 理想門派傾向 |
| `XiangshuType` | arg47 | :278 | 相術類型 |
| `MonkType` | arg48 | :279 | 僧侶類型 |
| `LifeSkillTypeInterest` | arg49 | :280 | 技藝偏好 |
| `CombatSkillTypeInterest` | arg50 | :281 | 武學偏好 |
| `MainAttributeInterest` | arg51 | :282 | 主屬性偏好 |
| **`BaseMainAttributes`** | arg56 | :287 | **6 主屬性**：[膂力,灵敏,定力,体质,根骨,悟性]（順序＝`MainAttributeType.cs`，名稱＝`CharacterPropertyDisplay` 0~5 行：膂力/灵敏/定力/体质/根骨/悟性） |
| `BaseLifeSkillQualifications` | arg98 | :329 | 16 項技藝資質（LifeSkillShorts） |
| **`BaseCombatSkillQualifications`** | arg102 | :333 | **14 項武學資質**（CombatSkillShorts，索引 0~13＝內功/身法/絕技/拳掌/指法/腿法/暗器/劍法/刀法/長兵/奇門/軟兵/御射/樂器） |

`OrganizationInfo` 結構見 `GameData/Domains/Character/OrganizationInfo.cs:7`。
`CreatingType` 常量見 `CreatingType.cs:5-11`；`IsFixedPresetType`(0/3)、`IsNonEvolutionaryType`(0/2/3)。

### ⚠ 反編譯坑：複合型參數被「提升成區域變數」
反編譯器把每列的複合型參數（List\<short\>、OrganizationInfo、MainAttributes、
CombatSkillShorts…）**抽成呼叫前的區域變數 `argN`**，`new CharacterItem(...)` 處只寫變數名：

```csharp
List<short> arg914 = new List<short> { 127 };
OrganizationInfo arg916 = new OrganizationInfo(40, 6, principal: true, -1);
MainAttributes arg918 = new MainAttributes(150, 120, 60, 150, 10, 10);
dataArray39.Add(new CharacterItem(218, 849, 850, 851, ..., arg914, ..., arg916, ..., arg918, ...));  // 老虎
```

且這些區域變數名**跨列重複使用**（arg914 在多列各被重新賦值）。
因此抽取時不能整檔搜 `arg914 = ...`，必須**以「上一個 `new CharacterItem` 結尾 ~ 本列起點」這段**
為作用域去取最近一次賦值。`extract_npc_templates.py` 的 `collect_locals()` 即按此切段解析。
另注意呼叫裡的具名標籤 `arg9: true`（建構子形參名）要先以 `^arg\d+:\s*` 去掉，
而值若是區域變數 `arg914`（無冒號）則交給 `resolve()` 回查。

## 三、分類維度與各類數量

主分類 `CreatingType`（882 筆）：

| CreatingType | 含義 | 筆數 |
|---|---|---:|
| 0 | 固定角色（命名 NPC / 劇情角色 / 部分精怪） | 424 |
| 1 | 智能角色（地區×性別 人口生成模板） | 32 |
| 2 | 隨機敵人（隨機怪 / 路人惡徒） | 235 |
| 3 | 固定敵人（劇情敵 / 首領 / 野獸座騎） | 191 |

- 性別 `Gender`：女 222 / 男 408 / 隨機 252
- 種族 `Race`：漢 879 / 藏族 3（僅藏族男/女模板 + 1）
- 帶初始特性 656 筆、帶特化主屬性 558 筆、帶武學資質 400 筆、**全部 882 筆都帶 `OrganizationInfo`**
- **智能角色＝16 地區 × 男/女＝32**：京畿/巴蜀/广南/荆北/山西/广东/山东/荆南/福建/辽东/西域/云南/淮南/江南/江北/藏族，
  各地區「男/女」各一個模板。命名規則證實＝`<地區><性別>`（地區+性別兩維度）。
- 非人口模板多以 `OrganizationInfo.OrgTemplateId` 標所屬：41=剑冢化身、40=野兽、各門派 id 對應 `Organization.ref.txt`。

## 四、產出檔案

| 檔案 | 內容 |
|---|---|
| `extract_npc_templates.py` | 抽取腳本（複用 `../extract_objects.py` 的 `split_top`/`iter_new_calls`/`load_ref`/`load_lang`），含 hoisted-local 解析 |
| `npc_templates.json` | Character 全 882 模板，每筆含分類/性別/種族/主屬性/武學資質/技藝資質/特性/所屬門派 |
| `event_actors.json` | EventActors 292 筆（性別/年齡區間/魅力區間/服飾/僧侶） |
| `NPC模板總覽.md` | 依 CreatingType 分節；智能角色全列，固定/敵人依所屬門派分組列關鍵欄位，含 EventActors |

## 五、重現方式

```bash
cd "analysis/taiwu/object_data_dump/NPC模板"
python3 extract_npc_templates.py
# 產生 npc_templates.json / event_actors.json / NPC模板總覽.md
```

依賴：`~/dev/taiwu-src` 反編譯源 + 安裝版 `StreamingAssets`（ref/語言檔）。腳本對兩者唯讀。

## 六、與 `../12_NPC與商隊模板.md` 的關係

- `12_` 只列 Character 的 **882 個名稱清單**（TemplateId↔名稱）＋商隊（Merchant/MerchantType）。
- 本資料夾**不重複名稱清單**，而是補上每個模板的**欄位/分類/屬性**（生成類型、性別、種族、所屬門派、主屬性、武學/技藝資質、初始特性）。
- 機制面研究見 `../../npc_population_research/`（生成入口、人口比例等），本檔只做「模板資料」，不覆蓋其機制結論。

## 七、未納入 / 註記

- **`Boss.cs`（具名首領）未抽取**：`BossItem.cs` 是**戰鬥演出/動畫**配置（攻擊動畫、粒子、階段技能、立繪），
  其 `CharacterIdList` 反指回 Character 表的角色 id，本身**不含 NPC 屬性**，故只在此註明、不納入模板資料。
- `CharacterFilterRules.cs`、`CharacterFeature.cs`：前者是生成篩選規則、後者是特性定義表（734 筆）；
  本任務僅借 `CharacterFeature.ref.txt` 把模板的 FeatureIds 解成名稱，未整表抽取。
