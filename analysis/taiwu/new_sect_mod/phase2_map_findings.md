# 陳家堡 Mod — Phase 2 上地圖機制調查＋反射程式雛形

> 任務：純調查＋留檔。唯一事實來源＝反編譯原始碼 `~/dev/taiwu-src/`（backend 在 `~/dev/taiwu-src/backend/`）。
> 接續 Phase 0（`phase0_findings.md` §3）與 `plan.md` §2.3/§8。Phase 1 程式已在 `projects/taiwu/ChenJiaBao/`（唯讀，不碰）。
> 本檔結論逐項回原始碼覆核並標 path:line。**狀態：1–5 全釘死＋反射雛形就緒；發現 §6.0 重大阻斷器並給出修正策略。**

---

## 0. 任務範圍與背景（Phase 1 既成事實，唯讀）

- Phase 1：`Backend/Plugin.cs` 的 `Plugin : TaiwuRemakePlugin`，`Initialize()` 內呼 `InjectChenJiaBao()`，
  克隆少林(id=1)→ `OrganizationItem` id=42，`Organization.Instance.AddExtraItem("ChenJiaBao","ChenJiaBao_42",item)`。
  常數 `ChenJiaBaoTemplateId = 42`。
- 本 Phase 任務：把「陳家堡上地圖」的反射改寫設計成放在 `Initialize()` 內、**org 注入之後**呼叫的新方法（例如 `PlaceOnMap()`）。

---

## 1. settlementCount 與世界生成迴圈（已覆核）

### 1.1 settlementCount 來源（行號已位移，覆核版）
`MapDomain.cs:3879`：
```csharp
int settlementCount = areaConfigData.OrganizationId.Length + (taiwuVillageInArea ? 1 : 0);
```
- `areaConfigData = mapAreaData.GetConfig()`（`:3871`）即該 area 的 `MapAreaItem` 藍圖。
- 一般 area 的聚落數 = `OrganizationId.Length`；只有太吾村所在 area 額外 +1。

### 1.2 生成迴圈（`MapDomain.cs:4093-4101`，覆核版）
```csharp
for (int i4 = settlementCount - 1; i4 >= 0; i4--) {
    short blockId9 = staticBlockIdList[i4];
    Location location = new Location(areaId, blockId9);
    ...
    sbyte orgTemplateId = (sbyte)(isTaiwuVillage ? 16 : (isStoryStockade ? 38 : areaConfigData.OrganizationId[i4]));
    short settlementId = DomainManager.Organization.CreateSettlement(context, location, orgTemplateId);
    ...
    mapAreaData.SettlementInfos[i4] = new SettlementInfo(settlementId, blockId9, ...);  // :4105
}
```
- `orgTemplateId = areaConfigData.OrganizationId[i4]`（一般 area），呼 `CreateSettlement` 生聚落。
- `blockId9 = staticBlockIdList[i4]`：**這個 blockId 是執行期算出的座標索引**，由 `PlaceStaticBlocks` 填入 `staticBlockIdList`。

### 1.3 ⚠️ 對 Phase 0 的重大修正：`SettlementBlockCore[i]` 不是「地圖座標 block id」，而是「block 模板 id」
`PlaceStaticBlocks`（`MapDomain.cs:4509`）：
```csharp
List<short> staticBlockCore = ...;
if (areaId == 138) staticBlockCore.Add(36);
else staticBlockCore.AddRange(areaConfigData.SettlementBlockCore);   // :4519
int settlementCount = staticBlockCore.Count;                          // :4521
...
for (int index = 0; index < staticBlockCore.Count; index++) {
    MapBlockItem blockConfig = MapBlock.Instance[staticBlockCore[index]];          // :4563 ← 當 MapBlock 模板 id 用！
    GetStaticBlockPosRandomPool(blockConfig, mapSize, availableBlockMap, edgeClipMap, canUsePosList);  // :4564 引擎自己挑空位
    ...
    if (index < settlementCount && canUsePosList.Count == 0)
        throw new Exception($"Area {areaId} is too small to place the {index} static block {blockConfig.TemplateId}");  // :4595
    ByteCoordinate byteCoordinate = ... canUsePosList.GetRandom(random);          // :4600 隨機挑一個合法空位
    PlaceStaticBlock(areaId, ..., staticBlockCore[index], byteCoordinate, ...);   // :4601
    staticBlockIds.Add(CoordinateToIndex(byteCoordinate, mapSize));               // :4602 ← 把座標索引塞回 staticBlockIdList
}
```
- `staticBlockCore[index]` 被當作 `MapBlock.Instance[...]` 的鍵（`:4563`）→ 它是 **`MapBlock` config 的 TemplateId（block 種類）**，例如「門派型聚落 block」這個模板，不是地圖上某個 (x,y) 座標。
- 真正的座標 (`byteCoordinate`) 由 `GetStaticBlockPosRandomPool`（`:4610`）掃描 `availableBlockMap`/`edgeClipMap` 找出**所有合法空位**，再 `GetRandom(random)` 隨機挑一個（`:4600`）。
- `GetStaticBlockPosRandomPool`（`:4610-4643`）排除條件：邊界、`availableBlockMap[i,j]==1`（已被佔）、`edgeClipMap[i,j]!=1`（被裁掉/不可放）。後續還排除與既有 block 重疊、與中心距離過近（`:4565/4570/4571-4592`）。
- ⇒ **引擎已負責挑「合法、未被佔用」的空位**。mod 端不需要也不該硬指定一個地圖座標 id。
- `staticBlockIdList` 與 `OrganizationId` 透過 index 對位：第 `index` 個 `SettlementBlockCore` 模板被擺到第 `index` 個座標 → 迴圈 `:4099/4095` 用同一 `i4` 取 `OrganizationId[i4]` 與 `staticBlockIdList[i4]`。**平行對應成立**（前提：兩陣列等長，見 §2）。

> 結論修正：Phase 0 §3.2「append 一個該 area 內合法、未被佔用的區塊 id」措辭易誤導。正解＝在 `SettlementBlockCore` append 一個**合法的 block 模板 id（聚落型 MapBlock TemplateId）**，引擎自動找空位擺放，無需手動算座標。詳見 §3。

## 1.4 兩陣列平行對應 — 全 area 機器掃描驗證（鐵證）

對 `MapArea.cs` 全部 `new MapAreaItem(...)` 解析建構子第 17/18 位（= `SettlementBlockCore`/`OrganizationId`）：**120 個一般 area（TemplateId 0–119）全部 `SettlementBlockCore.Length == OrganizationId.Length`，零例外。** 其餘 18 個（120–137）為特殊 area（出生/引導/秘境/故事山寨/CustomBlockConfig），不在改寫範圍。
- 欄位型別與宣告（`MapAreaItem.cs`）：`SettlementBlockCore` 是 `short[]`（`:44`）、`OrganizationId` 是 `sbyte[]`（`:46`），皆 `readonly`。
- 建構子位置（`MapAreaItem.cs:82` 簽名、`:100/101` 賦值）：第 17 個引數 `arg16 → SettlementBlockCore`、第 18 個引數 `arg17 → OrganizationId`。
- 抽樣覆核（path:line 為 `MapArea.cs`）：
  - area 0：`SettlementBlockCore={17}`、`OrganizationId={0}`（`:129/130`，`:219` Add）。
  - area 1（京城/城市）：`{1,35,36}`/`{21,37,38}`（`:268/269`，`:361` Add）。
  - area 16（少林門派區）：`{19,35,36}`/`{1,37,38}`（`:2361/2362`，`:2451` Add）。
