# SimplePortal 分析 session log

- 確認素材：mod 根 `.../294100/3325512144`，自帶 54 個 .cs 在 `1.6/Src/src/`，優先讀源碼。
- 讀 About.xml：author Furia、packageId flammpfeil.SimplePortal、supportedVersions 1.5/1.6。
- 核心發現：`SimplePortal_Building : MapPortal`（SimplePortal_Building.cs:18）—繼承原版深淵之門基底。
- 核心發現：目的地是對端傳送門的真實地圖（GetOtherMap=linkedPortal.MapHeld），非 PocketMap。
- 核心發現：傳送＝DeSpawn+GenSpawn 到對面（JobDriver_EnterSimplePortal.cs:89-90）。
- 核心發現：配對＝雙向 linkedPortal 引用（CommandLinkThePortals.cs:44-45），Scribe_References 存檔。
- 確認 PocketMap 僅作 exit 欄位佔位（SimplePortal_Building.cs:352）+ 進入時特判非 PocketMap 才卸貨。
- 確認 4 Harmony patch：抑制原版進入鈕、護地圖不回收、放行連結瞄準、微縮選單。
- 確認 XML 變體共 4 種，純資料可調 8 個 CompProperties 欄位。
- 產出 00_overview.md（定位/相依鏈/分佈表/總圖）。
- 產出 01_portal_mechanism.md（配對→傳送管線+PocketMap+存檔）。
- 產出 details/extension_points.md（A 純 XML vs B 改碼二分）。
- 產出 projects/.../simple-portal/SOURCE_POINTER.md（源碼指標）。
