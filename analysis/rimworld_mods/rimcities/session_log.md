# RimCities 分析 session_log

- 讀 About.xml：確認 packageId Cabbage.RimCities、1.0-1.6 全支援、僅相依 Core+內附 Harmony、無 modDependencies。
- 列 1.6 檔樹：Assemblies(RimCities.dll+0Harmony)、Defs(MapGeneration/WorldObjects/Incidents/Duties/TraderKinds/Quests…)、Patches(CE/MedievalTimes/MoreFactionInteraction 軟相容)。
- 讀 WorldObjects.xml：五種城市 def 皆 ParentName=CityCommon，worldObjectClass=Cities.City/Citadel，各指不同 mapGenerator。
- 讀 WorldGeneration.xml+Patches.xml：WorldGenStep_Cities 掛在 Surface PlanetLayer 的 worldGenSteps。
- 讀 MapGeneration.xml：確認城市地圖=XML 定義 genStep 管線(Walls/Streets/Docks/Bazaars/Prison/Hospital/各建築/Fields/Sidewalks/Post)，大量參數(count/areaConstraints/options/roomDecorators)資料驅動。
- 讀 decompiled City/Citadel/WorldGenStep_Cities：City:Settlement，Citadel 120x625 攻城地圖，世界散佈 defName 寫死四種。
- 讀 GenCity/Stencil/GenStep_RectScatterer/GenStep_Buildings/GenStep_Streets：確認佈局=Stencil DSL+遞迴 BSP 切房+flood-fill 選址，演算法寫死 C#。
- 讀 RoomDecorator/BuildingDecorator：裝飾器 abstract+多子類，XML 用 Class 引用，新規則需新 C# 型別。
- 讀 23 個 Harmony patch(2146-2576)：mapSize/派系/防擊敗/交易/失竊好感/尋路/砲塔 等城市行為靠 patch 注入。
- 讀 Config_Cities/Mod_Cities：城市數量/比例/尺寸=mod 設定(非 def)；enableLooting/Turrets/Mortars/Quests 等開關。
- 確認任務系統=自製舊框架(Quest:IExposable+WorldComponent_QuestTracker)，Script_CityQuest.xml 僅 TODO 佔位。
- 產出 architecture/00_overview.md、01_city_map_generation.md、details/extension_points.md、tutorial/01_pure_xml_extension.md。
- 寫 projects 端 SOURCE_POINTER.md。