- ⇒ **平行等長對應成立**：第 `i` 個 `SettlementBlockCore`（block 模板）↔ 第 `i` 個 `OrganizationId`（門派）。在尾端各 append 一格即新增一個聚落槽，`settlementCount`（`MapDomain.cs:3879`）自動 +1。

## 2. 目標 area 選定

> ⚠️ **先讀 §6.0**：因 `MapAreaData.SettlementInfos` 硬限 3 格，本節原先「area 16 加長到 4」**不可行**。
> 最終建議目標＝**常規野外區 area 31（1 聚落→2）**（方案 ①）；area 16 改為「取代槽」備案（方案 ②）。下表分析仍有效。

### 2.1 候選分類（依 §1.4 掃描）
| 類別 | TemplateId | Size | 每區聚落數 | 內容 |
|------|-----------|------|-----------|------|
| 城市區 | 1–15 | 30 | 3 | 1 城 + Town(37) + WalledTown(38) |
| **門派區** | **16–30** | **30** | **3** | 1 大派 Sect + 2 個 Town/WalledTown |
| 常規野外區 | 31–119 | 20 | 1 | 單一 Town(35)/WalledTown(36)/Village(34) |

### 2.2 選定：**area TemplateId = 16（少林所在門派區，DefIcon `MapGangShaolin`）**
理由（一句）：**它本來就是「門派區」、Size=30（地夠廣）、已內含 Sect 型 block 與門派氛圍配置，而 Phase 1 的陳家堡正是克隆少林(id=1) → 安插在少林同區語意最自然、視覺最相容、且不擠掉任何原版聚落（用 append 不取代）。**
- area 16 現有 `OrganizationId = {1, 37, 38}`（少林 / Town / WalledTown），`SettlementBlockCore = {19, 35, 36}`（ShaolinPai block / Town block / WalledTown block）（`MapArea.cs:2361/2362`，`:2451` Add）。
- area 16 `Size=30`，3 聚落 → 加到 4 聚落，密度仍低，遠未觸及「area too small」例外（`MapDomain.cs:4595`）。
- 備選：若不想與少林同區，任一城市區（如 area 0/京城周邊地廣區）或多個常規區同理可改；流程完全一致，只是改不同 area config。

> 注意：選 area 16 不影響 Phase 0「不進大派好感度網」結論——陳家堡 id=42 仍非 1..15，`GetLargeSectIndex(42)=-1`（`OrganizationDomain.cs:1320-1323`），與所在 area 無關。

## 3. 空閒 block 與 SettlementBlockCore 模板選定（已釐清＋已選定）

### 3.1 重大澄清：`SettlementBlockCore[i]` 是 **block 模板 id（MapBlock.TemplateId）**，不是地圖座標
見 §1.3。`PlaceStaticBlocks` 把 `SettlementBlockCore[i]` 餵給 `MapBlock.Instance[...]`（`MapDomain.cs:4563`）當「block 種類」，引擎用 `GetStaticBlockPosRandomPool`（`:4610`）自動掃出合法空位再隨機挑（`:4600`）。
- ⇒ **mod 不需要、也不該自己算一個 (x,y) 座標 id。** 只要 append 一個合法的 **block 模板 id**，引擎自動找該 area 內合法、未被佔用、passable 的位置擺放。
- 「未被佔用」判定在引擎端（`GetStaticBlockPosRandomPool` 排除 `availableBlockMap==1` 已佔、`edgeClipMap!=1` 不可放、`:4626`；後續再排除與既有 block 重疊/距中心過近，`:4565/4570/4571-4592`）。

### 3.2 block 模板分類（`MapBlock.cs`，path:line）
- Sect 型 block：id **19–33**（`MapBlock.cs:255-269`），各綁特定門派視覺/atlas（如 id 19 = `EMapBlockType.Sect, EMapBlockSubType.ShaolinPai`，`:255`）。
- 通用聚落 block：id **34 Village**（`:270`）、**35 Town**（`:271`）、**36 WalledTown**（`:272`）——無門派專屬視覺。
- 沒有「通用 Sect block」：所有 Sect block 都帶特定門派 atlas。

### 3.3 選定 `SettlementBlockCore` 新成員 = **block 模板 id 19（ShaolinPai 型 Sect block）**
理由（一句）：**陳家堡克隆自少林，沿用 19 號 Sect block 可讓地圖區塊正確顯示為「門派型聚落」且視覺與少林一致（既然資料整套克隆少林）；它是合法、`CanGenerate=true` 的 block 模板，引擎會自動找空位。**
- block 19 = `MapBlockItem(19, EMapBlockType.Sect, EMapBlockSubType.ShaolinPai, ..., arg36: true)`（`MapBlock.cs:255`，末位 `arg36=CanGenerate=true`，欄位 `MapBlockItem.cs:82`）。
- 後備方案 A（不想視覺撞少林）：用通用 **35 Town**（`MapBlock.cs:271`）或 **34 Village**（`:270`）當 `SettlementBlockCore` 新成員——聚落仍是 Sect（由 `OrganizationId=42`+`IsSect` 決定，§見 1/CreateSettlement），只是地圖圖示走通用城鎮樣式。
- 後備方案 B（最保險、零視覺風險）：直接複製 area 16 既有的某個 `SettlementBlockCore` 值（例如再放一個 35 Town block），確定該 block 模板在此 area 必能擺放（原版已用）。
- ⚠️ 不存在「block 模板 id 與 area 不相容」的硬限制；唯一風險是 area 太小擺不下（`:4595`），area 16 Size=30 + 僅 4 聚落不會觸發。執行期保險：見 §6「area too small 後備」。

## 4. 注入時機：`MapArea.Init()` 先於 plugin `Initialize()`（已釘死＝安全）

backend 啟動序列（`Program.cs:Main`，path:line）：
1. `:46` `DomainManager.Global.ReloadAllConfigData()`
   → `GlobalDomain.cs:396-402`：`Parallel.ForEach(ConfigCollection.Items, item => item.Init())`（`:399/401`）。
   → `MapArea.Instance` 在 `ConfigCollection.Items` 內（`ConfigCollection.cs:120`），故此步呼叫 `MapArea.Init()`（`MapArea.cs:17921-17930`）→ 重建 `_dataArray = new List<MapAreaItem>(138)`、跑 `CreateItems0/1/2()` 灌滿 138 個 area。**此時所有 area config（含 area 16 的兩陣列）已就緒。**
