# 太吾繪卷 0.0.79.60 — 產業視圖與建築系統逆向調查

> 調查員：建築系統逆向組　日期：2026-05-23
> 事實來源：實裝版 0.0.79.60（前端 `Assembly-CSharp.dll`、後端 `GameData.dll` / `GameData.Shared.dll`），已用 `ilspycmd` 對關鍵方法/型別反編譯驗證。
> 舊版反編譯源（`~/dev/taiwu-src/`）僅供 grep/型別關係瀏覽；凡標「(實裝驗證)」者已對 DLL 核對。

---

## 0. 名詞與檔案速查

| 概念 | 型別 | 位置 |
|---|---|---|
| 一個地格上的「建築/資源」單元（運行時資料） | `BuildingBlockData` | `GameData.dll` → `GameData/Domains/Building/BuildingBlockData.cs`（舊源 `Assembly-CSharp/GameData/Domains/Building/BuildingBlockData.cs`） |
| 定位某地格建築的鍵（AreaId+BlockId+格內 index） | `BuildingBlockKey` | `GameData/Domains/Building/BuildingBlockKey.cs` |
| 建築「型錄」設定（每個 TemplateId 一筆） | `BuildingBlockItem`（config） | `GameData.Shared.dll` → `Config.BuildingBlockItem`（實裝驗證） |
| 建築型錄容器 | `BuildingBlock : ConfigData<BuildingBlockItem, short>` | `GameData.Shared.dll` → `Config.BuildingBlock`（實裝驗證） |
| 產業視圖（地格網格 UI，點建築入口） | `UI_BuildingArea` | 前端 `Assembly-CSharp.dll`（舊源 4701 行 / 實裝 4309 行） |
| 點開單一建築的管理彈窗 | `UI_BuildingManage` | 前端 |
| 建造選單（列出可建建築） | `UI_BuildingOverview` | 前端 |
| 後端建築領域 | `BuildingDomain` | `GameData.dll` → `GameData/Domains/Building/BuildingDomain.cs`（實裝 18773 行） |
| 聚落 / 門派 / 平民聚落 | `Settlement`(abstract) / `Sect` / `CivilianSettlement` | `GameData.dll` → `GameData/Domains/Organization/` |
| 地格上的聚落索引資料 | `SettlementInfo` | `GameData/Domains/Map/SettlementInfo.cs` |
| 商會（商人系統） | `Config.MerchantTypeItem` / `Config.MerchantType` | `GameData.Shared.dll`（實裝驗證） |
| 商店事件（商品/資源/募人資料） | `Config.ShopEventItem` / `Config.ShopEvent` | `GameData.Shared.dll`（實裝驗證） |

---

## 1. 點擊觸發鏈（從世界地圖到單格建築彈窗）

### 1.1 入口：世界地圖上點聚落「進入產業」
`MapElementSettlementBtn`（前端，`Assembly-CSharp/MapElementSettlementBtn.cs`）是世界地圖上每個聚落的按鈕集合。它在初始化時綁定多個子按鈕（`MapElementSettlementBtn.cs:131-140`）：
- `EnterBuildingArea` → `OnClickBuilding()`（進入產業視圖）
- `SettlementInformation` → `OnClickInfo()`（聚落資訊）
- `Warehouse` → `OnClickWarehouse()`
- `CombatSkillTree`（門派）→ `OnClickSect()`（僅 `OrgTemplateId>=0 && Organization.Instance[OrgTemplateId].IsSect`，見 `:231`）
- `Merchant` → `OnClickMerchant()`

`OnClickBuilding()`（`MapElementSettlementBtn.cs:303-330`）流程：
1. 若該地格 `== WorldMapModel.GetTaiwuVillageBlock()` 且處於「歸夢」未解鎖狀態 → 走劇情鉤子 `TaiwuCrossArchiveFindMemory(4)` 後 return。
2. 否則打包 `AreaId`/`BlockId` 進 `ArgumentBox`，設給 `UIElement.BuildingArea` 與 `UIElement.BuildingBlockList`，最後 `CommandManager.AddCommandStackUI(EPriority.StackUINormal, UIElement.StateBuilding)` 開啟產業視圖。

