# Walk the World 分析 session log

- 辨識：addvans.WalkTheWorld（3546716725），僅相依 Harmony，無自訂 Def、無 Patches XML。
- 反編譯 WalkTheWorld.dll → projects/.../decompiled/（1731 行）。
- 核心：WalkTheWorld:GameComponent 偵測 pawn 走到邊緣→進相鄰世界格地圖（MapGenerator 即時生成、離開重置）；VisitCell:Camp 當徒步據點。
- Harmony patch：ExitMapGrid 四邊設出口、徒步交易接管、聚落擊敗判定、Caravan 可達物品。
- 行為靠 ModSettings 三 enum（LeavingType/RandomEventsFilterType/CameraFocusMode）。
- 結論：純 C# 機制 mod，無資料層、對外無純 XML 擴充面；衍生須改 C#。注意與 ExitMapGrid 相關 patch 的跨 mod 衝突。
- 產出 architecture/00_overview.md、details/extension_points.md、projects/.../SOURCE_POINTER.md。