2. `:52` `GameData.GameDataBridge.GameDataBridge.Initialize()`
   → `GameDataBridge.cs:118` `InitializeGameDataModule()`（`:180`）→ `:184` `DomainManager.Mod.LoadAllMods(_modInfos)`
   → `ModDomain.cs:127-132`：對每個 backend plugin 呼 `PluginHelper.LoadPlugin(...)`（`:130`，TaiwuModdingLib 內，會實例化 plugin 並呼其 `Initialize()`）。**陳家堡 `Plugin.Initialize()` 在此跑。**
   → `:189-191` 才跑各 domain `OnInitializeGameDataModule()`（含 `OrganizationDomain.InitializeSectOrgTemplateIds()` 建可加入門派池）。
3. `:55` `OnInitializeGameDataModule()`、`:56` `OnLoadWorld()`；**世界生成（`MapDomain` 放聚落迴圈）遠在開新世界時才跑**，晚於 plugin `Initialize()`。

**結論**：`MapArea.Init()`（步驟 1，`:46`）**嚴格早於** plugin `Initialize()`（步驟 2，`:52`）。
⇒ 陳家堡的地圖反射改寫放在 `Plugin.Initialize()` 內**安全**：改寫時 area 16 config 已存在；改寫後、世界生成前資料已就位。
- 與 Phase 0 §4 一致，且本 Phase 把「`MapArea.Init` 是否先完成」由推測升級為**原始碼確證**（同一條 `ReloadAllConfigData` 並行 Init 機制，與 Organization 表同步完成）。
- 注意 `ReloadAllConfigData` 用 `Parallel.ForEach`（`GlobalDomain.cs:399`）→ 各 config 表的 `Init()` 是平行跑的，但**全部在 `:46` 這一步同步等待完成後才往下**（`Parallel.ForEach` 會 join），故 plugin `Initialize()`（`:52`）執行時所有表必已 Init 完。**這也呼應 MEMORY「過月平行段勿寫全域」的陷阱**——但本 Phase 的反射改寫發生在 plugin `Initialize()`（單執行緒、平行段已結束），不在平行段內，安全。

## 5. 反射加長兩陣列各一格 — C# 程式雛形（已就緒）

### 5.1 欄位對齊（`MapAreaItem.cs` 真實宣告）
- `public readonly short[] SettlementBlockCore;`（`MapAreaItem.cs:44`）
- `public readonly sbyte[] OrganizationId;`（`MapAreaItem.cs:46`）
兩者皆 `readonly` → 不能直接賦值；做法＝**建新陣列複製舊值 + 尾端 append**，再用 `FieldInfo.SetValue` 把整個陣列引用換掉（與 MySwordArt `DataConfigAppender` 反射覆寫 `readonly` 欄位同一手法）。
- **修改對象是既有 area 16 的 `MapAreaItem` 物件本身**（從 `MapArea.Instance[16]` 取得的那個引用），**不是** `MapArea.AddExtraItem`（那是新增 area，本任務不用）。
- `MapArea.Instance[16]` 走索引器 `this[short]` → `GetItem(16)`（`MapArea.cs:108`），16 < `_dataArray.Count(=138)` → 回 `_dataArray[16]`，即 config 表內那個實例。改它的陣列欄位＝改 config，世界生成時 `mapAreaData.GetConfig()`（`MapDomain.cs:3871`）取到同一引用。

### 5.2 程式雛形（要整合進 ChenJiaBao Phase 1 的 `Backend/Plugin.cs`）
整合說明：在 `Plugin.Initialize()` 內、`InjectChenJiaBao()`（org 注入）**之後**呼叫新方法 `PlaceOnMap()`。
即把 `Initialize()` 改成：
```csharp
public override void Initialize()
{
    try
    {
        InjectChenJiaBao();   // Phase 1：注入 org 42（必須先做，PlaceOnMap 依賴 42 已存在）
        PlaceOnMap();         // Phase 2：把 area 16 的兩陣列各加一格
    }
    catch (System.Exception ex)
    {
        AdaptableLog.TagError(Tag, "陳家堡注入失敗：" + ex);
    }
}
```
新方法（建議放在 `Plugin.cs`，與 `InjectChenJiaBao()` 同類）：
```csharp
using System;
using System.Reflection;
using Config;          // MapArea / MapAreaItem
// 既有 using：GameData.Utilities (AdaptableLog) 等

// 目標 area：常規野外區 TemplateId=31（原 1 聚落，加長到 2，仍 ≤ SettlementInfos[3] 上限）。
//   見 §6.0：area 16(3聚落) 加長到 4 會 IndexOutOfRange，故改選 <3 聚落的常規區。
private const short TargetMapAreaId = 31;
// 新聚落用的 block 模板 id：19 = ShaolinPai 型 Sect block（與克隆來源少林一致）。
// 後備：改 35(Town) 或 34(Village) 走通用城鎮圖示，見 §3.3。
private const short ChenJiaBaoBlockTemplateId = 19;

private void PlaceOnMap()
{
    // 取得既有 area 16 的 config 實例（GetItem fallback：16 < _dataArray.Count，回 _dataArray[16]）。
    MapAreaItem area = MapArea.Instance[TargetMapAreaId];
    if (area == null)
    {
        AdaptableLog.TagError(Tag, $"找不到 MapArea[{TargetMapAreaId}]，放置陳家堡失敗。");
        return;
    }

    // readonly 欄位反射控柄（欄位名對齊 MapAreaItem.cs:44 / :46）。
    FieldInfo fOrg   = typeof(MapAreaItem).GetField("OrganizationId",
                          BindingFlags.Public | BindingFlags.Instance);
    FieldInfo fBlock = typeof(MapAreaItem).GetField("SettlementBlockCore",
                          BindingFlags.Public | BindingFlags.Instance);
    if (fOrg == null || fBlock == null)
    {
        AdaptableLog.TagError(Tag, "反射取不到 OrganizationId / SettlementBlockCore 欄位（欄位名或型別改版？）。");
        return;
    }

    sbyte[] oldOrg   = (sbyte[])fOrg.GetValue(area);     // 如 {1,37,38}
    short[] oldBlock = (short[])fBlock.GetValue(area);   // 如 {19,35,36}

    // 平行等長前置斷言（理論上必相等，見 §1.4；不等則放棄，避免越界）。
    if (oldOrg == null || oldBlock == null || oldOrg.Length != oldBlock.Length)
    {
        AdaptableLog.TagError(Tag,
            $"area {TargetMapAreaId} 兩陣列長度不一致（org={oldOrg?.Length}, block={oldBlock?.Length}），放棄。");
        return;
    }

    // 冪等防呆：若已包含 42（重複載入 / 與他 mod 衝突）則略過。
    foreach (sbyte v in oldOrg)
        if (v == ChenJiaBaoTemplateId)
        {
            AdaptableLog.TagWarning(Tag,
                $"area {TargetMapAreaId} 已含 OrganizationId={ChenJiaBaoTemplateId}，略過地圖放置。");
            return;
        }

    // 對齊 MapAreaData.SettlementInfos 硬限 3（MapAreaData.cs:70/141/182）：
    // 加長後長度必須 <=3，否則世界生成 MapDomain.cs:4105 IndexOutOfRange / 存檔斷言失敗。
    if (oldOrg.Length + 1 > 3)
    {
        AdaptableLog.TagError(Tag,
            $"area {TargetMapAreaId} 已有 {oldOrg.Length} 聚落，加長到 {oldOrg.Length + 1} 超過 SettlementInfos[3] 硬限，放棄。" +
            "請改選聚落數 <3 的常規區（如 31）或改用『取代槽』策略（見 §6.0）。");
        return;
    }

    // 建新陣列：複製舊值 + 尾端 append（兩陣列同 index 對位，見 MapDomain.cs:4099/4095）。
    sbyte[] newOrg = new sbyte[oldOrg.Length + 1];
    Array.Copy(oldOrg, newOrg, oldOrg.Length);
    newOrg[newOrg.Length - 1] = ChenJiaBaoTemplateId;          // 42

    short[] newBlock = new short[oldBlock.Length + 1];
    Array.Copy(oldBlock, newBlock, oldBlock.Length);
    newBlock[newBlock.Length - 1] = ChenJiaBaoBlockTemplateId; // 19

    // 替換引用（讀寫 readonly 欄位）。
    fOrg.SetValue(area, newOrg);
    fBlock.SetValue(area, newBlock);

    AdaptableLog.TagInfo(Tag,
        $"陳家堡上地圖：area {TargetMapAreaId} 聚落槽 {oldOrg.Length} -> {newOrg.Length}，" +
        $"新增 OrganizationId={ChenJiaBaoTemplateId} / SettlementBlockCore={ChenJiaBaoBlockTemplateId}。");
}
```