→ **太吾村家園與其他聚落用同一個 UI（`UI_BuildingArea`），差異靠後續分支區分。**

### 1.2 產業視圖建立每格：`UI_BuildingArea`
- `OnInit/InitData` 時 `_isTaiwuVillage = _worldMapModel.IsAtTaiwuVillage(_areaId, _blockId)`（`UI_BuildingArea.cs:485`，`IsAtTaiwuVillage` 定義於 `WorldMapModel.cs:2078`）。此布林是後面所有「家園 vs 非家園」分支的開關。
- 每格由 `CreateBlock(index, blockWidth)`（`UI_BuildingArea.cs:1047`）建立，並綁定點擊：`btn.ClearAndAddListener(() => BuildingIconClick(blockRefers))`（`:1059-1062`）。
- 取格資料：`_blockList[index]`（`BuildingBlockData[]`，從後端 `BuildingDomainHelper.MethodCall.GetBuildingBlockList(listenerId, new Location(areaId, blockId))` 取回，見 `:658`）。設定資料：`config = BuildingBlock.Instance[blockData.TemplateId]`（`:1153`）。

### 1.3 點一格 → `BuildingIconClick` → `OpenBuildingManage`
`BuildingIconClick(blockRefers)`（`UI_BuildingArea.cs:1086`）：
- 若處於「移動/重置建築規劃」模式 → `SetBlockToEmpty(...)`。
- 否則 → **`OpenBuildingManage((short)blockRefers.UserInt)`**（核心分流）。

### 1.4 核心分流：`OpenBuildingManage(short blockIndex)`（實裝驗證，`UI_BuildingArea.cs:3579`）
實裝 0.0.79.60 反編譯結果（與舊源略有差異，已重寫為實裝版）：

```csharp
short templateId = _blockList[blockIndex].TemplateId;
if (!_isTaiwuVillage && templateId == 48)            // 非家園的「倉庫(48)」直接開倉庫 UI
    UIManager.Instance.ShowUI(UIElement.Warehouse);
else if (IsSectSpecialBuilding(templateId))          // 門派特殊建築 → 觸發事件
    TaiwuEventDomainMethod.Call.OnSectSpecialBuildingClicked(templateId);
else if (IsSettlementTreasuryBuilding(templateId))   // 聚落金庫(284~302) → 觸發事件
    TaiwuEventDomainMethod.Call.SettlementTreasuryBuildingClicked(templateId, 0, 0);
else if (IsSettlementPrisonBuilding(templateId))     // 聚落牢房(303~317)
    OrganizationDomainMethod.AsyncCall.IsTaiwuSectFugitive(this, cfg.BelongOrganization, cb => {
        if (是太吾門派逃犯) TaiwuEventDomainMethod.Call.OnSectBuildingClicked(templateId); // 觸發事件
        else                ShowBuildingManage(blockIndex, templateId);                   // 開管理彈窗
    });
else {                                                // 一般情形
    ShowBuildingManage(blockIndex, templateId);                                            // 開管理彈窗
    DelayCall(() => TaiwuEventDomainMethod.Call.OnSectBuildingClicked(templateId), 1f);    // 並補觸發事件
}
```

> 補充：舊源還有「非家園 + `IsUsefulResource` → `EnterResourceOfferUpMenuMode`」分支（`UI_BuildingArea.cs:3520-3527`，奉獻資源給聚落支援）；實裝把這個入口改由 `BuildingBlockCanInteractable` + 別處處理。`BuildingBlockCanInteractable`（`:774`）決定一格能否點：`_isTaiwuVillage || (cfg.canOpenManageOutTaiwu && _canUseBuilding) || (主線>=8 且 IsUsefulResource) || templateId==48 || ==49`。

