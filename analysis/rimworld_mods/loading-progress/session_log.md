# Loading Progress 分析 session log

- 辨識：ilyvion.LoadingProgress（3535481557），MIT/Apache 開源(GitHub ilyvion/loading-progress)，僅相依 Harmony，無 Def 無 Patches XML、單 DLL。
- 反編譯 ilyvion.LoadingProgress.dll → projects/.../decompiled/（7056 行含編譯器產物）。
- 核心：Harmony 鉤住啟動載入管線(LoadedModManager.CombineIntoUnifiedXML/ModContentPack.ReloadContentInt/LoadPatches/XmlInheritance/DirectXmlToObjectNew/DirectXmlCrossRefLoader/LoadedLanguage/LongEventHandler)→LoadingDataTracker 累積→LoadingProgressWindow 畫進度。
- StartupImpact 子系統量測逐 mod 載入耗時；LoadingStage enum 表階段；Settings 只有視窗位置。
- 結論：純 C# 工具 mod，無資料層、對外無純 XML 擴充面；create 價值＝技術參考(instrument 啟動管線/LongEventHandler 畫 UI/逐 mod 耗時)，衍生須 fork C#。
- 產出 architecture/00_overview.md、details/extension_points.md、projects/.../SOURCE_POINTER.md。
