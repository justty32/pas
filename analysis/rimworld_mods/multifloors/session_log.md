# MultiFloors 分析 session log

- 辨識：telardo.MultiFloors（3384660931），核心 MultiFloors.dll＋0PrepatcherAPI.dll（依賴 Prepatcher）＋9 個 ModCompat 子 DLL。
- 反編譯核心 → projects/.../multifloors/decompiled/（22880 行）；compat DLL 不深入只記模式。
- 釐清核心：樓層＝PocketMap（MF_UpperLevelMapComp/MF_BasementMapComp : MF_PocketMapComp），垂直通行＝Stair : MapPortal＋Elevator 三型＋ElevatorNet。
- 跨層傳輸：TransferPolicy/AutoTransferWorker/ITab_PowerTransmission/ITab_BillGiverLinkSetting；全域 MultiFloorManager : GameComponent。
- 資料設定：UpperLevelSettingsDef 把 PlanetLayerDef→地形+MapGenerator（MayRequire gate 各星球層 mod）；StairsModExtension 設樓梯/電梯配對。
- 結論：引擎全 C#＋Prepatcher；純 XML 接點＝UpperLevelSettingsDef（新星球層支援）＋新外觀樓梯電梯（沿用 thingClass+StairsModExtension）＋ModCompat gated DLL 模式。
- 產出 architecture/00_overview.md、details/extension_points.md、projects/.../SOURCE_POINTER.md。