### 5.3 為何這樣就會自動生出陳家堡
- 改寫後 area 16 的 `OrganizationId.Length` 由 3 → 4 → `settlementCount`（`MapDomain.cs:3879`）自動 +1。
- `PlaceStaticBlocks`（`:4509`）對新加的 `SettlementBlockCore[3]=19` 在 area 內找一個合法空位擺放，索引塞回 `staticBlockIdList[3]`（`:4602`）。
- 生成迴圈（`:4093-4101`）以 `i4=3` 取 `OrganizationId[3]=42` → `CreateSettlement(ctx, Location(16, 該空位), 42)` → 因 `IsSect(42)=true`（`OrganizationDomain.cs:2026→3601`）生成真正的 `Sect`＝陳家堡。
- **這是改既有 area 的 config 陣列，不是 `AddExtraItem` 新增 area**（再次強調，與 §5.1 對齊）。

## ⚠️ 6.0 重大阻斷器（本 Phase 最關鍵發現）：`MapAreaData.SettlementInfos` 硬限 3 格

> **這推翻 Phase 0「把任意 area 兩陣列加長一格」的通用做法。必須改策略。**

世界生成迴圈把每個聚落寫進**執行期** area 資料 `MapAreaData.SettlementInfos`：
`MapDomain.cs:4105`：
```csharp
mapAreaData.SettlementInfos[i4] = new SettlementInfo(settlementId, blockId9, settlement.GetOrgTemplateId(), randomNameId);
```
而 `MapAreaData.SettlementInfos` **硬寫死長度 3**，且 `CreateNormalArea`（`MapDomain.cs:3858`）**全程不依 `settlementCount` 重新配置它**：
- ctor：`SettlementInfos = new SettlementInfo[3];`（`MapAreaData.cs:70`）
- `Init`：`for (int i = 0; i < 3; i++) SettlementInfos[i] = ...`（`MapAreaData.cs:80-83`）
- 序列化斷言：`Tester.Assert(SettlementInfos.Length == 3);`（`MapAreaData.cs:141`）
- 反序列化修正：`if (SettlementInfos == null || SettlementInfos.Length != 3) SettlementInfos = new SettlementInfo[3];`（`MapAreaData.cs:182-184`）
- `_areas[i] = new MapAreaData();`（`MapDomain.cs:463`）→ 每個 area 都是 `[3]`。

⇒ 若把 area 16（原 3 聚落）的 `OrganizationId` 加長到 4，`settlementCount=4`，迴圈跑到 `i4=3` → `SettlementInfos[3]` **IndexOutOfRangeException，世界生成崩潰**。而且就算不崩，序列化斷言 `Length==3`（`:141`）也會在存檔時失敗。
- **原版每個 area 聚落數上限就是 3**（城市/門派區＝3；常規區＝1；太吾村區 = `OrganizationId.Length(≤2) + 1` ≤3）。`SettlementInfos[3]` 正好卡死這個上限。

### 6.0.1 修正後策略（取代 §2 對 area 16「加長到 4」的方案）
**唯一安全的純反射做法（零核心 Harmony patch）＝把一個「目前 < 3 聚落」的 area 加長到「仍 ≤ 3」，留在 `[3]` 上限內。**

兩個可選：
- **方案 ①（建議）— 在常規野外區（Size=20、目前 1 聚落）加長到 2**：
  - 例如 area **TemplateId=31**（`MapArea.cs:4553` Add；`SettlementBlockCore = arg515 = new short[1]{35}`（`:4462`）、`OrganizationId = arg516 = new sbyte[1]{37}`（`:4463`））。
  - 反射後 → `OrganizationId={37,42}`、`SettlementBlockCore={35,19}`，`settlementCount=2`（≤3，`SettlementInfos[3]` 足夠）。
  - 保留原有 1 個城鎮 + 新增陳家堡，**不擠掉原版聚落、不崩**。
  - 缺點：常規區 Size=20 較小、知名度低（`Fame=0`），但對「最小可行小派」完全夠用。
- **方案 ②（取代槽，不加長）— 把某 3 聚落 area 的一個 `OrganizationId[i]` 直接改成 42**：
  - 例如 area 16：把 `OrganizationId[1]`（原 37 Town）改成 42，`SettlementBlockCore[1]`（原 35）改成 19。長度仍 3 → `SettlementInfos[3]` OK。
  - 優點：陳家堡進入地廣、知名的少林門派區（Size=30）。
  - 缺點：**少一個原版城鎮（Town）**——這正是 `plan.md §9` 決策點 2「取代 vs 新增」的取代路線。

> 折衷建議：**先用方案 ①（常規區加長到 2）驗證整條鏈不崩、聚落可見可進**，因為它最接近 Phase 0「新增槽位」的原意又零破壞；確認後若要更顯眼再評估方案 ②。
> 兩方案的反射程式幾乎一樣（§5.2），只差「目標 area id」「append 或覆寫某 index」「最終長度是否 ≤3」。**§5.2 的 `PlaceOnMap()` 須加一個防呆：若 `newOrg.Length > 3` 直接放棄並記 error**，以免誤打 3 聚落區。