### 1.5 「跳出」的東西有三類
1. **管理彈窗** `ShowBuildingManage` → 開 `UIElement.BuildingManage`（`UI_BuildingArea.cs:3634`），並發 `UiEvents.NotifyOpenBuildingManage`。彈窗內容由 `UI_BuildingManage` 依 `templateId` 再細分（見 §4）。
2. **遊戲事件**：`OnSectBuildingClicked` / `OnSectSpecialBuildingClicked` / `SettlementTreasuryBuildingClicked`（→ 後端事件系統，見 §5）。
3. **交易/商店視窗** `UIElement.Shop`：不是在 `OpenBuildingManage` 直接開，而是先開 `UI_BuildingManage`，由其中的「商會」按鈕開（見 §4）。

---

## 2. 建築型別分類

### 2.1 `EBuildingBlockType`（實裝驗證，`GameData.Shared.dll`）
```
Invalid = -1, NormalResource(0), SpecialResource(1), UselessResource(2),
Building(3), MainBuilding(4), Empty(5), Count(6)
```
語意（`BuildingBlockData` 靜態方法，`BuildingBlockData.cs`）：
- `IsBuilding(type)` = `Building || MainBuilding`
- `IsResource(type)` = `NormalResource || SpecialResource || UselessResource`
- `IsUsefulResource(type)` = `NormalResource || SpecialResource`（可奉獻/可升級）
- `CanUpgrade(type)` = `IsBuilding || NormalResource`
- `UselessResource`＝廢棄/無用資源點（如荒地），不可建管理選單。

### 2.2 `EBuildingBlockClass`（功能分類，實裝同舊源）
`Static, BornResource, Villiage, Resource, Function, Kungfu, Music, Chess, Poem, Painting, Math, Appraisal, Forging, Woodworking, Medicine, Toxicology, Weaving, Jade, Taoism, Buddhism, Cooking, Eclectic`。
建造選單 `UI_BuildingOverview.InitData`（`:518`）只收 `Class >= BornResource && Type != UselessResource` 的型錄並按 `Class` 分頁。

### 2.3 各型別點擊行為差異（綜合 §1.4 與 §4）
| 型別 / TemplateId 段 | 分類 | 點擊行為 |
|---|---|---|
| `Empty`(空地) | — | 不可點（建造模式下才用來放建築） |
| `UselessResource`(廢資源) | 不可互動 | 一般不開管理 |
| `NormalResource`/`SpecialResource`(可用資源) | 資源 | 家園→管理；非家園→奉獻資源支援聚落（`EnterResourceOfferUpMenuMode`） |
| `Building`/`MainBuilding`(建築/主建築) | 建築 | 開 `UI_BuildingManage` |
| 民居/作坊/商店(46,47,48,49,121,122,…,作坊段) | 建築 | 開 `UI_BuildingManage`（內含經營/作物/募人/商店） |
| 門派建築 239~253 (`SectBuildingIdList`) | 門派 | `ShowBuildingManage` + `OnSectBuildingClicked` 事件 |
| 門派特殊建築 239,244,259~273 (`SectSpecialBuildingIdList`) | 門派特殊 | `OnSectSpecialBuildingClicked` 事件（不開管理） |
| 城市建築 224~238,254~256 (`CityBuildingIdList`) | 城市 | 開管理 |
| 太吾建築 44,257,258 (`TaiwuBuildingIdList`) | 太吾 | 開管理 |
| 商會 274~280 / 318 | 商會 | 管理彈窗→「商會」鈕→開 `UIElement.Shop` 交易 |
| 聚落金庫 284~302 | 金庫 | `SettlementTreasuryBuildingClicked` 事件 |
| 聚落牢房 303~317 | 牢房 | 視是否太吾門派逃犯 → 事件 or 管理 |

（ID 段定義：`UI_BuildingArea.cs:152-170` `SectSpecialBuildingIdList/CityBuildingIdList/TaiwuBuildingIdList/SectBuildingIdList`；治理段 `IsSettlementTreasuryBuilding`=284~302、`IsSettlementPrisonBuilding`=303~317，見 `:2336-2348`。重要型錄常數見 `Config.BuildingBlock.DefKey`，例 `Residence=46, Warehouse=48, ChickenCoop=49, TeaHouse=121, Tavern=122, ForgingRoom=129, GamblingHouse=215, Brothel=216, Pawnshop=222, ExcellentPersonShop=223` 等。）

