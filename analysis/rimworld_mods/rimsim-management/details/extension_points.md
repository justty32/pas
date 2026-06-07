# RimSim Management Framework 擴充接點（純 XML vs 必須 C#）

> 結論：作者刻意把可擴充 Def 收進 `Defs/Reusable/` 並用中文註解教「複製改 defName」。**開店內容（商品/服務/顧客/收藏品/平衡）大多純 XML**；新顧客行為/新設施機制/新服務邏輯才需 C#。

## 純 XML vs 必須 C# 二分表

| 需求 | 純 XML？ | 接點 / 說明 |
|---|---|---|
| 新增商品分類 | ✅ 純 XML | 複製 `SimManagementLib.SimDef.GoodsDef`（`Reusable/GoodsDef/`）改 defName，`GoodsList` 列 ThingDef（可用 `MayRequire` gate DLC 物） |
| 新增付費服務 | ✅ 純 XML（行為除外） | `ShopServiceDef`：`basePrice`/`durationTicks`/`billingMode`（PayBeforeUse…）/`useJobDef`/`labelOverride`/`checkoutAfterSelection`；沿用預設 `ShopServiceWorker` 即純 XML，要全新服務效果才設 `workerClass`（C#） |
| 新增顧客類型 | ✅ 純 XML | `CustomerKindDef`（`Reusable/CustomerKindDef/`） |
| 收藏品兌換清單 | ✅ 純 XML | `CollectibleExchangeListDef` |
| 顧客表情/台詞 | ✅ 純 XML | `CustomerExpressionSetDef`（＋`CustomerExpressionTagExtension` DefModExtension） |
| 購買結果 | ✅ 純 XML | `PurchaseOutcomeDef` |
| 經營數值調校 | ✅ 純 XML | `ShopTuningDef`（`Reusable/ShopTuningDef/`） |
| 擴店推薦項 | ✅ 純 XML | `BusinessExtensionRecommendationDef` |
| 店員角色 / 經營 UI 分頁 | ✅ 純 XML（多數） | `ShopStaffRoleDef` / `ShopUiPageDef`（在 `Required/`，但本身是 data def） |
| 新店內設施（用既有 Comp） | ✅ 純 XML | 新 `ThingDef` 掛既有 `ThingComp_ServiceProvider/VendingMachine/GoodsData/CashStorage/CollectibleDisplayStand/CustomSign` |
| 全新顧客「行為」 | ❌ C# | `CustomerActionDef` 多半綁 `JobDriver`（`CustomerActionJobDriverBase`），新行為要寫 JobDriver |
| 全新服務「效果」 | ❌ C# | `ShopServiceDef.workerClass` 指向新 `ShopServiceWorker` 子類 |
| 全新設施「機制」 | ❌ C# | 新 `ThingComp` / `WorkGiver` / `JobDriver` |
| 財務/評價/上門排程規則 | ❌ C# | `GameComponent_ShopFinanceManager` / `GameComponent_CustomerReviewManager` / `CustomerArrivalManager` |

## 最省力衍生（純 XML，作者明示路徑）

1. **加一個主題商店的商品**：複製 `GoodsDef` 改 defName＋`GoodsList`（例如「藥房」只賣藥品與醫療包）。
2. **加付費服務**：寫 `ShopServiceDef`（如「按摩椅」`basePrice`＋`durationTicks`＋沿用預設 worker），純 XML。
3. **接種族 mod 的顧客**：因建議載入在種族 mod 之下，`CustomerKindDef`/pawnGroup 可納入這些種族（純 XML）。
4. **平衡包**：只改 `ShopTuningDef`。

## 對 Create 的意義

- 本框架的 `Required/Reusable` 分層＋XML 註解，是本群組中對「純 XML 內容擴充」最友善、指引最明確者之一（與 World Tech Level 的 `TechLevelConfigDef`、Vehicle Framework 的範本同類「框架預期被 XML 餵養」）。
- 想做「一間特色商店 / 一套服務 / 一群主題顧客」→ 純 XML 內容包即可，零 C#。
- 想做「新顧客玩法行為 / 新設施機制」→ 需 C#（無源碼，但 Def 階層清楚，照 WorkGiver+JobDriver+ThingComp 三件組擴充）。