### 6.0.2 對 §5.2 程式雛形的修補（已內嵌）
§5.2 的 `PlaceOnMap()` 已：①預設 `TargetMapAreaId = 31`（常規區，方案 ①）；②在建新陣列前加 `oldOrg.Length + 1 > 3` 上限防呆（對齊 `MapAreaData.SettlementInfos[3]`）。
若改走方案 ②（取代 area 16 槽，不加長），則不用 append，而是覆寫某 index：
```csharp
// 方案 ②：area 16，把第 1 槽（原 Town 37 / block 35）改成陳家堡（42 / block 19），長度仍 3。
int slot = 1;
sbyte[] newOrg = (sbyte[])oldOrg.Clone();  short[] newBlock = (short[])oldBlock.Clone();
newOrg[slot] = ChenJiaBaoTemplateId;        // 42
newBlock[slot] = ChenJiaBaoBlockTemplateId; // 19
fOrg.SetValue(area, newOrg);  fBlock.SetValue(area, newBlock);
```

## 6.1 其他風險
- **block 衝突 / 重疊**：由引擎 `GetStaticBlockPosRandomPool`/重疊排除處理（`MapDomain.cs:4610/4571-4592`）；風險低，唯一硬例外是 area too small（`:4595`）——常規區 Size=20 放 2 個聚落仍綽綽有餘。
- **area too small 後備**：若選定 area 真擺不下，捕捉不到例外（在世界生成期、非 plugin 期）→ 改用更大的 area 或方案 ②取代槽。
- **前端地圖是否需同步**：
  - 世界生成（聚落放置）只在 **backend**（`Program.cs` 進程）跑，讀 **backend** `GameData.dll` 的 `Config.MapArea`。`MapDomain` 在 `GameData/GameData/Domains/Map/`，綁的是 `GameData/Config/MapArea.cs`（`namespace Config`）。
  - 存在第二份 `GameData.Shared/Config/MapArea.cs`（`namespace Config`，`:166` 另一個 `Instance`）供前端 UI；但**前端地圖顯示的聚落來自存檔內的 `MapAreaData.SettlementInfos`（執行期生成資料，型別在 `GameData.Shared`，前後端共用同一份序列化資料）**，不是前端 re-run 放置邏輯。
  - ⇒ **理論上前端 `MapArea` config 不需同步改**：陳家堡聚落一旦由 backend 生成寫入 `SettlementInfos`，前端讀存檔即可顯示。**但** Phase 1 已確認門派**名稱**顯示要前後端各注入一次（`Organization` config）——地圖上聚落的「名稱/門派歸屬」顯示仍依賴前端 `Organization[42]` 存在（Phase 1 範疇）。**地圖 area config 本身（`MapArea`）預期只需 backend 改。** 此點列為**實測項**，非已證實。
  - Phase 1 csproj 同時引用 `GameData.dll` + `GameData.Shared.dll`（`ChenJiaBao.Backend.csproj:27-28`），`using Config;` 解析到哪個 `MapArea` 取決於型別繫結（見 `details/dual_assembly_type_conflict.md`，0.0.79.60 已不需 extern alias）。**backend plugin 改的應是 backend `GameData.dll` 的 `MapArea.Instance`**（與 Phase 1 `Organization.Instance` 同一條路、已驗證可寫）。
- **存檔相容**：陳家堡靠世界生成擺放 → **只影響新開的世界**；既有存檔不會長出它（與 Phase 0 §6 一致）。`MapAreaData.SettlementInfos[3]` 序列化格式不變（我們維持 ≤3），**舊存檔讀取不受影響**。
- **冪等 / 重複載入**：`PlaceOnMap()` 內含「已含 42 則略過」防呆（§5.2）；避免重複載入把陣列越加越長。

## 6.2 實機驗證步驟（給後續施工 / 不在本 Phase 執行）
1. 部署 backend plugin（含 Phase 1 org 注入 + 本 Phase `PlaceOnMap()`，目標 area=31、方案 ①）。
2. 啟動遊戲，看 backend log：應有「陳家堡注入成功」（Phase 1）＋「陳家堡上地圖：area 31 聚落槽 1 -> 2」（本 Phase）。
3. **開新世界**（非讀舊檔），等世界生成完成、不崩（特別盯 `MapDomain.cs:4105` 與序列化斷言 `MapAreaData.cs:141`）。
4. 開地圖找 area 31，確認多出一個聚落、可進入、顯示為門派（名稱「陳家堡」需 Phase 1 前端名稱注入到位）。
5. 進入後確認成員依 `Members[9]` 生成（Phase 0 §2）、可加入、傳武。
6. 存檔再讀檔，確認 `SettlementInfos` 序列化往返正常（驗證 ≤3 未破壞存檔格式）。
7. 若改用方案 ②（取代 area 16 槽），改盯 area 16 是否少一個原版城鎮、陳家堡取而代之。

## 7. 結論速覽
- 平行對應：`SettlementBlockCore[i]` ↔ `OrganizationId[i]` 等長對應，全 120 個一般 area 零例外（§1.4）。**成立。**
- `SettlementBlockCore[i]` 是 **block 模板 id（MapBlock.TemplateId）**，引擎自動找空位（§1.3/§3.1）——不需手算座標。
- 注入時機：`MapArea.Init()`（`Program.cs:46`）嚴格早於 plugin `Initialize()`（`:52`）→ 放 `Initialize()` 內安全（§4）。**成立。**
- **重大阻斷器**：`MapAreaData.SettlementInfos` 硬限 3（§6.0）→ **不能把 3 聚落區加長到 4**。修正策略＝在常規區（1 聚落）加長到 2（方案 ①，建議），或取代既有槽（方案 ②）。
- 反射雛形：§5.2 + §6.0.2 上限防呆，已就緒，整合進 `Plugin.Initialize()` 的 `PlaceOnMap()`、在 `InjectChenJiaBao()` 之後呼叫。

## §8 落點修正（換離死地）

> 任務：把陳家堡上地圖落點從 area config TemplateId=31（會變死地）換到「開局必生、不會死地」的可靠區，重編部署。事實來源 `~/dev/taiwu-src/backend/`。

### 8.1 死地機制（為何 area 31 整區不生聚落）— 已釘死
世界生成 `CreateStateAreas`（`MapDomain.cs:3782`）：15 個行政區(state)，每 state 佔 3 個 runtime area，runtime `areaId = stateId*3 + stateAreaIndex`（`:3809`），故 area 0–44 是正常區、45+ 是破碎之地。
- `stateAreaIndex` switch（`:3810-3815`）：0→`stateConfig.MainAreaID`（城市）、1→`stateConfig.SectAreaID`（門派區）、2→`thirdAreaTemplateId`（第三區）。
- **第三區候選池**：把 area config TemplateId **≥31**（`MapArea.Instance.GetAllKeys()[i>=31]`，`:3786`）按 `StateID` 分組進 `thirdAreaDict`（`:3786-3796`）。
- **每個 state 只從自己的候選池隨機抽 1 個**當第三區（`:3806` `Random.Next`），其餘候選**全部丟進 `brokenAreaTemplateIdList`（`:3827-3828`）→ `CreateBrokenArea`（`:3844`）做成破碎之地**。
- `CreateBrokenArea`（`:4338-4368`）只放廢墟 block（ruinPool id 118–123，`:3831-3836`）＋一個 station(38)（`:4364`），`Discovered=false`（`:4361`），**完全不呼叫 `CreateSettlement`** → 死地不生任何聚落。
- ⇒ **死地一句話**：area config TemplateId 31（洛陽）是「第三區候選」，每個 seed 大機率落選 → 被做成破碎之地（廢墟、不生聚落）→ 改在它上面的陳家堡隨之消失。