---

## 3. 非太吾村狀況（家園 vs 一般聚落）

決定分支的核心開關 `_isTaiwuVillage`（`UI_BuildingArea.cs:485`，來自 `WorldMapModel.IsAtTaiwuVillage`），以及後端用 `WorldMapModel.GetTaiwuVillageBlock()` 比對地格。差異點：

1. **能否互動/能否建造**：`BuildingBlockCanInteractable`（`:774`）— 非家園時，唯有 `cfg.canOpenManageOutTaiwu` 且 `_canUseBuilding`、或可奉獻資源、或倉庫(48)/雞舍(49) 才可點。建造選單（`UI_BuildingOverview` / `StartPlanBuilding`）實務上只在家園可用（規劃流程綁定 `_isTaiwuVillage`）。
2. **建築等級**：`BuildingModel.GetBuildingLevel`（`/tmp/cjb_decomp/BuildingModel.cs:427`）—
   - 非家園地格：直接 `Min(blockData.Level, cfg.MaxLevel)`。
   - 家園地格：`UselessResource` 回 `blockData.Level`；其餘走 `_buildingBlockDataExDict[(ulong)blockKey].CalcUnlockedLevelCount()`（家園才有逐級解鎖資料 `BuildingBlockDataEx`）。
3. **資源奉獻**：非家園 + 可用資源 → `EnterResourceOfferUpMenuMode`（`:3811`）給該聚落支援，呼 `ExtraDomainHelper.AsyncMethodCall.GetSupportingBuildingBlockDisplayData`。
4. **倉庫**：非家園的倉庫(48)直接開 `UIElement.Warehouse`（實裝 `OpenBuildingManage` 首分支）。
5. **聚落治理建築**（金庫 284~302 / 牢房 303~317）只在「有聚落」的地格才出現，點擊走事件而非一般管理。
6. **取聚落歸屬**：`OrganizationDomainHelper.MethodCall.GetSettlementIdByAreaIdAndBlockId(listenerId, areaId, blockId)`（`:496`）+ `OrganizationDomainHelper.MethodCall.GetSettlementTreasuryDisplayData(...settlementId)`（`:726`）取該地格所屬聚落與金庫資料。

---

## 4. 跳交易/商店視窗

兩條交易路徑：

### 4.1 玩家自營商店（家園的「店鋪」經營）
`BuildingBlockItem.IsShop == true`（實裝 config 欄位）的建築在 `UI_BuildingManage` 內有「店鋪經營」面板（`ShopEvent*` 一整套，`UI_BuildingManage.cs:288-590` 等）。商品/產出資料來源：
- `cfg.SuccesEvent[0]` → `Config.ShopEvent.Instance[...]`（`ShopEventItem`）。其欄位（實裝驗證 `Config.ShopEventItem`）：`ItemList`(賣的物品)、`ResourceGoods`/`ExchangeResourceGoods`(資源交易)、`RecruitPeopleProb`(募人)、`LearnLifeSkill/CombatSkillProb` 等。
- 後端大量以 `Config.ShopEvent.Instance.GetItem(cfg.SuccesEvent[0]).ItemList/ResourceGoods/RecruitPeopleProb` 驅動結算（`BuildingDomain.cs:3282-3307, 12463-12790`，舊源 `11521+`）。
- 店鋪進度 `BuildingBlockData.ShopProgress` / `MaxProduceValue`（`BuildingBlockData.cs`，UI 在 `UI_BuildingArea.UpdateShopProgressInfo :1919`）。

→ **結論：玩家商店的「商品」資料＝建築型錄 `SuccesEvent` 指向的 `ShopEvent` 設定，全是 ConfigData。**

