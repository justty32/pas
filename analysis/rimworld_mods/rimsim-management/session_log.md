# RimSim Management Framework 分析 session log

- 辨識：chezhou.Framework.RimSimManagementFramework（边缘模拟经营框架，3736621496，作者 追踪虫+Migua），商店/經營模擬框架；單 DLL SimManagementLib.dll，僅 Harmony，建議載入在種族 mod 之下。
- 反編譯 → projects/.../decompiled/（64541 行）。
- 關鍵：Defs 分 Required/(核心骨架勿動)與 Reusable/(資料驅動擴充，作者註解「複製改 defName」)。
- Reusable Def 型別：GoodsDef(ThingDef 清單)/ShopServiceDef(價格/時長/計費/workerClass)/CustomerKindDef/CollectibleExchangeListDef/PurchaseOutcomeDef/ShopTuningDef/CustomerExpressionSetDef/BusinessExtensionRecommendationDef。
- 機制：CustomerArrivalManager:MapComponent 排顧客上門→顧客 AI JobDriver(WindowShop/BrowseAndPick/PayAtRegister/UseVendingMachine/UsePaidService/DineIn)；店員 WorkGiver(ManCashRegister/Restock/PrepareOrder)；ThingComp(ServiceProvider/VendingMachine/GoodsData/CashStorage/Sign)；GameComponent 財務+評價。
- 結論：開店內容(商品/服務/顧客/收藏/平衡)大多純 XML；新顧客行為(CustomerActionDef+JobDriver)/服務效果(workerClass)/設施機制(Comp+WorkGiver+JobDriver)需 C#。
- 對外最友善的純 XML 內容框架之一(同 WorldTechLevel/VehicleFramework「框架預期被 XML 餵養」)。
- 產出 architecture/00_overview.md、details/extension_points.md、projects/.../SOURCE_POINTER.md。
