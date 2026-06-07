# session_log — dead-mans-switch（Analysis）

- 讀 About.xml：packageId Aoba.DeadManSwitch.Core，1.6 硬相依 Harmony/Biotech/AOBA.Framework（FFF），舊版用 VFE Core。
- 讀 計畫內容.txt：作者企劃＝機兵殘骸/墳場地標、叛逃者開局、鉭鎢/石墨稀生產鏈、機兵特化武器、防衛建築。
- 統計 Defs：357 ThingDef / 79 Recipe / 68 PawnKind / 57 Hediff / 25 Research / 18 Ability / 2 Faction / 1 Gene。
- 反編譯 DMS.dll（1409 行 17 類）：只做 Bossgroup 突襲、文件處理任務、Royalty 授勳/穿梭機 permit；0 處 Fortified.*。
- 驗證機兵 thingClass：Fortified.WeaponUsableMech×2、Fortified.HumanlikeMech×1、Pawn×2；行為全在 FFF。
- 驗證武器 verbClass：35×Verb_Shoot、5×Fortified.Verb_ArcSprayProjectile；FFF 提供 31×HeavyEquippableExtension/27×MechWeaponExtension 等。
- 確認 DLC 內容用 Biotech/Ideology/Royalty 子資料夾 + MayRequire 條件載入。
- 既有 00_overview.md / 01_mech_data_model.md（前次 session）內容經抽查與本次驗證一致，保留。
- 補寫 details/extension_points.md（純 XML vs 必須 C# 二分表 + 判定法則）。
- 結論：DMS＝純資料內容包；引擎＝FFF（Fortified Feature Framework）；與 Exosuit/Mobile Dragoon 為共享 FFF 的兄弟內容包。