### 4.2 商會（向商人交易）— 實裝驗證 `UI_BuildingManage.cs:3127-3160`
商會建築 **274~280（總號/分號）** 與 **318（特殊）** 在 `UI_BuildingManage` 內產生「商會」按鈕（icon `building_icon_shanghui`），點擊開 `UIElement.Shop`：
```csharp
MerchantTypeItem mt = Config.MerchantType.Instance[_configData.MerchantId];
bool isHead = mt.HeadArea == 本Area的TemplateId;          // 判斷總號/分號
OpenShopEventArguments arg = new() {
    BuildingMerchantType = _configData.MerchantId,          // 商會 = MerchantType
    MerchantSourceType   = isHead ? MerchantHeadBuilding : MerchantBranchBuilding (318→SpecialBuilding)
};
UIElement.Shop.SetOnInitArgs(...); UIManager.Instance.ShowUI(UIElement.Shop);
```
- **商會的身分＝`Config.MerchantTypeItem`**（實裝驗證），欄位含 `HeadArea`(總號所在城市 TemplateId)、`BranchArea`(分號)、`HeadLevel/BranchLevel`、`CityAttributeType`、頭像/對話文案。一個商會＝一筆 `MerchantType`，掛在哪個地格由「商會建築(274~280/318)」放置位置 + `cfg.MerchantId`（指向該 MerchantType）決定。
- 同樣 `MerchantId` 也用於太吾村商人切換（`TaiwuDomain.cs:2538-2561 GetSelectMapBlockHasMerchantId`）。

→ **「跳交易視窗」＝商會建築（274~280/318，`MerchantId>0`）在管理彈窗按商會鈕開 `UIElement.Shop`；交易對象與商品由 `Config.MerchantType` + 商人庫存系統驅動，不是 `ShopEvent`。**

---

## 5. 觸發事件（建築 → 事件系統）

### 5.1 點擊型事件（即時觸發）
`OpenBuildingManage` 分支會呼後端 `TaiwuEventDomainMethod.Call.*`，最終進 `TaiwuEventDomain`（`GameData.dll`）：
- `OnSectBuildingClicked(templateId)` → `OnEvent_SectBuildingClicked` → 廣播給各 `EventManager`（`TaiwuEventDomain.cs:3288, 5773`）。
- `OnSectSpecialBuildingClicked(templateId)` → `OnEvent_OnSectSpecialBuildingClicked`（`:3334, 5872`）。
- `SettlementTreasuryBuildingClicked(templateId)` → `OnEvent_OnSettlementTreasuryBuildingClicked`（`:3413, 6142`）。

這些對應 `Config.EventTriggerType`（`GameData.Shared/Config/EventTriggerType.cs`）的觸發類型：
- `SectBuildingClicked = 17`、`OnSectSpecialBuildingClicked = 20`、`OnSettlementTreasuryBuildingClicked = 22`，且三者 **`allowExternal: true`**（`:298-303`）→ **mod 可掛這些觸發點**。

### 5.2 建築型錄自帶的事件欄位
`BuildingBlockItem`（實裝 config）帶四組事件欄位：
- `SuccesEvent` / `FailEvent`（`List<short>`，多用作店鋪結算 ShopEvent，§4.1；FailEvent 見 `BuildingDomain` 舊源 `3526`）。
- `IdleEvent`（`short`，閒置事件）。
- `SpecialEvent`（`List<ShortList>`，特殊事件組）。
這些是「建築本身配事件」。完工事件另由 `BuildingDomain.TriggerBuildingCompleteEvents`（實裝 `:2205`，新遊戲月 `TaiwuEventDomain.OnNewGameMonth` 也會呼）批量觸發，並讀 `cfg.SuccesEvent[0]`（`BuildingDomain.cs:2167`）。

### 5.3 結論
- **建築本身（型錄）配事件**：`SuccesEvent/FailEvent/IdleEvent/SpecialEvent`（型錄欄位）。
- **點擊行為事件**：由前端依 templateId 段判斷後呼後端 `*Clicked` 觸發點（門派/金庫/牢房）。
- 地格/聚落層級的事件則走聚落本身的劇情任務鏈（`OrganizationItem.TaskChains`），非建築欄位。