### 8.2 哪些區「開局必生、絕不死地」— 已釘死
- **stateAreaIndex=0（MainArea 城市）與 stateAreaIndex=1（SectArea 門派區）固定**用 `MainAreaID`/`SectAreaID`（`:3812/3813`）→ 每 state 都會跑 `CreateNormalArea`（`:3825`）正常生聚落，**永遠不進 brokenAreaTemplateIdList**。
- 京畿 state（`MapState.cs:73` `new MapStateItem(1,1,1,16,1,...)`，建構子 arg2=MainAreaID=1、arg3=SectAreaID=**16**，欄位 `MapStateItem.cs:41/42`）→ **area config TemplateId 16（嵩山/少林門派區）= 京畿 SectArea，每局必生，零死地風險。**

### 8.3 太吾村所在區 — 為何不選（不可行）
- `taiwuVillageInArea = (areaConfigData.StateID == GetTaiwuVillageStateTemplateId() && indexInState==2)`（`MapDomain.cs:3872`）→ **太吾村固定在其 state 的 stateAreaIndex=2（第三區）**。
- 但「第三區」的 TemplateId 是該 state 候選池隨機抽出（`:3806`），且 `TaiwuVillageStateTemplateId` 由玩家開局選（`WorldDomainHelper.cs:51` 預設 21，實際 `ProtagonistCreationInfo.cs:31`）。
- ⇒ **太吾村所在 area 的 config TemplateId 每個 seed 都不同，plugin `Initialize()`（世界生成前）無法預知**；且若硬改某個 ≥31 TemplateId，該 TemplateId 大概率落選變死地 → 與現況同病。**故太吾村區方案不可行，排除。**
- 太吾村座標 = `GetTaiwuBuildingAreas()[0]`（`TaiwuDomain.cs:10565-10568`），執行期才登記（`MapDomain.cs:4140` `AddTaiwuBuildingArea`），更證實無法靜態指定。

### 8.4 決策：嵩山 area config TemplateId 16，取代槽（方案②）
- 選 **TemplateId 16（嵩山/少林門派區，DefIcon `MapGangShaolin`，Size 30）**。理由：①SectArea 每局必生、零死地（最高優先＝可靠）；②與陳家堡（克隆少林 id=1）主題契合；③玩家在京畿/少林一帶好找。
- area 16 現有 3 聚落（`OrganizationId={1,37,38}`、`SettlementBlockCore={19,35,36}`，`MapArea.cs:2451` 上方 `arg275/arg276`）→ **已達 `SettlementInfos[3]` 硬限（`MapAreaData.cs:70/141/182`），不能 append，只能取代槽**。
- **取代 index 1**（原 Town 37 / block 35）→ 改成 42（陳家堡）/ 19（ShaolinPai Sect block）。長度維持 3。
- **犧牲**：少林門派區內一個普通城鎮(Town, org 37)，換成陳家堡。保留少林本體(index 0)與 WalledTown(index 2)。

### 8.5 實作 / 編譯 / 部署 — 已完成
- `Backend/Plugin.cs`：常數改 `TargetMapAreaId = 31 → 16`；新增 `ReplaceSlotIndex = 1`；`PlaceOnMap()` 由「append 一格」改為「取代槽」：
  - 移除 `oldOrg.Length+1>3` append 上限防呆，改為 `ReplaceSlotIndex` 範圍防呆（`<0 || >=length` 放棄）。
  - 用 `oldOrg.Clone()/oldBlock.Clone()` 後覆寫 `[1]`：`OrganizationId[1]=42`、`SettlementBlockCore[1]=19`，長度維持 3（`SettlementInfos[3]` 不溢位、存檔格式不變）。
  - 保留原防呆：`area==null`、反射欄位取不到、兩陣列等長斷言、冪等「已含 42 略過」。
  - log 改印：最終 area 16（標註「嵩山/少林門派區，必生不死地」）、策略（取代槽）、覆寫的 index、被犧牲的原 org/block。
- 編譯：`dotnet build -c Release` → **Build succeeded, 0 Warning / 0 Error**。
- 部署：`ChenJiaBao.Backend.dll` 已覆蓋到 `.../The Scroll Of Taiwu/Mod/ChenJiaBao/Plugins/`（Config.lua 未動）。

### 8.6 對原聚落的影響、找法、風險
- **犧牲**：少林門派區(area 16)內 index 1 的普通城鎮（org 37 Town / block 35）被陳家堡(42 / Sect block 19)取代。保留少林本體(index 0, org 1)、WalledTown(index 2, org 38)。少林區聚落數仍 3。
- **找法**：開**新世界**（舊存檔不長出陳家堡），到京畿（少林所在那一州）的少林門派區，找一個少林同區的門派型聚落即陳家堡。
- **最大風險**：area 16 是 Size 30 的門派區（原本就放得下 3 聚落，本次只換內容不加量）→ `area too small`（`MapDomain.cs:4595`）不會觸發；唯一殘留風險＝若其他 mod 也改 area 16 的 index 1 槽或改 area config TemplateId 對位，會互相覆蓋（冪等防呆只擋「已含 42」，不擋他 mod 佔同槽）。前端地圖名稱/門派歸屬仍依賴 Phase 1 前端 Organization[42] 注入（已部署）。

---

## §9 改放太吾村起始區（runtime Harmony）

> 任務：把陳家堡落點從靜態 area config 16(嵩山) 改成「玩家開局太吾村所在的起始區」，玩家一開局就在旁邊必找得到。
> 因太吾村區的第三區 config TemplateId 是世界生成隨機抽（plugin Initialize 當下不可知），改用 **Harmony Prefix 在世界生成當下動態改 config**。事實來源 `~/dev/taiwu-src/backend/`。逐項回源覆核並標 path:line。

### §9.1 為何 runtime patch（靜態不可行）— 回源確認
- 太吾村固定在其 state 的第三區：`taiwuVillageInArea = areaConfigData.StateID == DomainManager.World.GetTaiwuVillageStateTemplateId() && indexInState == 2`（`MapDomain.cs:3872`；另一處同條件 `:3820`）。
- 第三區 config TemplateId 由該 state 候選池**隨機抽**：`thirdAreaTemplateId = thirdAreaList[context.Random.Next(thirdAreaList.Count)]`（`MapDomain.cs:3806`），候選池＝所有 TemplateId≥31 的 area config 按 StateID 分組（`:3786-3796`）。
- 太吾村所在 state 由玩家開局選：`GetTaiwuVillageStateTemplateId()` 回傳 `_taiwuVillageStateTemplateId`（`WorldDomain.cs:8902-8905`），預設 21（`WorldDomainHelper.cs:51`），實際由 `SetWorldCreationInfo`（`WorldDomain.cs:759`，吃 `info.TaiwuVillageStateTemplateId`）設定。
- ⇒ plugin `Initialize()`（世界生成前）**無法預知**是哪個 config TemplateId、StateID 是多少 → **靜態改 config 行不通**；但世界生成當下 `_taiwuVillageStateTemplateId` 已設，故用 Harmony patch 在生成當下改。

