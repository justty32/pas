# session_log — vanilla-base-generation-expanded（VBGE）

- 2026-06-06 初次分析：確認 VBGE 為純資料 mod（無 .cs/.dll），硬相依 VFE Core 的 KCSG 引擎。
- 2026-06-06 拆素材結構：SettlementDefs（4 派系，21 個 SettlementLayoutDef 含 abstract）、LayoutDefs/Specialisations（7 檔派系結構）、LayoutDefs/GenericLayouts（14 檔通用房）、約 317 個 StructureLayoutDef、約 12 個 SymbolDef。
- 2026-06-06 確認三層模型：SymbolDef（具名符號，多數 grid token 直接用原版 defName 隱式 symbol）→ StructureLayoutDef（grid 藍圖+tags）→ SettlementLayoutDef（allowedStructures 用 tag+count 抽結構），靠 tag 字串鬆耦合。
- 2026-06-06 確認掛接：Patches/Settlements.xml 用 PatchOperationAddModExtension 把 KCSG.CustomGenOption 注入 4 個 FactionDef；帝國那條用 PatchOperationFindMod 判 Royalty。
- 2026-06-06 產出 5 份分析：architecture/00_overview、architecture/01_kcsg_data_model、details/extension_points、tutorial/01_add_settlement_layout，及 projects 下 SOURCE_POINTER.md。
- 2026-06-06 結論：自製整套派系聚落外觀＝純資料可成（VBGE 自身即證明）；只有新生成原語/resolver/版面演算法/觸發時機需 KCSG C#（屬 VFE Core，待驗證）。