---

## 6. 建築 ↔ 組織關聯（關鍵）

### 6.1 運行時資料層：建築**不**存組織 Id
`BuildingBlockData`（實裝）欄位只有：`BlockIndex, TemplateId, Level, RootBlockIndex, Durability, Maintenance, OperationType, OperationProgress, OperationStopping, ShopProgress`。
→ **單格建築運行時資料裡沒有 `OrganizationId` 欄位。** 建築與組織的關係是「間接」的：

```
Area(地格) ──含──> SettlementInfo{ SettlementId, BlockId, OrgTemplateId }   ← 地格層的組織歸屬
        │
        └──> BuildingAreaData(該地格的產業網格) ──含──> BuildingBlockData[]（各格只有 TemplateId）
                                                              │
組織(Sect/CivilianSettlement, OrgTemplateId+Location) ──放置──┘ 透過 PlaceBuildingAtBlock 放特定 templateId
```

- **地格的組織歸屬**：`SettlementInfo{ short SettlementId; short BlockId; sbyte OrgTemplateId; short RandomNameId }`（`GameData/Domains/Map/SettlementInfo.cs:7`）。`MapElementSettlementBtn` 用 `_settlementInfo.OrgTemplateId` 判斷是否門派（`:231`）。
- **聚落本體**：`Settlement`(abstract) 持 `protected sbyte OrgTemplateId; protected Location Location;`（`Organization/Settlement.cs:33-36`）。子類 `Sect` / `CivilianSettlement`。組織型錄 `Config.OrganizationItem`（`OrgTemplateId` 索引）含 `IsSect, IsCivilian, MerchantTendency, MerchantLevel, PrisonBuilding(short 牢房建築 templateId), TaskChains` 等。

### 6.2 組織如何「擁有」建築：靠 PlaceBuildingAtBlock 放在自己 Location
範例：門派牢房放置 `OrganizationDomain.FixComplementSectPrisonBuilding`（`Organization/OrganizationDomain.cs:324`）：
```csharp
Location loc = sect.GetLocation();
sbyte sectIndex = GetLargeSectIndex(sect.GetOrgTemplateId());
if (sectIndex >= 0) {
    short buildingTemplateId = (short)(sectIndex + 303);   // 牢房段 303~317 對應大門派
    DomainManager.Building.PlaceBuildingAtBlock(context, loc.AreaId, loc.BlockId, buildingTemplateId, forcePlace:true, isRandom:false);
}
```
`PlaceBuildingAtBlock`（實裝 `BuildingDomain.cs:678`）在該地格的 `BuildingAreaData` 找空格、`ResetData(templateId)`、`PlaceBuilding(...)`。
→ **「某建築屬於某組織」＝該組織把對應 templateId 的建築放到自己聚落地格的產業網格。** 反查由前端 `cfg.BelongOrganization`（型錄欄位，sbyte）輔助（牢房分支 `IsTaiwuSectFugitive(cfg.BelongOrganization)`，`UI_BuildingArea.cs:3601`）。

### 6.3 `BelongOrganization` 與 `AvailableOrganization`
- `BelongOrganization`（型錄 sbyte）：標示該建築型「屬於哪個組織」。實裝可確認的**唯一運行時讀取點**在前端 `UI_BuildingArea.cs:3601`（牢房逃犯判斷），後端 `BuildingDomain` 未直接讀（grep 無命中）。→ 屬「弱關聯」，主要是分類/UI 用途。
- `AvailableOrganization`（型錄 `List<short>`，**實裝新增**欄位，舊源無；見 §0 `Config.BuildingBlockItem` 實裝欄位清單）：語意為「此建築可用於哪些組織」。在 `BuildingDomain` 也未見直接讀取（可能由其他 domain/前端或 ConfigData 注入流程消費），需另行追查，但其存在強烈暗示「建築型↔組織」是設計上的可配置維度。