### §9.2 patch 切入點與時機 — 回源釘死
- **patch 目標方法 = `MapDomain.CreateNormalArea`**（`MapDomain.cs:3858`，簽名 `private unsafe void CreateNormalArea(DataContext context, MapAreaData mapAreaData, short areaId, Dictionary<int,List<short>> blockTypeDict, Dictionary<int,List<short>> blockSubTypeDict, int indexInState = -1)`）。
- **用 Prefix**（不 skip 原方法，回傳 void 不攔截）。Prefix 在原方法本體執行**之前**跑，而原方法所有讀 config 陣列的點都在本體內、晚於 Prefix：
  - `areaConfigData = mapAreaData.GetConfig()`（`:3871`）取的是 `MapArea.Instance[TemplateId]` 同一引用 → Prefix 改它的 `OrganizationId/SettlementBlockCore` 後，本體讀到的就是改過的。
  - `settlementCount = areaConfigData.OrganizationId.Length + (taiwuVillageInArea ? 1 : 0)`（`:3879`）→ append 後自動 +1。
  - `PlaceStaticBlocks(... areaConfigData ...)`（`:3902`）內 `staticBlockCore.AddRange(areaConfigData.SettlementBlockCore)`（`:4519`）讀改過的 block 陣列。
  - 聚落生成迴圈 `OrganizationId[i4]`（`:4099`）。
- **時機鏈（嚴格早於本方法）**：`CreateWorld`（`WorldDomain.cs:734`）→ `:737 SetWorldCreationInfo`（內 `:759 SetTaiwuVillageStateTemplateId`）→ `:740 DomainManager.Map.CreateAllAreas` →（map gen）`CreateStateAreas`（`MapDomain.cs:3691`）→ `CreateNormalArea`（`:3825`）。故 Prefix 跑時 `GetTaiwuVillageStateTemplateId()` 已是玩家選定值，可靠。
- **判定太吾村區的條件（Prefix 內重算，與 `:3872` 一致）**：`indexInState == 2 && mapAreaData.GetConfig().StateID == DomainManager.World.GetTaiwuVillageStateTemplateId()`。只在符合時才改 config，其餘 area 一律放行。

### §9.3 append 還是取代槽 — 回源算出（決策＝append，不犧牲任何原聚落）
- 全 89 個第三區候選 config（TemplateId 31–119）經機器掃描：**`OrganizationId.Length` 全部 == 1、`SettlementBlockCore.Length` 全部 == 1，零例外**（解析 `MapArea.cs` 全部 `new MapAreaItem(...)`，arg17=org / arg16=block，取最近前置 `argNNN` 定義；範例 area 31：`arg515={35}`(`MapArea.cs:4462`)、`arg516={37}`(`:4463`)）。
- 太吾村區當下聚落數 = `OrganizationId.Length(1) + 太吾村(+1) = 2`（`MapDomain.cs:3879`）→ **還有 1 格空間（`SettlementInfos[3]` 硬限，`MapAreaData.cs:70/141/182`）**。
- ⇒ **決策＝append**：把陳家堡(42 / block 19) 加到 config 兩陣列尾端 → 聚落數變 3（原城鎮 + 陳家堡 + 太吾村），**≤3、不溢位、不犧牲任何原聚落**。
- **索引對位正確性（關鍵覆核）**：太吾村 block(id 0) 在 `PlaceStaticBlocks` 內被 append 到 `staticBlockCore` **最尾端**（`:4524`，在 `AddRange(SettlementBlockCore)` 之後）；且太吾村判定是 `index == areaConfigData.SettlementBlockCore.Length`（`:4597`/`:4601`）與聚落迴圈 `i4 == settlementCount-1`（`:4098`）＝同一邊界。我們對 `SettlementBlockCore` append 一格只是把該邊界右移一格，陳家堡落在新的 index 1，太吾村仍在最尾、用 org 16（`:4099`）。**append 後對位仍精確，太吾村不受影響。**

### §9.4 防呆（全保留，後端未捕捉例外＝整個 GameData 崩潰）
- 整個 Prefix 包 try-catch，例外只記 log、放行原方法（不中斷世界生成）。
- 早退條件：`indexInState != 2` 或非太吾村 state → 直接 return（對其他 area 零副作用）。
- 反射欄位取不到（`OrganizationId`/`SettlementBlockCore` 改版）→ 記 error、放棄改寫、放行。
- 兩陣列 null / 長度不一致 → 放棄。
- 冪等：config 已含 org 42 → 略過（防同一 config 物件被多次抽中為不同 seed 第三區時重複 append；config 是 `MapArea.Instance` 單例，跨 state 迴圈共用）。
- 上限：append 後總聚落數（含太吾村 +1）`> 3` → 不 append，改**取代** config 最後一個非太吾村槽（覆寫 index `Length-1`，長度不變，仍 ≤3）。理論上候選恆為 1 聚落故走 append，取代分支為防呆後備。

### §9.5 對 InjectChenJiaBao / SeniorityGroupId 的影響
- `InjectChenJiaBao()`（org 42 克隆少林、沿用 SeniorityGroupId）**完全不動**——僧侶法號字庫依賴它（`CharacterDomain.cs:15328`），改 -1 會崩。
- 移除 `Initialize()` 內的靜態 `PlaceOnMap()` 呼叫（不再改 area 16），保留方法本體於檔內當註解參考但不再被呼叫（或刪除）。

### §9.6 玩家開局後在哪找陳家堡
- 開**新世界**（runtime patch 只影響新生成的世界，舊存檔不長出）。
- 陳家堡會生在**太吾村所在的那一格起始區**（第三區）裡，與太吾村同 area，玩家開局就在旁邊、必能找到，無需跨州。

