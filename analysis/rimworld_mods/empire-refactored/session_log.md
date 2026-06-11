# Empire Refactored 分析 session log

- 2026-06-06 讀 README/About，確認 v1.3.74、1.6 only、硬相依 harmony、9 個 compat 子模組。
- 2026-06-06 勘查 Core 源碼樹（279 .cs），定位入口：FactionColoniesMod:Mod、FactionFC:WorldComponent、WorldSettlementFC:Settlement。
- 2026-06-06 確認帝國資料模型＝FactionFC.settlements（每聚落為正規 WorldObject by-reference）。
- 2026-06-06 讀 WorldComponentTick/TaxTick/AddTax，釐清稅務與分層 tick 排程。
- 2026-06-06 確認 def 化擴充：WorldSettlementDef/ResourceTypeDef/BuildingFCDef/FCEventDef/FCPolicyDef 純 XML。
- 2026-06-06 確認 compat 機制＝LoadFolders.xml IfModActive 條件載入；兩風格＝Harmony patch / bridge 介面。
- 2026-06-06 盤點 15 個 Registry + 20+ FCInterfaces 擴充接點（免 Harmony 路徑）。
- 2026-06-06 完成 5 份產出：00_overview/01_core_systems/02_compat_modules/extension_points + SOURCE_POINTER。
- 2026-06-11 深挖：補 details/bridge_module_walkthrough.md（Patch-RW 逐檔走讀＋22 介面完整 API＋Registry 形狀與 ClearCaches 陷阱）。
- 2026-06-11 新增 tutorial/01_writing_extension_module.md（從零寫第三方擴展 mod，含 csproj/Init 防護/接點決策/部署驗證/陷阱表）。
- 2026-06-11 生成 html/ 導覽層：index＋architecture＋compat＋extension＋tutorial 五頁＋_shared.css（沿用 c-mera/hermes 樣式體系，5 連結 nav）。