### 6.4 商會是不是 Organization？
**不是。** 商會＝`Config.MerchantTypeItem`（商人系統），與 `Config.OrganizationItem`（門派/聚落）是兩套獨立系統：
- 商會掛載靠「商會建築(274~280 總/分號, 318 特殊) + `cfg.MerchantId` 指向 MerchantType」，位置由 `MerchantTypeItem.HeadArea/BranchArea`（城市 area templateId）決定。
- 門派/聚落根據地則靠 `Settlement.Location` + `SettlementInfo.OrgTemplateId`。

### 6.5 對「小門派根據地＝特殊建築」構想的結論
- 遊戲**已有**「組織(Sect) 持 Location + 在該地格放專屬建築」的完整機制（牢房 303~317、門派建築 239~253、特殊建築 259~273）。一個 `Sect` 就是把某 `OrgTemplateId` 綁到一個 `Location`，並在該產業網格放置門派建築。
- 因此「特殊建築作為小門派根據地」在**資料模型上是現成可行的方向**：建立一個 `OrganizationItem`(IsSect) → 給它一個 `Location`(某地格) → 用 `PlaceBuildingAtBlock` 放代表性建築。
- 但「建築本身即根據地」（純靠一格建築承載組織）並不成立——根據地實體是 `Settlement`，建築只是其在網格上的視覺/功能載體。

---

## 7. Mod 可行性評估

### 7.1 哪些是 ConfigData（可注入）、哪些寫死
**可注入（ConfigData，走 `ConfigData<T,TKey>.AddExtraItem(identifier, refName, item)`）——實裝驗證 `Config.BuildingBlock : ConfigData<BuildingBlockItem, short>`、基類 `ConfigData` 確有 `public int AddExtraItem(...)`：**
- `BuildingBlock`（建築型錄）、`ShopEvent`（商品/募人/資源）、`MerchantType`（商會）、`Organization`（門派/聚落）皆為 `ConfigData<,>`，理論上都能 `AddExtraItem` 注入新項。
- 參考 mod 已有同模式範例：`mods/MoreFactionCombatSkillsBackend/FeaturesBoundToFuyu/DataConfigAppenderHelpers.cs`（`AddSpecialEffectItemToConfig` 等用 `((ConfigData<...>)Instance).AddExtraItem(...)`）+ `DataConfigAppender.cs`（YAML 驅動補/改 config，反射逐欄位套用）。

**寫死（硬編碼，mod 難改）：**
- **TemplateId 段判斷**：前端 `UI_BuildingArea` 把行為綁死在數字區間（`SectSpecialBuildingIdList`、`274~280`、`284~302`、`303~317`、`templateId==48/49` 等）。新增的建築 templateId 落在這些段「之外」→ 走 `else`（一般 `ShowBuildingManage`）；想要新建築觸發商會/事件/治理等特殊行為，要嘛把 templateId 落進既有段（風險高、撞 ID），要嘛 Harmony patch 這些判斷方法。
- **`UI_BuildingManage` 內依 templateId 生成的按鈕**（商會 274~280/318、金庫 284~302…）同樣硬編碼。
- 商會總/分號的城市綁定（`MerchantType.HeadArea/BranchArea` 用 area templateId）是城市級設計，非任意地格。

### 7.2 構想 A：「給一個城鎮建設產業視圖（讓它有產業可建/可看）」
- **可看（進入產業視圖）**：所有有 `BuildingAreaData` 的聚落地格本來就能 `OnClickBuilding` 進 `UI_BuildingArea`（非家園也可，只是多數格不可互動）。所以「看得到產業」門檻低。
- **可建（在非家園蓋新建築）**：建造流程（`UI_BuildingOverview`/`StartPlanBuilding`/`ConfirmBuild`）與互動閘 `BuildingBlockCanInteractable` 都綁 `_isTaiwuVillage`（家園才可規劃建造）。要讓某城鎮可建，需 Harmony patch `_isTaiwuVillage`/`BuildingBlockCanInteractable`/規劃流程的家園判斷，並確保後端 `BuildingDomain` 的建造/維護結算也接受該地格。
- **難度：部分可行（中高）**。看＝易；可建＝需多處前後端 patch（家園判斷散落），且後端結算（資源產出、店鋪、月結）多以太吾村 settlementId 為前提，要逐一處理。