### §9.7 風險
- **最大風險（開局極早期/引導）**：patch 在世界生成迴圈中改 config 陣列引用。已確認 append 後索引對位精確（§9.3），太吾村本體生成不受影響（org 16、座標 center），引導階段太吾村相關邏輯（`SetTaiwuVillageSettlementId`，`MapDomain.cs:4109`）讀的是 `isTaiwuVillage` 那一格，與陳家堡無關 → 引導不受影響。
- **area too small**：太吾村區被強制放大成 `TaiwuVillageForceAreaSize`（`MapDomain.cs:3822/3876`），空間更充裕，多放 1 聚落不會觸發 `:4595`。
- **config 單例污染**：`MapArea.Instance[TemplateId]` 是跨整局共用的 config 單例；Prefix 改它後該 TemplateId 的 area 永久帶陳家堡。但因冪等防呆 + 只在「該 config 當太吾村第三區」時改，且每局世界生成前 config 由 `ReloadAllConfigData` 重建（plugin Initialize 在其後、patch 在更後的世界生成期）→ 同進程連開多世界時，第二局可能命中已被改過的 config（冪等防呆擋住重複 append，但若第二局太吾村在不同 state，舊被改的 config 仍帶 42）。**殘留風險：同進程連開多個不同 state 的新世界，先前被改的 config 不會還原** → 列為已知限制（單局遊玩無影響；重啟遊戲即還原）。
- **其他 mod 衝突**：若他 mod 也 patch `CreateNormalArea` 或改同 config，順序未定可能互蓋；冪等只擋「已含 42」。

---

## §10 ⚠️ 推翻 §9「append」決策：太吾村家園寫死 `SettlementInfos[1]` → 改「取代原城鎮槽」（2026-05-23 實機 crash 修復）

**症狀（實機）**：開新世界、玩到主線進度 8，**點擊「陳家堡的產業」→ 前端 Unity NullReferenceException → 遊戲 crash**。
（門派按鈕、過月、成員名等其餘功能皆正常；唯獨產業會炸。）

**crash 堆疊（前端 Player.log）**：
```
NullReferenceException
  at BuildingModel.GetBuildingLevel(BuildingBlockKey, BuildingBlockData) [0x00094]   ← BuildingModel.cs:560
  ← UI_BuildingArea.UpdateBlockInfo  (:1389)
  ← UI_BuildingArea.UpdateBlock      (:1348)
  ← UI_BuildingArea.InitBuildingArea (:881)
  ← UI_BuildingArea.OnNotifyGameData (:737)
（另一條同源：← UI_BuildingArea.SetBuildingLevelText :2120）
```

**根因（反編譯實裝 0.0.79.60 `Assembly-CSharp.dll`，ilspycmd + ikdasm 雙確認）**：
`BuildingModel.GetBuildingLevel` 兩分支——
```csharp
Location taiwuVillageBlock = WorldMapModel.GetTaiwuVillageBlock();
BuildingBlockItem cfg = BuildingBlock.Instance[blockData.TemplateId];
if (taiwuVillageBlock != blockKey)                       // 一般聚落 → 安全
    return Math.Min(blockData.Level, cfg.MaxLevel);
// 否則＝這格被判定為「太吾村家園 block」：
... var ex = _buildingBlockDataExDict.GetValueOrDefault(blockKey);   // class，查無 → null
return ex.CalcUnlockedLevelCount();                      // IL offset 0x94：對 null callvirt → NRE
```
crash 在 offset `0x94` = 家園分支的 `CalcUnlockedLevelCount()`。亦即**看陳家堡產業時 `blockKey` 竟等於 `GetTaiwuVillageBlock()`**。

而 `GetTaiwuVillageBlock()` / `GetTaiwuVillageSettlementId()` 把家園**寫死在 `SettlementInfos[1]`**：
```csharp
public Location GetTaiwuVillageBlock()    => new(村區AreaId, Areas[村區].SettlementInfos[1].BlockId);
public short    GetTaiwuVillageSettlementId() =>          Areas[村區].SettlementInfos[1].SettlementId;
//   村區AreaId = (TaiwuVillageStateTemplateId-1)*3+2（GetTaiwuVillageAreaId，= 第三區，與 §9 area 判定一致）
```

**§9「append」的致命錯誤**：起始區聚落填充順序＝org 聚落填 `SettlementInfos[0..Length-1]`、太吾村家園永遠由引擎 append 在**最後**（index `Length`）。原版該區 `OrganizationId.Length==1` → `[0]=原城鎮、[1]=太吾村家園`，**故遊戲寫死讀 `[1]`**。
我們 append 陳家堡使 `OrganizationId` 變長 2（`[原城鎮, 42]`）→ 聚落變 `[0]=原城鎮、[1]=陳家堡、[2]=家園`：
- **家園被擠到 `[2]`，`SettlementInfos[1]` 變成陳家堡** → `GetTaiwuVillageBlock()` 回傳的「家園」其實是陳家堡。
- 點陳家堡產業：`blockKey(陳家堡) == GetTaiwuVillageBlock()(也=陳家堡)` 成立 → 誤入家園分支 → `_buildingBlockDataExDict` 只含真家園 block、查無陳家堡 → null → **NRE crash**。
- **更嚴重的潛在後果**：家園身分被劫持，`IsAtTaiwuVillage` / 主線進度判定（`MainStoryLineProgress`）/ BGM 等所有讀 `SettlementInfos[1]` 的邏輯全指向陳家堡（crash 只是最先冒出的症狀）。

> §9.3 當時覆核「索引對位」只驗了**太吾村 block 仍在 staticBlockCore 最尾**（位置正確），卻**漏看前端 `GetTaiwuVillageBlock` 把家園寫死在 `SettlementInfos[1]`**——位置正確 ≠ 寫死索引正確。教訓：改動「按固定 index 取用」的陣列前，要把**所有寫死該 index 的取用端**一起 grep（前後端皆是）。

**修法（已實作、已部署）＝改 append 為「取代原城鎮槽」**：覆寫 `OrganizationId[0]`（起始區唯一的 org 城鎮槽）為陳家堡 42 / block 19，**`OrganizationId.Length` 維持 1**：
- 聚落仍為 `[0]=陳家堡、[1]=太吾村家園` → 所有寫死 `SettlementInfos[1]==家園` 的假設不破。
- 點陳家堡產業：`blockKey(陳家堡=[0]) != GetTaiwuVillageBlock()(=[1]家園)` → 走安全分支 `Math.Min(level, cfg.MaxLevel)`，不再 NRE。
- **代價**：起始區原本那個普通城鎮被陳家堡取代（仍在起始區、好找；主題上「太吾村旁有座陳家堡」反而更乾淨）。
- `Backend/Plugin.cs` 的 `CreateNormalArea_Patch.Prefix` 已將 append/取代雙分支整段換成「取代 index 0」單路徑，移除 `MaxSettlementsPerArea` 常數。`Build 0/0`、已部署。

**通則（補入「第 16 派踩雷」清單）**：把新門派放進「**太吾村起始區**」時，**不可增加該區 `OrganizationId` 長度**（家園寫死 `SettlementInfos[1]`，增長即劫持家園身分）。**必須取代既有 org 城鎮槽**（長度不變）。此限制專屬太吾村起始區；門派區（如 area 16）無此寫死、取代槽是因 `SettlementInfos[3]` 上限。

**待驗證**：須開**新世界**（patch 只影響世界生成；舊存檔家園已被劫持、無法熱修）。新世界中：起始區應見「太吾村家園 + 陳家堡」兩聚落、**點陳家堡產業不再 crash**、家園相關（主線/BGM/IsAtTaiwuVillage）正常。