### 7.3 構想 B：「新增一種產業建築」
- **新增型錄**：用 `BuildingBlock.AddExtraItem` 注入一筆 `BuildingBlockItem`（可走參考 mod 的 YAML appender 模式）。
- **若是純功能/資源/作坊型建築**（落在一般 `Building` 分支，靠 `SuccesEvent→ShopEvent`、`CollectResourcePercent`、`DependBuildings` 等型錄欄位即可）：**較可行**，因為一般分支走 `ShowBuildingManage`，再靠型錄欄位驅動 UI/結算。
- **若要特殊互動（商會/事件/治理）**：需讓 templateId 落入硬編碼段或 patch 判斷方法 → **較困難**。
- **難度：部分可行**。普通產業建築可注入；特殊行為建築受 templateId 段硬編碼限制。

### 7.4 構想 C：「特殊建築作為小門派根據地」
- 根據地實體是 `Settlement`（持 `OrgTemplateId`+`Location`），不是單格建築。要做小門派根據地：注入 `OrganizationItem`(IsSect) + 在世界生成時建立一個綁該 OrgTemplateId 的 `Sect`(Location) + 用 `PlaceBuildingAtBlock` 放標誌建築。
- **難度：部分可行（高）**。資料模型支援，但「在既有存檔/世界中動態新增一個門派聚落」需深入 `OrganizationDomain` 的聚落生成/成員生成流程，且要處理地圖 `SettlementInfo` 注入、金庫/牢房/成員等附屬資料，工程量大。

### 7.5 最小切入點建議
1. **先做「可看 + 普通產業建築注入」**：用 `BuildingBlock.AddExtraItem` 注入一筆落在 `Building` 型、不需特殊互動的新建築（功能靠 `SuccesEvent→ShopEvent` / 資源欄位），驗證它能在產業視圖出現、能開 `UI_BuildingManage`。這條最不依賴 patch。
2. **要特殊互動時**：用 Harmony patch `UI_BuildingArea.OpenBuildingManage` / 各 `Is*Building` 判斷，把新 templateId 導向想要的行為，或攔 `BuildingIconClick`。
3. **要事件**：優先利用型錄 `SuccesEvent/SpecialEvent/IdleEvent`，或掛 `EventTriggerType` 中 `allowExternal:true` 的觸發點（17/20/22）。
4. **要根據地門派**：先在新世界生成階段（非既有存檔）實驗 `OrganizationDomain` 聚落+建築放置，降低存檔遷移風險。

---

## 8. 待釐清問題
1. `AvailableOrganization`（型錄新欄位）的實際消費者在哪個 domain/UI？（`BuildingDomain` grep 無命中，需掃 `OrganizationDomain`/前端/ConfigData 注入流程。）
2. 非家園聚落是否真有可寫的 `BuildingAreaData`？普通城鎮的產業網格是否只讀（純展示組織擺好的建築）？需確認 `BuildingDomain.GetElement_BuildingAreas(location)` 對非家園地格的初始化來源。
3. 商會 `MerchantType` 的庫存/商品實際從哪個 domain 取（`UIElement.Shop` 的後端資料源、Merchant domain 的 `MerchantInfoMerchantData`）— §4.2 只追到開窗，未追商品結算。
4. `BuildingBlock.AddExtraItem` 注入的新 templateId 是否會被序列化/存檔接受（`BuildingBlockData` 只存 templateId，但型錄需在每次載入重注入）— 需驗證 mod 載入時序與存檔相容性。
5. 構想 B「特殊行為新建築」若 patch `OpenBuildingManage`，是否會與既有 ID 段判斷產生副作用（顏色標記 `UI_BuildingArea.cs:4208` 等也用 ID 段）。
